/**
 * 字体加载工具
 * 自动从后端获取字体列表和文件,加载到 Canvas
 */

interface Font {
  name: string;
  value: string;
  type: 'system' | 'custom';
  file?: string;
  url?: string;
}

interface FontsData {
  fonts: Font[];
}

// 缓存字体列表
let fontsCache: Font[] | null = null;
const loadedFonts = new Set<string>(); // 已加载的字体

/**
 * 从后端获取字体列表和信息
 */
export async function fetchFontsList(fontsPath?: string): Promise<Font[]> {
  if (fontsCache) {
    return fontsCache;
  }

  try {
    let url = 'http://localhost:8000/api/fonts';
    if (fontsPath) {
      url += `?fonts_path=${encodeURIComponent(fontsPath + '/fonts')}`;
    }
    const response = await fetch(url);
    const data: FontsData = await response.json();
    fontsCache = data.fonts || [];
    console.log('字体列表已加载:', fontsCache);
    return fontsCache;
  } catch (error) {
    console.error('获取字体列表失败:', error);
    return [
      { name: '微软雅黑', value: '微软雅黑', type: 'system' },
      { name: '宋体', value: '宋体', type: 'system' },
      { name: '黑体', value: '黑体', type: 'system' },
    ];
  }
}

/**
 * 加载所有自定义字体到 Canvas
 */
export async function loadCustomFonts(fontsPath?: string): Promise<void> {
  try {
    const fonts = await fetchFontsList(fontsPath);

    // 过滤出需要加载的自定义字体
    const customFonts = fonts.filter(f => f.type === 'custom' && f.url);

    const loadPromises = customFonts.map(async (font) => {
      // 避免重复加载
      if (loadedFonts.has(font.value)) {
        return;
      }

      try {
        const fontFace = new FontFace(
          font.value,
          `url(${font.url})`,
          { display: 'swap' }
        );

        const loadedFont = await fontFace.load();
        document.fonts.add(loadedFont);
        loadedFonts.add(font.value);
        console.log(`字体加载成功: `,fontFace);
      } catch (error) {
        console.warn(`字体加载失败: ${font.name}`, error);
      }
    });

    await Promise.all(loadPromises);
    console.log('所有自定义字体加载完成');
  } catch (error) {
    console.error('加载字体过程出错:', error);
  }
}

/**
 * 获取字体显示名称列表(用于 MaterialPanel)
 */
export async function getFontDisplayNames(fontsPath?: string): Promise<string[]> {
  try {
    const fonts = await fetchFontsList(fontsPath);
    return fonts.map(f => f.name);
  } catch (error) {
    console.error('获取字体显示名称失败:', error);
    return ['微软雅黑', '宋体', '黑体', 'Arial', 'Times New Roman'];
  }
}

/**
 * 获取完整的字体列表(用于需要name和value的场景)
 */
export async function getFontsList(fontsPath?: string): Promise<Font[]> {
  return await fetchFontsList(fontsPath);
}

/**
 * 通过显示名称获取字体值
 */
export async function getFontValueByName(displayName: string, fontsPath?: string): Promise<string> {
  try {
    const fonts = await fetchFontsList(fontsPath);
    const font = fonts.find(f => f.name === displayName);
    return font?.value || displayName;
  } catch (error) {
    return displayName;
  }
}
