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

# 获取项目根目录下的 fonts 路径
def get_fonts_dir():
    # 假设 backend 在项目根目录下
    current_file = Path(__file__)
    project_root = current_file.parent.parent
    return project_root / "fonts"

def register_custom_fonts():
    fonts_dir = get_fonts_dir()
    fonts_json = fonts_dir / "fonts.json"

    if not fonts_json.exists():
        return

    try:
        with open(fonts_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as error:
        print(f"读取字体配置失败: {error}")
        return

    system_font_map = {
        "微软雅黑": "msyh.ttc",
        "宋体": "simsun.ttc",
        "黑体": "simhei.ttc",
    }

    if os.name == "nt":
        windows_fonts_dir = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts"
        for font in data.get("fonts", []):
            font_name = font.get("value") or font.get("name")
            font_type = font.get("type")
            
            if font_name in pdfmetrics.getRegisteredFontNames():
                continue
            
            if font_type == "custom":
                font_path = fonts_dir / font.get("file", "")
                if font_path.exists():
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
                    except Exception as error:
                        print(f"注册自定义字体失败: {font_name}, {error}")
            
            elif font_type == "system" and font_name in system_font_map:
                font_file = system_font_map[font_name]
                font_path = windows_fonts_dir / font_file
                if font_path.exists():
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
                    except Exception as error:
                        print(f"注册系统字体失败: {font_name}, {error}")

@app.get("/api/fonts")
async def get_fonts_list(request: Request):
    """获取字体列表及其文件路径"""
    fonts_dir = get_fonts_dir()
    fonts_json = fonts_dir / "fonts.json"
    
    if not fonts_json.exists():
        return {"fonts": []}
    
    with open(fonts_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 为每个自定义字体添加文件信息
    base_url = str(request.base_url).rstrip("/")
    for font in data.get("fonts", []):
        if font.get("type") == "custom" and "file" in font:
            font_file = fonts_dir / font["file"]
            if font_file.exists():
                encoded_filename = quote(font["file"], safe='')
                font["url"] = f"{base_url}/api/fonts/file/{encoded_filename}"
    return data

@app.get("/api/fonts/file/{filename}")
async def get_font_file(filename: str):
    """获取字体文件(用于前端加载)"""
    # 解码 URL 编码的文件名
    decoded_filename = unquote(filename)
    
    fonts_dir = get_fonts_dir()
    font_path = fonts_dir / decoded_filename
    
    # 安全检查,防止路径遍历攻击
    if not font_path.exists() or not str(font_path).startswith(str(fonts_dir)):
        return {"error": "字体文件不存在"}
    
    return FileResponse(
        font_path,
        media_type="application/octet-stream",
        filename=decoded_filename
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
                if field_name and field_name in row_data:
                    field_value = str(row_data[field_name])
                    overlay_pdf.setFont(font_family, font_size)
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
        
        elif mode == "conditional":
            conditions = icon_item.get("conditions", [])
            match_mode = icon_item.get("matchMode", "所有")
            
            if check_condition(row_data, conditions, match_mode):
                option = icon_item.get("option", {})
                item_type = option.get("type")
                
                if item_type == "field":
                    field_name = option.get("fieldName")
                    font_family = option.get("fontFamily", "微软雅黑")
                    if field_name and field_name in row_data:
                        field_value = str(row_data[field_name])
                        overlay_pdf.setFont(font_family, font_size)
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
    

