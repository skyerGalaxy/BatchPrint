from importlib.readers import FileReader
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import pandas as pd
import json
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

app = FastAPI()

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
    
    def _apply_font_style(c, font_family, font_weight, font_size, color_hex, item_opacity):
        def _safe_set_font(name, size):
            try:
                c.setFont(name, size)
                return True
            except:
                return False

        if font_weight >= 600:
            bold_name = font_family + "-Bold"
            if not _safe_set_font(bold_name, font_size):
                if not _safe_set_font(font_family, font_size):
                    _safe_set_font("微软雅黑", font_size)
        else:
            if not _safe_set_font(font_family, font_size):
                _safe_set_font("微软雅黑", font_size)

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

    def render_icon_to_overlay(overlay_pdf, icon_item, row_data: dict, overlay_height: float):
        from reportlab.lib.utils import ImageReader
        
        mode = icon_item.get("mode")
        pointer = icon_item.get("pointer", {})
        client_x = pointer.get("clientX", 0)
        client_y = pointer.get("clientY", 0)
        size = icon_item.get("size", 150)
        
        x = client_x
        y = overlay_height - client_y
        
        font_size = max(8, size * 0.3)
        
        if mode == "single":
            option = icon_item.get("option", {})
            item_type = option.get("type")
            
            if item_type == "field":
                field_name = option.get("fieldName")
                font_family = option.get("fontFamily", "微软雅黑")
                font_weight = option.get("fontWeight", 400)
                item_color = option.get("color", "#000000")
                item_opacity = option.get("opacity", 1.0)
                if field_name and field_name in row_data:
                    field_value = str(row_data[field_name])
                    _apply_font_style(overlay_pdf, font_family, font_weight, font_size, item_color, item_opacity)
                    overlay_pdf.drawCentredString(x, y, field_value)
            
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
                            img = Image.open(local_path)
                            img_width, img_height = img.size
                            img_ratio = img_width / img_height
                            if img_ratio > 1:
                                render_width = size
                                render_height = size / img_ratio
                            else:
                                render_width = size * img_ratio
                                render_height = size
                            
                            overlay_pdf.drawImage(
                                ImageReader(local_path),
                                x - render_width / 2, y - render_height / 2,
                                width=render_width,
                                height=render_height,
                                mask='auto'
                            )
                        except Exception as e:
                            print(f"图片渲染失败: {local_path}, {e}")
            
            elif item_type == "icon":
                icon_char = option.get("icon")
                if icon_char:
                    icon_color = option.get("color", "#000000")
                    icon_opacity = option.get("opacity", 1.0)
                    icon_size = max(12, size * 0.8)
                    _apply_font_style(overlay_pdf, "Segoe UI Symbol", 400, icon_size, icon_color, icon_opacity)
                    overlay_pdf.drawCentredString(x, y, icon_char)
        
        elif mode == "conditional":
            if evaluate_icon_conditions(row_data, icon_item):
                option = icon_item.get("option", {})
                item_type = option.get("type")
                
                if item_type == "field":
                    field_name = option.get("fieldName")
                    font_family = option.get("fontFamily", "微软雅黑")
                    font_weight = option.get("fontWeight", 400)
                    item_color = option.get("color", "#000000")
                    item_opacity = option.get("opacity", 1.0)
                    if field_name and field_name in row_data:
                        field_value = str(row_data[field_name])
                        _apply_font_style(overlay_pdf, font_family, font_weight, font_size, item_color, item_opacity)
                        overlay_pdf.drawCentredString(x, y, field_value)
                
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
                                img = Image.open(local_path)
                                img_width, img_height = img.size
                                img_ratio = img_width / img_height
                                if img_ratio > 1:
                                    render_width = size
                                    render_height = size / img_ratio
                                else:
                                    render_width = size * img_ratio
                                    render_height = size
                                
                                overlay_pdf.drawImage(
                                    ImageReader(local_path),
                                    x - render_width / 2, y - render_height / 2,
                                    width=render_width,
                                    height=render_height,
                                    mask='auto'
                                )
                            except Exception as e:
                                print(f"图片渲染失败: {local_path}, {e}")
                
                elif item_type == "icon":
                    icon_char = option.get("icon")
                    if icon_char:
                        icon_color = option.get("color", "#000000")
                        icon_opacity = option.get("opacity", 1.0)
                        icon_size = max(12, size * 0.8)
                        _apply_font_style(overlay_pdf, "Segoe UI Symbol", 400, icon_size, icon_color, icon_opacity)
                        overlay_pdf.drawCentredString(x, y, icon_char)
    
    generated_files = []
    
    for row_idx, row in enumerate(content):
        row_data = {headers[i]: row[i] for i in range(len(headers))}
        
        row_writer = PdfWriter()
        
        for page_idx in range(pdf_page_count):
            source_reader = PdfReader(io.BytesIO(pdf_content))
            original_page = source_reader.pages[page_idx]
            
            scaled_width = original_page.mediabox.width * pdf_scale
            scaled_height = original_page.mediabox.height * pdf_scale
            
            original_page.scale(pdf_scale, pdf_scale)
            
            icons_on_page = [icon for icon in icon_list_data if icon.get("pageIndex") == page_idx + 1]
            
            if icons_on_page:
                overlay_buffer = io.BytesIO()
                c = canvas.Canvas(overlay_buffer, pagesize=(scaled_width, scaled_height))
                
                for icon_item in icons_on_page:
                    render_icon_to_overlay(c, icon_item, row_data, scaled_height)
                
                c.save()
                overlay_buffer.seek(0)
                
                overlay_reader = PdfReader(overlay_buffer)
                overlay_page = overlay_reader.pages[0]
                
                original_page.merge_page(overlay_page)
            
            original_page.scale(1/pdf_scale, 1/pdf_scale)
            row_writer.add_page(original_page)
        
        output_filename = f"{row_idx + 1}.pdf"
        output_path = target_dir / output_filename
        with open(output_path, "wb") as f:
            row_writer.write(f)
        
        generated_files.append(str(output_path))
    
    return {"msg": "PDF 已保存", "path": str(target_dir), "files": generated_files}
    

