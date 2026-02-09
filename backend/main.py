from fastapi import FastAPI, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import json
from pathlib import Path
from urllib.parse import quote
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
