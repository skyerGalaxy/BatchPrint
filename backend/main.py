from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import pandas as pd
import json
from pathlib import Path
from urllib.parse import quote
import io
import zipfile
from PIL import Image
import base64
# import batch_print

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
    from urllib.parse import unquote
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
    headers = df.columns.tolist()
    # 获取内容并返回
    content = df.values.tolist()
    return {"headers": headers, "content": content}


@app.post("/generate_batch_pdf")
async def generate_batch_pdf(
    pdf_file: UploadFile = File(...),
    excel_file: UploadFile = File(...),
    icon_list: str = ""
):
    """
    批量生成PDF
    
    参数:
    - pdf_file: PDF模板文件
    - excel_file: Excel数据文件
    - icon_list: JSON格式的图标列表
      每个icon包含:
      - id: 图标ID
      - matchMode: "single"表示单一模式，其他值表示条件模式
      - option: {type: "field"或"image", ...}
      - pageIndex: 页码
      - pointer: {clientX, clientY} 坐标
      - conditions: 条件数组（仅条件模式有）
    """
    try:
        from PyPDF2 import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas
        import requests
        import tempfile
        import os
        
        # 读取Excel数据
        df = pd.read_excel(excel_file.file)
        excel_data = df.to_dict('records')
        
        # 解析icon_list
        icon_list_data = json.loads(icon_list) if icon_list else []
        
        print(f"接收到的icon_list: {json.dumps(icon_list_data, ensure_ascii=False, indent=2)}")
        print(f"Excel数据行数: {len(excel_data)}")
        
        # 读取PDF模板
        pdf_content = await pdf_file.read()
        pdf_reader = PdfReader(io.BytesIO(pdf_content))
        
        # 获取PDF页面尺寸
        first_page = pdf_reader.pages[0]
        page_width = float(first_page.mediabox.width)
        page_height = float(first_page.mediabox.height)
        
        print(f"PDF尺寸: {page_width} x {page_height}")
        
        # 生成输出文件的ZIP
        output_zip = io.BytesIO()
        
        # 创建临时目录存储字体和图片
        temp_dir = tempfile.mkdtemp()
        
        try:
            with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # 为每一行Excel数据生成一个PDF
                for row_idx, row_data in enumerate(excel_data, 1):
                    print(f"\n处理第 {row_idx} 行数据: {row_data}")
                    
                    pdf_writer = PdfWriter()
                    
                    # 复制PDF的所有页面到writer
                    for page in pdf_reader.pages:
                        pdf_writer.add_page(page)
                    
                    # 创建一个覆盖层，用于添加文本和图片
                    packet = io.BytesIO()
                    can = canvas.Canvas(packet, pagesize=(page_width, page_height))
                    
                    # 遍历icon_list，在PDF上添加内容
                    for icon in icon_list_data:
                        match_mode = icon.get('matchMode', '')
                        option = icon.get('option', {})
                        pointer = icon.get('pointer', {})
                        page_index = icon.get('pageIndex', 1)
                        
                        # 获取坐标
                        x = pointer.get('clientX', 0)
                        y = page_height - pointer.get('clientY', 0)  # PDF坐标系Y轴是从下往上
                        
                        # 判断是否应该渲染此icon
                        should_render = False
                        
                        if match_mode == 'single':
                            # 单一模式，直接渲染
                            should_render = True
                        else:
                            # 条件模式，检查conditions
                            conditions = icon.get('conditions', [])
                            should_render = evaluate_conditions(row_data, conditions)
                        
                        if should_render:
                            option_type = option.get('type', '')
                            
                            if option_type == 'field':
                                # 渲染文字
                                field_name = option.get('fieldName', '')
                                font_family = option.get('fontFamily', 'Helvetica')
                                font_size = option.get('size', 12)
                                
                                # 获取字段值
                                field_value = row_data.get(field_name, '')
                                
                                print(f"  渲染文字: {field_name}={field_value} at ({x}, {y}), 字体:{font_family}, 大小:{font_size}")
                                
                                # 设置字体（如果是中文字体，需要注册TTF）
                                try:
                                    can.setFont(font_family, font_size)
                                except:
                                    # 如果字体不存在，使用默认字体
                                    can.setFont("Helvetica", font_size)
                                
                                can.drawString(x, y, str(field_value))
                            
                            elif option_type == 'image':
                                # 渲染图片
                                image_src = option.get('src', '')
                                
                                print(f"  渲染图片: {image_src} at ({x}, {y})")
                                
                                if image_src:
                                    try:
                                        # 下载图片
                                        if image_src.startswith('http'):
                                            response = requests.get(image_src, timeout=10)
                                            img_data = response.content
                                        else:
                                            # 本地文件
                                            with open(image_src, 'rb') as f:
                                                img_data = f.read()
                                        
                                        # 保存到临时文件
                                        temp_img_path = os.path.join(temp_dir, f"img_{row_idx}_{icon.get('id')}.png")
                                        with open(temp_img_path, 'wb') as f:
                                            f.write(img_data)
                                        
                                        # 获取图片尺寸
                                        img = Image.open(io.BytesIO(img_data))
                                        img_width, img_height = img.size
                                        
                                        # 使用icon的size或默认大小
                                        icon_size = icon.get('size', 50)
                                        scale = icon_size / max(img_width, img_height)
                                        draw_width = img_width * scale
                                        draw_height = img_height * scale
                                        
                                        can.drawImage(temp_img_path, x, y - draw_height, 
                                                    width=draw_width, height=draw_height, 
                                                    preserveAspectRatio=True)
                                    except Exception as img_error:
                                        print(f"    图片加载失败: {img_error}")
                    
                    can.save()
                    packet.seek(0)
                    
                    # 将覆盖层添加到PDF
                    overlay_reader = PdfReader(packet)
                    first_page = pdf_writer.pages[0]
                    first_page.merge_page(overlay_reader.pages[0])
                    
                    # 输出PDF到ZIP
                    output_pdf = io.BytesIO()
                    pdf_writer.write(output_pdf)
                    pdf_filename = f"output_{row_idx:04d}.pdf"
                    zip_file.writestr(pdf_filename, output_pdf.getvalue())
                    
                    print(f"  生成PDF: {pdf_filename}")
        
        finally:
            # 清理临时目录
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        output_zip.seek(0)
        
        return StreamingResponse(
            iter([output_zip.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=batch_pdfs.zip"}
        )
    
    except ImportError as e:
        error_msg = f"缺少必要的库: {str(e)}"
        print(error_msg)
        return {"success": False, "message": error_msg}
    except Exception as e:
        import traceback
        error_msg = f"生成PDF失败: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return {"success": False, "message": error_msg}


def evaluate_conditions(data: dict, conditions: list) -> bool:
    """
    评估条件数组
    conditions是一个数组，每个元素是一个条件组（字典）
    条件组中的每个条件都需要满足（AND关系）
    """
    if not conditions:
        return False
    
    try:
        for condition_group in conditions:
            # condition_group 是一个字典，如 {0: {...}, 1: {...}}
            all_match = True
            for key, condition in condition_group.items():
                # 每个condition可能包含字段和值的比较
                # 这里需要根据实际的condition结构来实现
                # 暂时简单实现：检查condition是否为空
                if isinstance(condition, dict) and condition:
                    # 可以在这里添加更复杂的条件判断逻辑
                    pass
            
            if all_match:
                return True
        
        return False
    except Exception as e:
        print(f"条件评估失败: {e}")
        return False
