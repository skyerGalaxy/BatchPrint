import json
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class FontManager:
    """后端字体管理"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.fonts_dir = self.project_root / "fonts"
        self.fonts_config = self._load_fonts_config()
        self.registered_fonts = {}
    
    def _load_fonts_config(self) -> dict:
        """加载 fonts.json 配置"""
        fonts_json = self.fonts_dir / "fonts.json"
        if fonts_json.exists():
            with open(fonts_json, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"fonts": []}
    
    def register_fonts(self):
        """注册所有自定义字体"""
        for font_info in self.fonts_config.get("fonts", []):
            if font_info.get("type") == "custom" and "file" in font_info:
                try:
                    font_file = self.fonts_dir / font_info["file"]
                    if font_file.exists():
                        pdfmetrics.registerFont(
                            TTFont(font_info["value"], str(font_file))
                        )
                        self.registered_fonts[font_info["value"]] = str(font_file)
                        print(f"字体注册成功: {font_info['name']} -> {font_file}")
                except Exception as e:
                    print(f"字体注册失败: {font_info['name']}, 错误: {e}")
    
    def get_font_name(self, font_display_name: str) -> str:
        """根据显示名称获取可用的字体"""
        # 查找对应的字体
        for font_info in self.fonts_config.get("fonts", []):
            if font_info.get("name") == font_display_name:
                return font_info.get("value", "Helvetica")
        
        # 如果找不到,返回默认字体
        return "Helvetica"

# 全局字体管理器
font_manager = FontManager()
