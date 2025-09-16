import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io, json

def run():
    # 注册字体
    pdfmetrics.registerFont(TTFont("Handwriting", "Handwriting.ttf"))

    # 读取 Excel
    df = pd.read_excel("data.xlsx")

    # 读取坐标配置
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    for i, row in df.iterrows():
        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=A4)
        c.setFont("Handwriting", 22)

        # 根据配置写入
        for field, pos in config.items():
            x, y = pos
            c.drawString(x, y, str(row[field]))

        c.save()
        packet.seek(0)

        # 合并到模板
        template = PdfReader("template.pdf")
        overlay = PdfReader(packet)

        output = PdfWriter()
        page = template.pages[0]
        page.merge_page(overlay.pages[0])
        output.add_page(page)

        with open(f"output_{row['户主姓名']}.pdf", "wb") as f:
            output.write(f)
