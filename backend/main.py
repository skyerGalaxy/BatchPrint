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
from pypdf import PdfReader, PdfWriter
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