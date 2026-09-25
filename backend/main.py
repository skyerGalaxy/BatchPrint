from importlib.readers import FileReader
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import pandas as pd
import json
import math
from pathlib import Path
from urllib.parse import quote, unquote, urlparse
import io
from PIL import Image
import requests
import tempfile
import os
import shutil
import base64
from pypdf import PdfReader, PdfWriter
from docx import Document
from docx.shared import Pt, Mm, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docxtpl import DocxTemplate, InlineImage
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def register_custom_fonts():
    system_font_map = {
        "微软雅黑": "msyh.ttc",
        "楷体": "simkai.ttf",
        "宋体": "simsun.ttc",
        "黑体": "simhei.ttc",
    }

    if os.name == "nt":
        windows_fonts_dir = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts"

        seguisym_path = windows_fonts_dir / "seguisym.ttf"
        if seguisym_path.exists() and "Segoe UI Symbol" not in pdfmetrics.getRegisteredFontNames():
            try:
                pdfmetrics.registerFont(TTFont("Segoe UI Symbol", str(seguisym_path)))
            except Exception as error:
                print(f"注册 Segoe UI Symbol 失败: {error}")

        for font_path, font_name in [
            ("wingdng2.ttf", "Wingdings 2"),
            ("arial.ttf", "Arial"),
            ("arialbd.ttf", "Arial-Bold"),
            ("ariali.ttf", "Arial-Italic"),
            ("arialbi.ttf", "Arial-BoldItalic"),
        ]:
            full_path = windows_fonts_dir / font_path
            if full_path.exists() and font_name not in pdfmetrics.getRegisteredFontNames():
                try:
                    pdfmetrics.registerFont(TTFont(font_name, str(full_path)))
                except Exception as error:
                    print(f"注册字体 {font_name} 失败: {error}")

        for font_name, font_file in system_font_map.items():
            font_path = windows_fonts_dir / font_file
            if font_path.exists() and font_name not in pdfmetrics.getRegisteredFontNames():
                try:
                    pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
                except Exception as error:
                    print(f"注册系统字体失败: {font_name}, {error}")


def register_user_fonts(fonts_dir_str: str):
    if not fonts_dir_str:
        return
    user_dir = Path(fonts_dir_str)
    if user_dir.exists():
        for font_file in user_dir.glob("*.ttf"):
            font_name = font_file.stem
            if font_name not in pdfmetrics.getRegisteredFontNames():
                try:
                    pdfmetrics.registerFont(TTFont(font_name, str(font_file)))
                except Exception as error:
                    print(f"注册用户字体失败: {font_name}, {error}")


@app.get("/api/fonts")
async def get_fonts_list(request: Request, fonts_path: str = None):
    fonts: list = [
        {"name": "微软雅黑", "value": "微软雅黑", "type": "system"},
        {"name": "楷体", "value": "楷体", "type": "system"},
        {"name": "宋体", "value": "宋体", "type": "system"},
        {"name": "黑体", "value": "黑体", "type": "system"},
        {"name": "Arial", "value": "Arial", "type": "system"},
        {"name": "Times New Roman", "value": "Times New Roman", "type": "system"},
    ]

    base_url = str(request.base_url).rstrip("/")
    if fonts_path:
        user_fonts_dir = Path(fonts_path)
        if user_fonts_dir.exists():
            for font_file in user_fonts_dir.glob("*.ttf"):
                font_name = font_file.stem
                encoded_path = quote(str(font_file), safe='')
                fonts.append({
                    "name": font_name,
                    "value": font_name,
                    "type": "custom",
                    "file": str(font_file),
                    "url": f"{base_url}/api/fonts/file/user?path={encoded_path}",
                })

    return {"fonts": fonts}


@app.get("/api/fonts/file/user")
async def get_user_font_file(path: str):
    font_path = Path(unquote(path))
    if not font_path.exists() or not font_path.suffix.lower() == ".ttf":
        return {"error": "字体文件不存在"}
    return FileResponse(
        font_path,
        media_type="application/octet-stream",
        filename=font_path.name
    )

def resolve_local_path_from_url(url: str) -> str:
    parsed = urlparse(url)
    raw_path = unquote(parsed.path)
    if os.name == "nt" and raw_path.startswith("/") and len(raw_path) > 2 and raw_path[2] == ":":
        return raw_path[1:]
    return raw_path

@app.post("/save_config")
async def save_config(data: dict):
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"msg": "配置已保存"}

# @app.post("/generate")
# async def generate():
#     batch_print.run()  # 调用批处理逻辑
#     return {"msg": "生成完成"}

@app.post("/get_excel_headers")
async def get_excel_headers(file: UploadFile = File(...)):
    df = pd.read_excel(file.file)
    raw_headers = df.columns.tolist()
    headers = [str(h) for h in raw_headers]
    has_merged_cells = any(
        str(h).startswith("Unnamed:") for h in raw_headers
    ) and not all(str(h).startswith("Unnamed:") for h in raw_headers)
    df_obj = df.astype(object)
    content = df_obj.where(df_obj.notna(), None).values.tolist()
    return {
        "headers": headers,
        "content": content,
        "has_merged_cells": has_merged_cells,
    }

def sse_message(event_type: str, payload: dict) -> str:
    return "data: " + json.dumps({"type": event_type, **payload}, ensure_ascii=False) + "\n\n"


# ============================================================
# DOCX 相关接口
# ============================================================

@app.post("/api/docx/parse")
async def parse_docx(file: UploadFile = File(...)):
    """解析 DOCX 结构，返回带 anchorId 的段落/表格序列，供前端定位与循环块配置。"""
    content = await file.read()
    try:
        doc = Document(io.BytesIO(content))
    except Exception as e:
        return {"error": f"无法解析 DOCX 文件: {e}"}

    structure = []
    p_idx = 0
    t_idx = 0
    for block in doc.element.body:
        tag = block.tag
        if tag == qn("w:p"):
            # 段落
            texts = []
            for node in block.iter(qn("w:t")):
                texts.append(node.text or "")
            structure.append({
                "type": "paragraph",
                "anchorId": f"p_{p_idx:04d}",
                "text": "".join(texts),
            })
            p_idx += 1
        elif tag == qn("w:tbl"):
            # 表格
            rows = []
            for r_idx, tr in enumerate(block.findall(qn("w:tr"))):
                cells = []
                for tc in tr.findall(qn("w:tc")):
                    cell_texts = []
                    for node in tc.iter(qn("w:t")):
                        cell_texts.append(node.text or "")
                    cells.append("".join(cell_texts))
                rows.append({
                    "anchorId": f"tr_{t_idx:04d}_{r_idx:04d}",
                    "cells": cells,
                })
            structure.append({"type": "table", "rows": rows})
            t_idx += 1
    return {"structure": structure}


def _docx_resolve_image_path(src: str, base_path: str) -> Path | None:
    """把前端传过来的图片 src 还原成本地路径。"""
    if not src:
        return None
    src = src.strip()
    if src.startswith("http://asset.localhost/"):
        local = resolve_local_path_from_url(src)
        return Path(local)
    # 相对路径按数据目录解析
    p = Path(src)
    if not p.is_absolute() and base_path:
        p = Path(base_path) / src
    return p if p.exists() else None


def _docx_apply_text_style(paragraph, font_family: str, font_size: float, font_weight: int, italic: bool, color: str, opacity: float):
    """对段落设置字体样式（作用于 run 级别）。"""
    for run in paragraph.runs:
        run.font.name = font_family
        run._element.rPr.rFonts.set(qn("w:eastAsia"), font_family)
        run.font.size = Pt(font_size)
        run.font.bold = font_weight >= 600
        run.font.italic = italic
        hex_str = color.lstrip("#")
        if len(hex_str) == 6:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            run.font.color.rgb = RGBColor(r, g, b)


def _docx_insert_run_at_offset(paragraph, text: str, style: dict, offset: int):
    """在段落指定字符偏移处插入带样式的文本 run。"""
    full_text = paragraph.text
    if offset < 0:
        offset = 0
    if offset > len(full_text):
        offset = len(full_text)

    before = full_text[:offset]
    after = full_text[offset:]

    # 保存原有第一个 run 的样式作为默认样式
    base_rpr = None
    if paragraph.runs:
        first_r = paragraph.runs[0]._element
        rpr = first_r.find(qn("w:rPr"))
        if rpr is not None:
            base_rpr = rpr

    # 清空段落
    for r in list(paragraph.runs):
        r._element.getparent().remove(r._element)

    def _add_run(txt, custom_style=None):
        if not txt:
            return
        run = paragraph.add_run(txt)
        if custom_style:
            run.font.name = custom_style.get("fontFamily", "微软雅黑")
            run._element.rPr.rFonts.set(qn("w:eastAsia"), custom_style.get("fontFamily", "微软雅黑"))
            run.font.size = Pt(custom_style.get("fontSize", 12))
            run.font.bold = custom_style.get("fontWeight", 400) >= 600
            run.font.italic = custom_style.get("italic", False)
            hex_str = custom_style.get("color", "#000000").lstrip("#")
            if len(hex_str) == 6:
                run.font.color.rgb = RGBColor(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
        elif base_rpr is not None:
            # 继承原样式
            import copy
            run._element.insert(0, copy.deepcopy(base_rpr))

    _add_run(before)
    _add_run(text, style)
    _add_run(after)


def _docx_insert_image_at_offset(paragraph, image_path: Path, width_mm: float, offset: int):
    """在段落指定字符偏移处插入 InlineImage。"""
    full_text = paragraph.text
    if offset < 0:
        offset = 0
    if offset > len(full_text):
        offset = len(full_text)

    before = full_text[:offset]
    after = full_text[offset:]

    base_rpr = None
    if paragraph.runs:
        first_r = paragraph.runs[0]._element
        rpr = first_r.find(qn("w:rPr"))
        if rpr is not None:
            base_rpr = rpr

    for r in list(paragraph.runs):
        r._element.getparent().remove(r._element)

    def _add_run(txt):
        if not txt:
            return
        run = paragraph.add_run(txt)
        if base_rpr is not None:
            import copy
            run._element.insert(0, copy.deepcopy(base_rpr))

    _add_run(before)
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=Mm(width_mm))
    _add_run(after)


def _docx_set_paragraph_text(paragraph, text: str, style: dict):
    """清空段落所有 run 并写入单一样式文本（用于整段替换）。"""
    for r in list(paragraph.runs):
        r._element.getparent().remove(r._element)
    run = paragraph.add_run(text)
    run.font.name = style.get("fontFamily", "微软雅黑")
    run._element.rPr.rFonts.set(qn("w:eastAsia"), style.get("fontFamily", "微软雅黑"))
    run.font.size = Pt(style.get("fontSize", 12))
    run.font.bold = style.get("fontWeight", 400) >= 600
    run.font.italic = style.get("italic", False)
    hex_str = style.get("color", "#000000").lstrip("#")
    if len(hex_str) == 6:
        run.font.color.rgb = RGBColor(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))


def _docx_insert_inline_image(paragraph, image_path: Path, width_mm: float):
    """在段落中插入 InlineImage。"""
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=Mm(width_mm))


def _docx_add_bookmark(paragraph, bookmark_id: str, bookmark_name: str):
    """在段落级别插入书签，作为循环块或字段锚点。"""
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), bookmark_id)
    start.set(qn("w:name"), bookmark_name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), bookmark_id)
    paragraph._p.insert(0, start)
    paragraph._p.append(end)


def _docx_wrap_table_row_with_loop(tbl, row_idx: int, loop_var: str, list_var: str):
    """把表格第 row_idx 行用 {%tr for item in items %} / {%tr endfor %} 包裹。"""
    tr = tbl.rows[row_idx]._tr
    first_tc = tr.findall(qn("w:tc"))[0]
    # 在该单元格最前面插入 for 标签段落
    for_p = OxmlElement("w:p")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "{%tr for " + loop_var + " in " + list_var + " %}"
    r.append(t)
    for_p.append(r)
    first_tc.insert(0, for_p)

    last_tc = tr.findall(qn("w:tc"))[-1]
    # 在该单元格最后面插入 endfor 标签段落
    end_p = OxmlElement("w:p")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "{%tr endfor %}"
    r.append(t)
    end_p.append(r)
    last_tc.append(end_p)


def _docx_wrap_paragraph_with_loop(doc: Document, anchor_id: str, loop_var: str, list_var: str):
    """根据 anchor_id 找到段落，在其前后插入 {%p for %} / {%p endfor %}。"""
    try:
        target_idx = int(anchor_id.split("_")[1])
    except Exception:
        return False
    body = doc.element.body
    p_idx = 0
    for child in body:
        if child.tag == qn("w:p"):
            if p_idx == target_idx:
                # 在段落前插入 for 段落
                for_p = OxmlElement("w:p")
                r = OxmlElement("w:r")
                t = OxmlElement("w:t")
                t.text = "{%p for " + loop_var + " in " + list_var + " %}"
                r.append(t)
                for_p.append(r)
                child.addprevious(for_p)
                # 在段落后插入 endfor 段落
                end_p = OxmlElement("w:p")
                r = OxmlElement("w:r")
                t = OxmlElement("w:t")
                t.text = "{%p endfor %}"
                r.append(t)
                end_p.append(r)
                child.addnext(end_p)
                return True
            p_idx += 1
    return False


def _docx_build_loop_rows(
    all_rows: list[list],
    headers: list[str],
    main_row: list,
    loop_cfg: dict,
) -> list[dict]:
    """根据循环块配置动态查询出子数据行。"""
    data_range = loop_cfg.get("dataRange", "all")
    range_col = loop_cfg.get("rangeColumn")
    conditions = loop_cfg.get("conditions", [])
    match_mode = loop_cfg.get("matchMode", "所有")

    # 数据范围：全部行 / 指定列非空的行
    if data_range == "columnNonEmpty" and range_col and range_col in headers:
        col_idx = headers.index(range_col)
        rows = [r for r in all_rows if r[col_idx] not in (None, "", "None")]
    else:
        rows = all_rows

    def resolve_value(v):
        if isinstance(v, str) and v.startswith("{{") and v.endswith("}}"):
            expr = v[2:-2].strip()
            if expr.startswith("当前行."):
                field = expr[4:]
                if field in headers:
                    return str(main_row[headers.index(field)] or "")
            return v
        return v

    def check(row):
        row_dict = {headers[i]: row[i] for i in range(len(headers))}
        results = []
        for cond in conditions:
            field = cond.get("field")
            op = cond.get("op")
            val = resolve_value(cond.get("value"))
            fv = row_dict.get(field, "")
            if fv is None:
                fv = ""
            fv = str(fv)
            if op == "等于":
                res = fv == val
            elif op == "不等于":
                res = fv != val
            elif op == "包含":
                res = val in fv
            elif op == "不包含":
                res = val not in fv
            elif op == "为空":
                res = fv == ""
            elif op == "不为空":
                res = fv != ""
            else:
                res = False
            results.append(res)
        if not results:
            return True
        return all(results) if match_mode == "所有" else any(results)

    return [{headers[i]: r[i] for i in range(len(headers))} for r in rows if check(r)]


@app.post("/generate_batch_docx")
async def generate_batch_docx(
    docx_file: UploadFile = File(...),
    excel_file: UploadFile = File(...),
    path: str = Form(...),
    icon_list: str = Form(default="[]"),
    loop_blocks: str = Form(default="[]"),
    filename_config: str = Form(default="{}"),
):
    """DOCX 批量生成（SSE 流式）。"""
    docx_content = await docx_file.read()
    excel_content = await excel_file.read()
    df = pd.read_excel(io.BytesIO(excel_content))
    headers = df.columns.tolist()
    content = df.values.tolist()

    try:
        icon_list_data = json.loads(icon_list)
    except json.JSONDecodeError:
        icon_list_data = []
    try:
        loop_blocks_data = json.loads(loop_blocks)
    except json.JSONDecodeError:
        loop_blocks_data = []
    try:
        filename_cfg = json.loads(filename_config)
    except json.JSONDecodeError:
        filename_cfg = {}

    name_parts = filename_cfg.get("parts") or []
    name_separator = filename_cfg.get("separator", "_")

    def sanitize_filename(name: str) -> str:
        for ch in '\\/:*?"<>|':
            name = name.replace(ch, "_")
        return name.strip().strip(".")

    def build_filename(row_data: dict, row_idx: int) -> str:
        segments = []
        for part in name_parts:
            part_type = part.get("type")
            if part_type == "field":
                value = row_data.get(part.get("field"))
                segment = "" if value is None else str(value)
            elif part_type == "seq":
                num = int(part.get("start") or 1) + row_idx
                digits = int(part.get("digits") or 0)
                segment = str(num).zfill(digits) if digits else str(num)
            else:
                segment = str(part.get("text") or "")
            if segment:
                segments.append(segment)
        name = sanitize_filename(name_separator.join(segments))
        return name or str(row_idx + 1)

    target_dir = Path(path) / "generateDocx"
    target_dir.mkdir(parents=True, exist_ok=True)

    # 所有行都作为主记录行生成
    main_rows = list(enumerate(content))

    image_cache: dict = {}

    def event_stream():
        try:
            total_rows = len(main_rows)
            yield sse_message("start", {"total": total_rows})

            generated_files = []
            used_names = {}

            for out_idx, (row_idx, row) in enumerate(main_rows):
                row_data = {headers[i]: row[i] for i in range(len(headers))}

                # 深拷贝模板，避免多行之间互相污染
                tpl_doc = Document(io.BytesIO(docx_content))

                # ===== 1) 处理循环块：包裹循环标签 + 准备每行子数据 =====
                loop_context: dict[str, list[dict]] = {}
                for block in loop_blocks_data:
                    anchor_id = block.get("anchorId", "")
                    loop_var = block.get("loopVar", "item")
                    list_var = block.get("listVar", "明细")
                    loop_type = block.get("loopType", "paragraph")  # paragraph | tableRow
                    cfg_rows = _docx_build_loop_rows(content, headers, row, block)
                    loop_context[list_var] = cfg_rows

                    if loop_type == "tableRow":
                        # 定位表格与行号
                        # anchorId 格式 tr_0001_0002
                        parts = anchor_id.split("_")
                        if len(parts) >= 3:
                            t_idx = int(parts[1])
                            r_idx = int(parts[2])
                            tbls = tpl_doc.tables
                            if t_idx < len(tbls):
                                tbl = tbls[t_idx]
                                if r_idx < len(tbl.rows):
                                    _docx_wrap_table_row_with_loop(tbl, r_idx, loop_var, list_var)
                    else:
                        _docx_wrap_paragraph_with_loop(tpl_doc, anchor_id, loop_var, list_var)

                # ===== 2) 处理字段/文本/图标：在指定字符偏移处插入内容 =====
                # 字段类：anchorId 指向段落，在 charOffset 处插入当前行字段值
                # 文本类：anchorId 指向段落，在 charOffset 处插入固定文本
                # 图标类：anchorId 指向段落，在 charOffset 处插入符号字符
                # 图片类：anchorId 指向段落，在 charOffset 处插入 InlineImage
                for icon in icon_list_data:
                    option = icon.get("option", {})
                    item_type = option.get("type")
                    anchor_id = icon.get("anchorId", "")
                    if not anchor_id:
                        continue

                    # 条件显隐判断（复用 PDF 的条件逻辑）
                    if icon.get("mode") == "conditional":
                        if not _docx_evaluate_conditions(row_data, icon):
                            # 条件不满足时删除该段落或置空
                            _docx_remove_paragraph_by_anchor(tpl_doc, anchor_id)
                            continue

                    # charOffset 存在 pointer.clientY 中（前端拖放时记录）
                    char_offset = icon.get("pointer", {}).get("clientY", 0)

                    try:
                        target_idx = int(anchor_id.split("_")[1])
                    except Exception:
                        continue
                    body = tpl_doc.element.body
                    p_idx = 0
                    target_p = None
                    for child in body:
                        if child.tag == qn("w:p"):
                            if p_idx == target_idx:
                                from docx.text.paragraph import Paragraph
                                target_p = Paragraph(child, tpl_doc)
                                break
                            p_idx += 1
                    if target_p is None:
                        continue

                    style = {
                        "fontFamily": option.get("fontFamily", "微软雅黑"),
                        "fontSize": max(4, math.floor((icon.get("size") or 120) * 0.12)),
                        "fontWeight": option.get("fontWeight", 400),
                        "italic": option.get("italic", False),
                        "color": option.get("color", "#000000"),
                    }

                    if item_type == "field":
                        field_name = option.get("fieldName")
                        if field_name and field_name in row_data:
                            _docx_insert_run_at_offset(target_p, str(row_data[field_name] or ""), style, char_offset)
                    elif item_type == "text":
                        _docx_insert_run_at_offset(target_p, option.get("text", ""), style, char_offset)
                    elif item_type == "icon":
                        _docx_insert_run_at_offset(target_p, option.get("icon", ""), {
                            **style,
                            "fontFamily": "Segoe UI Symbol",
                        }, char_offset)
                    elif item_type == "image":
                        src = option.get("src", "")
                        img_path = _docx_resolve_image_path(src, path)
                        if img_path and img_path.exists():
                            # 用宽度近似换算：size(px) * 0.2646
                            width_mm = max(10, (icon.get("size") or 120) * 0.2646 * 0.3)
                            _docx_insert_image_at_offset(target_p, img_path, width_mm, char_offset)

                # ===== 3) 用 docxtpl 渲染 =====
                # 先把处理过的 Document 转 bytes，再交给 DocxTemplate
                buf = io.BytesIO()
                tpl_doc.save(buf)
                buf.seek(0)
                tpl = DocxTemplate(buf)

                context = dict(row_data)
                # 注入循环变量
                for list_var, rows in loop_context.items():
                    context[list_var] = rows

                try:
                    tpl.render(context)
                except Exception as e:
                    yield sse_message("error", {"message": f"模板渲染失败(第{out_idx+1}行): {e}"})
                    return

                base_name = build_filename(row_data, row_idx)
                if base_name in used_names:
                    used_names[base_name] += 1
                    base_name = f"{base_name}({used_names[base_name]})"
                else:
                    used_names[base_name] = 0
                output_path = target_dir / f"{base_name}.docx"
                tpl.save(str(output_path))

                generated_files.append(str(output_path))
                yield sse_message("progress", {
                    "current": out_idx + 1,
                    "total": total_rows,
                })

            yield sse_message("done", {
                "msg": "DOCX 已保存",
                "path": str(target_dir),
                "files": generated_files,
            })
        except Exception as error:
            yield sse_message("error", {"message": f"生成失败: {error}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _docx_remove_paragraph_by_anchor(doc: Document, anchor_id: str):
    """根据 anchor_id 删除对应段落（用于条件不满足时隐藏字段）。"""
    try:
        target_idx = int(anchor_id.split("_")[1])
    except Exception:
        return
    body = doc.element.body
    p_idx = 0
    for child in body:
        if child.tag == qn("w:p"):
            if p_idx == target_idx:
                body.remove(child)
                return
            p_idx += 1


def _docx_evaluate_conditions(row_data: dict, icon: dict) -> bool:
    """与 PDF 条件评估逻辑保持一致。"""
    logic_type = icon.get("logicType", "simple")

    def check_condition(conditions: list, match_mode: str) -> bool:
        results = []
        for condition in conditions:
            field = condition.get("field")
            op = condition.get("op")
            value = condition.get("value")
            field_value = row_data.get(field, "")
            if field_value is None:
                field_value = ""
            field_value = str(field_value)
            if op == "等于":
                result = field_value == value
            elif op == "不等于":
                result = field_value != value
            elif op == "包含":
                result = value in field_value
            elif op == "不包含":
                result = value not in field_value
            elif op == "为空":
                result = field_value == ""
            elif op == "不为空":
                result = field_value != ""
            else:
                result = False
            results.append(result)
        if not results:
            return True
        if match_mode == "所有":
            return all(results)
        return any(results)

    if logic_type == "advanced":
        groups = icon.get("groups", [])
        if not groups:
            return True
        group_results = []
        for group in groups:
            group_conditions = group.get("conditions", [])
            group_match_mode = group.get("matchMode", "所有")
            group_results.append(check_condition(group_conditions, group_match_mode))
        result = group_results[0]
        connectors = icon.get("groupConnectors", [])
        for i, connector in enumerate(connectors):
            if connector == "所有":
                result = result and group_results[i + 1]
            else:
                result = result or group_results[i + 1]
        return result

    conditions = icon.get("conditions", [])
    match_mode = icon.get("matchMode", "所有")
    return check_condition(conditions, match_mode)


@app.post("/generate_batch_pdf")
async def generate_batch_pdf(
    pdf_file: UploadFile = File(...),
    excel_file: UploadFile = File(...),
    path: str = Form(...),
    icon_list: str = Form(default="[]"),
    pdf_scale: float = Form(default=2.0),
    filename_config: str = Form(default="{}"),
):
    
    register_custom_fonts()
    register_user_fonts(str(Path(path) / "fonts") if path else None)
    
    pdf_content = await pdf_file.read()
    pdf_reader = PdfReader(io.BytesIO(pdf_content))
    pdf_page_count = len(pdf_reader.pages)
    
    excel_content = await excel_file.read()
    df = pd.read_excel(io.BytesIO(excel_content))
    headers = df.columns.tolist()
    content = df.values.tolist()
    
    try:
        icon_list_data = json.loads(icon_list)
    except json.JSONDecodeError:
        icon_list_data = []

    try:
        filename_cfg = json.loads(filename_config)
    except json.JSONDecodeError:
        filename_cfg = {}
    name_parts = filename_cfg.get("parts") or []
    name_separator = filename_cfg.get("separator", "_")

    def sanitize_filename(name: str) -> str:
        for ch in '\\/:*?"<>|':
            name = name.replace(ch, "_")
        return name.strip().strip(".")

    def build_filename(row_data: dict, row_idx: int) -> str:
        segments = []
        for part in name_parts:
            part_type = part.get("type")
            if part_type == "field":
                value = row_data.get(part.get("field"))
                segment = "" if value is None else str(value)
            elif part_type == "seq":
                num = int(part.get("start") or 1) + row_idx
                digits = int(part.get("digits") or 0)
                segment = str(num).zfill(digits) if digits else str(num)
            else:
                segment = str(part.get("text") or "")
            if segment:
                segments.append(segment)
        name = sanitize_filename(name_separator.join(segments))
        return name or str(row_idx + 1)
    
    target_dir = Path(path) / "generatePdf"
    target_dir.mkdir(parents=True, exist_ok=True)
    
    def check_condition(row_data: dict, conditions: list, match_mode: str) -> bool:
        results = []
        for condition in conditions:
            field = condition.get("field")
            op = condition.get("op")
            value = condition.get("value")
            
            field_value = row_data.get(field, "")
            if field_value is None:
                field_value = ""
            field_value = str(field_value)
            
            if op == "等于":
                result = field_value == value
            elif op == "不等于":
                result = field_value != value
            elif op == "包含":
                result = value in field_value
            elif op == "不包含":
                result = value not in field_value
            elif op == "为空":
                result = field_value == "" or field_value is None
            elif op == "不为空":
                result = field_value != "" and field_value is not None
            else:
                result = False
            
            results.append(result)
        
        if not results:
            return True
        
        if match_mode == "所有":
            return all(results)
        elif match_mode == "任一":
            return any(results)
        return True

    def evaluate_icon_conditions(row_data: dict, icon_item: dict) -> bool:
        logic_type = icon_item.get("logicType", "simple")

        if logic_type == "advanced":
            groups = icon_item.get("groups", [])
            if not groups:
                return True
            group_results = []
            for group in groups:
                group_conditions = group.get("conditions", [])
                group_match_mode = group.get("matchMode", "所有")
                group_results.append(check_condition(row_data, group_conditions, group_match_mode))

            result = group_results[0]
            connectors = icon_item.get("groupConnectors", [])
            for i, connector in enumerate(connectors):
                if connector == "所有":
                    result = result and group_results[i + 1]
                else:
                    result = result or group_results[i + 1]
            return result

        conditions = icon_item.get("conditions", [])
        match_mode = icon_item.get("matchMode", "所有")
        return check_condition(row_data, conditions, match_mode)
    
    def _apply_font_style(c, font_family, font_weight, font_size, color_hex, item_opacity, italic=False):
        def _safe_set_font(name, size):
            try:
                c.setFont(name, size)
                return True
            except:
                return False

        if italic:
            if font_weight >= 600:
                candidates = [
                    font_family + "-BoldItalic", font_family + "-BoldOblique",
                    font_family + "-Italic", font_family + "-Oblique",
                    font_family + "-Bold", font_family, "微软雅黑",
                ]
            else:
                candidates = [
                    font_family + "-Italic", font_family + "-Oblique",
                    font_family, "微软雅黑",
                ]
        elif font_weight >= 600:
            candidates = [font_family + "-Bold", font_family, "微软雅黑"]
        else:
            candidates = [font_family, "微软雅黑"]

        applied_font = None
        real_italic_font = False
        for name in candidates:
            if _safe_set_font(name, font_size):
                applied_font = name
                real_italic_font = italic and ("Italic" in name or "Oblique" in name)
                break

        # 无真斜体字体（如楷体等中文字体）时用水平错切合成斜体
        if italic and not real_italic_font:
            # PDF 坐标系 y 轴向上，字形顶部向右侧倾斜，错切矩阵 c 项取正（约 12°）
            c.transform(1, 0, 0.21, 1, 0, 0)

        if item_opacity < 1.0:
            try:
                c.setFillAlpha(item_opacity)
            except:
                pass

        hex_str = color_hex.lstrip('#')
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        c.setFillColorRGB(r, g, b)
        return applied_font

    def _draw_centred_text(c, x, y, text, font_name, font_size):
        # 前端 canvas 使用 textBaseline='middle'（文字垂直居中于 y），
        # ReportLab drawCentredString 的 y 是基线，需向下偏移到基线位置
        offset = font_size * 0.30
        if font_name:
            try:
                ascent, descent = pdfmetrics.getAscentDescent(font_name, font_size)
                offset = (ascent + descent) / 2.0
            except:
                pass
        c.drawCentredString(x, y - offset, text)

    def render_icon_to_overlay(overlay_pdf, icon_item, row_data: dict, page_rot: int, crop, pdf_scale: float):
        mode = icon_item.get("mode")
        if mode not in ("single", "conditional"):
            return
        if mode == "conditional" and not evaluate_icon_conditions(row_data, icon_item):
            return

        pointer = icon_item.get("pointer", {})
        # 前端坐标与尺寸都基于 pdf_scale 缩放后的视口，统一除回 pdf_scale 得到 PDF 用户空间单位
        size = icon_item.get("size")
        if size is None:
            size = 40  # 与前端 getIconSize 默认值保持一致
        unit = size / pdf_scale
        client_x = pointer.get("clientX", 0) / pdf_scale
        client_y = pointer.get("clientY", 0) / pdf_scale
        icon_rotation = icon_item.get("rotation") or 0

        crop_left, crop_bottom, crop_right, crop_top = crop

        # pdf.js getViewport 基于 CropBox 且随 /Rotate 旋转，
        # 将前端视口坐标(左上原点)转换回未旋转的 PDF 坐标(左下原点)
        if page_rot == 90:
            x = crop_left + client_y
            y = crop_bottom + client_x
        elif page_rot == 180:
            x = crop_right - client_x
            y = crop_bottom + client_y
        elif page_rot == 270:
            x = crop_right - client_y
            y = crop_top - client_x
        else:
            x = crop_left + client_x
            y = crop_top - client_y

        option = icon_item.get("option", {})
        item_type = option.get("type")

        overlay_pdf.saveState()
        overlay_pdf.translate(x, y)
        # 前端 rotation 为屏幕顺时针角度；页面显示时会再顺时针旋转 page_rot，
        # 因此叠加层需预旋转 (page_rot - rotation) 度（ReportLab 逆时针为正）
        angle = (page_rot - icon_rotation) % 360
        if angle:
            overlay_pdf.rotate(angle)

        try:
            if item_type == "field":
                field_name = option.get("fieldName")
                font_family = option.get("fontFamily", "微软雅黑")
                font_weight = option.get("fontWeight", 400)
                font_italic = bool(option.get("italic", False))
                item_color = option.get("color", "#000000")
                item_opacity = option.get("opacity", 1.0)
                font_size = max(4, math.floor(unit * 0.3))
                if field_name and field_name in row_data:
                    field_value = str(row_data[field_name])
                    applied_font = _apply_font_style(overlay_pdf, font_family, font_weight, font_size, item_color, item_opacity, font_italic)
                    _draw_centred_text(overlay_pdf, 0, 0, field_value, applied_font, font_size)

            elif item_type == "text":
                text_value = option.get("text", "")
                font_family = option.get("fontFamily", "楷体")
                font_weight = option.get("fontWeight", 400)
                font_italic = bool(option.get("italic", False))
                text_color = option.get("color", "#000000")
                text_opacity = option.get("opacity", 1.0)
                font_size = max(4, math.floor(unit * 0.3))
                if text_value:
                    applied_font = _apply_font_style(overlay_pdf, font_family, font_weight, font_size, text_color, text_opacity, font_italic)
                    _draw_centred_text(overlay_pdf, 0, 0, text_value, applied_font, font_size)

            elif item_type == "image":
                src = option.get("src")
                if src:
                    src = src.strip()
                    if src.startswith("http://asset.localhost/"):
                        local_path = resolve_local_path_from_url(src)
                    else:
                        local_path = src

                    if Path(local_path).exists():
                        try:
                            # 相同图片在多行之间只读取解码一次
                            img = image_cache.get(local_path)
                            if img is None:
                                img = Image.open(local_path)
                                img.load()
                                image_cache[local_path] = img
                            img_width, img_height = img.size
                            img_ratio = img_width / img_height

                            # 印章关闭"锁定纵横比"时拉伸填满正方形区域，其余保持原始比例
                            keep_ratio = option.get("keepRatio", True)
                            stretch = option.get("imageKind") == "seal" and keep_ratio is False
                            if stretch:
                                render_width = unit
                                render_height = unit
                            elif img_ratio > 1:
                                render_width = unit
                                render_height = unit / img_ratio
                            else:
                                render_width = unit * img_ratio
                                render_height = unit

                            # 圆角：短边尺寸的百分比，与前端一致
                            corner_radius = float(option.get("cornerRadius", 0) or 0)
                            radius = min(
                                corner_radius / 100.0 * min(render_width, render_height),
                                render_width / 2,
                                render_height / 2,
                            )
                            img_opacity = float(option.get("opacity", 1.0) or 1.0)

                            overlay_pdf.saveState()
                            try:
                                if radius > 0:
                                    clip_path = overlay_pdf.beginPath()
                                    clip_path.roundRect(
                                        -render_width / 2, -render_height / 2,
                                        render_width, render_height, radius,
                                    )
                                    overlay_pdf.clipPath(clip_path, stroke=0, fill=0)
                                if img_opacity < 1.0:
                                    overlay_pdf.setFillAlpha(img_opacity)
                                image_reader = image_reader_cache.get(local_path)
                                if image_reader is None:
                                    image_reader = ImageReader(img)
                                    image_reader_cache[local_path] = image_reader
                                overlay_pdf.drawImage(
                                    image_reader,
                                    -render_width / 2, -render_height / 2,
                                    width=render_width,
                                    height=render_height,
                                    mask='auto'
                                )
                            finally:
                                overlay_pdf.restoreState()
                        except Exception as e:
                            print(f"图片渲染失败: {local_path}, {e}")

            elif item_type == "icon":
                icon_char = option.get("icon")
                if icon_char:
                    icon_color = option.get("color", "#000000")
                    icon_opacity = option.get("opacity", 1.0)
                    icon_size = max(6, math.floor(unit * 0.8))
                    applied_font = _apply_font_style(overlay_pdf, "Segoe UI Symbol", 400, icon_size, icon_color, icon_opacity)
                    _draw_centred_text(overlay_pdf, 0, 0, icon_char, applied_font, icon_size)
        finally:
            overlay_pdf.restoreState()
    
    image_cache: dict = {}
    image_reader_cache: dict = {}

    def sse_message(event_type: str, payload: dict) -> str:
        return "data: " + json.dumps({"type": event_type, **payload}, ensure_ascii=False) + "\n\n"

    def event_stream():
        try:
            total_rows = len(content)
            yield sse_message("start", {"total": total_rows})

            # ===== 预计算每页静态信息，并区分静态/动态图标 =====
            # 静态：single 且非字段类（签字/印章/图标/文本），渲染结果与行数据无关
            # 动态：字段类（值随行变化）或条件类（显隐随行变化），需逐行处理
            pages_meta = []
            for page_idx in range(pdf_page_count):
                src_page = pdf_reader.pages[page_idx]
                rotation = int(src_page.get('/Rotate', 0)) % 360
                cb = src_page.cropbox
                crop_box = (float(cb.left), float(cb.bottom), float(cb.right), float(cb.top))
                page_size = (float(src_page.mediabox.width), float(src_page.mediabox.height))

                page_icons = [ic for ic in icon_list_data if ic.get("pageIndex") == page_idx + 1]
                static_icons = [
                    ic for ic in page_icons
                    if ic.get("mode") == "single" and ic.get("option", {}).get("type") != "field"
                ]
                static_ids = {id(ic) for ic in static_icons}
                dynamic_icons = [ic for ic in page_icons if id(ic) not in static_ids]
                pages_meta.append({
                    "rotation": rotation,
                    "crop": crop_box,
                    "size": page_size,
                    "static": static_icons,
                    "dynamic": dynamic_icons,
                })

            def make_overlay_page(meta, icons):
                buf = io.BytesIO()
                c = canvas.Canvas(buf, pagesize=meta["size"])
                for icon_item in icons:
                    render_icon_to_overlay(
                        c, icon_item, {}, meta["rotation"], meta["crop"], pdf_scale
                    )
                c.save()
                buf.seek(0)
                return PdfReader(buf).pages[0]

            # ===== 1) 静态图标只渲染/合并一次，生成基础 PDF =====
            if any(m["static"] for m in pages_meta):
                base_writer = PdfWriter()
                base_writer.append(pdf_reader, import_outline=False)
                for page_idx, meta in enumerate(pages_meta):
                    if meta["static"]:
                        base_writer.pages[page_idx].merge_page(make_overlay_page(meta, meta["static"]))
                base_buf = io.BytesIO()
                base_writer.write(base_buf)
                base_buf.seek(0)
                base_reader = PdfReader(base_buf)
            else:
                base_reader = pdf_reader

            generated_files = []
            used_names = {}
            # 动态覆盖层按 (页, 可见集合+字段值) 签名缓存，内容相同的行直接复用
            overlay_cache: dict = {}

            # ===== 2) 逐行克隆基础 PDF，仅处理动态图标 =====
            for row_idx, row in enumerate(content):
                row_data = {headers[i]: row[i] for i in range(len(headers))}

                row_writer = PdfWriter()
                row_writer.append(base_reader, import_outline=False)

                for page_idx, meta in enumerate(pages_meta):
                    dynamic = meta["dynamic"]
                    if not dynamic:
                        continue

                    # 条件图标先评估显隐；single 字段图标始终显示
                    visible = [
                        ic for ic in dynamic
                        if ic.get("mode") != "conditional" or evaluate_icon_conditions(row_data, ic)
                    ]
                    if not visible:
                        continue

                    # 签名同时包含字段类图标的当前值（字段值随行变化）
                    sig = frozenset(
                        (
                            id(ic),
                            str(row_data.get(ic.get("option", {}).get("fieldName"), ""))
                            if ic.get("option", {}).get("type") == "field" else None,
                        )
                        for ic in visible
                    )
                    cache_key = (page_idx, sig)
                    overlay_page = overlay_cache.get(cache_key)
                    if overlay_page is None:
                        # 强制按 single 绘制（显隐已在外部判定），避免重复评估条件
                        forced = [{**ic, "mode": "single"} for ic in visible]
                        buf = io.BytesIO()
                        c = canvas.Canvas(buf, pagesize=meta["size"])
                        for icon_item in forced:
                            render_icon_to_overlay(
                                c, icon_item, row_data, meta["rotation"], meta["crop"], pdf_scale
                            )
                        c.save()
                        buf.seek(0)
                        overlay_page = PdfReader(buf).pages[0]
                        overlay_cache[cache_key] = overlay_page

                    row_writer.pages[page_idx].merge_page(overlay_page)

                base_name = build_filename(row_data, row_idx)
                if base_name in used_names:
                    used_names[base_name] += 1
                    base_name = f"{base_name}({used_names[base_name]})"
                else:
                    used_names[base_name] = 0
                output_path = target_dir / f"{base_name}.pdf"
                with open(output_path, "wb") as f:
                    row_writer.write(f)

                generated_files.append(str(output_path))
                yield sse_message("progress", {
                    "current": row_idx + 1,
                    "total": total_rows,
                })

            yield sse_message("done", {
                "msg": "PDF 已保存",
                "path": str(target_dir),
                "files": generated_files,
            })
        except Exception as error:
            yield sse_message("error", {"message": f"生成失败: {error}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)