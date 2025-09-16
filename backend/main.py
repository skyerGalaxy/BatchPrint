from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import batch_print

app = FastAPI()

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/save_config")
async def save_config(data: dict):
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"msg": "配置已保存"}

@app.post("/generate")
async def generate():
    batch_print.run()  # 调用批处理逻辑
    return {"msg": "生成完成"}
