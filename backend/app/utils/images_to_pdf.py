# -*- coding: utf-8 -*-
"""
图片合并为PDF工具
使用PyMuPDF将多个图片合并成一个PDF文件
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Optional, Tuple, Literal
import logging

logger = logging.getLogger(__name__)

# 预设页面尺寸（单位：点，72 DPI）
PAGE_SIZES = {
    'A4': (595, 842),      # 210mm x 297mm (竖版)
    'A4-Landscape': (842, 595),  # 297mm x 210mm (横版)
    'A3': (842, 1191),     # 297mm x 420mm (竖版)
    'A3-Landscape': (1191, 842),  # 420mm x 297mm (横版)
    'A5': (420, 595),      # 148mm x 210mm (竖版)
    'A5-Landscape': (595, 420),  # 210mm x 148mm (横版)
    'Letter': (612, 792),  # 8.5" x 11" (竖版)
    'Letter-Landscape': (792, 612),  # 11" x 8.5" (横版)
    'Legal': (612, 1008),  # 8.5" x 14" (竖版)
    'Legal-Landscape': (1008, 612),  # 14" x 8.5" (横版)
    'Tabloid': (792, 1224), # 11" x 17"
}


def calculate_image_rect(
    img_width: float,
    img_height: float,
    page_width: float,
    page_height: float,
    fit_mode: Literal["fit", "stretch", "center", "custom"] = "fit",
    custom_rect: Optional[Tuple[float, float, float, float]] = None,
    margin: float = 0
) -> fitz.Rect:
    """
    计算图片在页面中的位置和尺寸
    
    Args:
        img_width: 图片原始宽度
        img_height: 图片原始高度
        page_width: 页面宽度
        page_height: 页面高度
        fit_mode: 适应模式
            - "fit": 保持比例，适应页面（默认）
            - "stretch": 拉伸填满页面（不保持比例）
            - "center": 保持原始尺寸，居中显示
            - "custom": 使用自定义尺寸和位置
        custom_rect: 自定义矩形 (x0, y0, x1, y1)，仅在fit_mode="custom"时使用
        margin: 边距（点），仅在fit_mode="fit"时使用
    
    Returns:
        fitz.Rect: 图片在页面中的矩形区域
    """
    available_width = page_width - 2 * margin
    available_height = page_height - 2 * margin
    
    if fit_mode == "fit":
        # 保持比例，适应可用区域
        scale_w = available_width / img_width
        scale_h = available_height / img_height
        scale = min(scale_w, scale_h)
        
        scaled_width = img_width * scale
        scaled_height = img_height * scale
        
        # 居中
        x0 = margin + (available_width - scaled_width) / 2
        y0 = margin + (available_height - scaled_height) / 2
        x1 = x0 + scaled_width
        y1 = y0 + scaled_height
        
    elif fit_mode == "stretch":
        # 拉伸填满页面（不保持比例）
        x0 = margin
        y0 = margin
        x1 = page_width - margin
        y1 = page_height - margin
        
    elif fit_mode == "center":
        # 保持原始尺寸，居中显示
        x0 = (page_width - img_width) / 2
        y0 = (page_height - img_height) / 2
        x1 = x0 + img_width
        y1 = y0 + img_height
        
    elif fit_mode == "custom":
        # 使用自定义尺寸和位置
        if custom_rect is None:
            raise ValueError("custom_mode需要提供custom_rect参数")
        x0, y0, x1, y1 = custom_rect
        
    else:
        raise ValueError(f"不支持的适应模式: {fit_mode}")
    
    return fitz.Rect(x0, y0, x1, y1)


def images_to_pdf(
    image_paths: List[str],
    output_pdf_path: str,
    page_size: Optional[Tuple[float, float]] = None,
    page_size_preset: Optional[str] = None,
    fit_mode: Literal["fit", "stretch", "center", "custom"] = "fit",
    margin: float = 0,
    custom_settings: Optional[List[dict]] = None
) -> str:
    """
    将多个图片合并为一个PDF文件
    
    Args:
        image_paths: 图片文件路径列表
        output_pdf_path: 输出PDF文件路径
        page_size: 自定义页面尺寸 (width, height)，单位：点（72 DPI）
        page_size_preset: 预设页面尺寸，可选值：'A4', 'A3', 'A5', 'Letter', 'Legal', 'Tabloid'
        fit_mode: 适应模式
            - "fit": 保持比例，适应页面（默认）
            - "stretch": 拉伸填满页面（不保持比例）
            - "center": 保持原始尺寸，居中显示
            - "custom": 每张图片使用custom_settings中的设置
        margin: 边距（点），默认0
        custom_settings: 每张图片的自定义设置列表
    
    Returns:
        str: 生成的PDF文件路径
    """
    pdf_doc = fitz.open()
    
    try:
        for idx, image_path in enumerate(image_paths):
            image_path = Path(image_path)
            if not image_path.exists():
                logger.warning(f"图片文件不存在，跳过: {image_path}")
                continue
            
            # 获取图片信息
            img_doc = fitz.open(str(image_path))
            img_rect = img_doc[0].rect
            img_width = img_rect.width
            img_height = img_rect.height
            img_doc.close()
            
            # 确定当前图片的设置
            if fit_mode == "custom" and custom_settings and idx < len(custom_settings):
                # 使用自定义设置
                settings = custom_settings[idx]
                current_page_size = settings.get("page_size")
                current_fit_mode = settings.get("fit_mode", "fit")
                current_margin = settings.get("margin", 0)
                current_custom_rect = settings.get("custom_rect")
            else:
                # 使用全局设置
                current_page_size = page_size_preset or page_size
                current_fit_mode = fit_mode
                current_margin = margin
                current_custom_rect = None
            
            # 确定页面尺寸
            if isinstance(current_page_size, str):
                # 预设尺寸
                if current_page_size not in PAGE_SIZES:
                    raise ValueError(f"不支持的预设尺寸: {current_page_size}")
                page_width, page_height = PAGE_SIZES[current_page_size]
            elif isinstance(current_page_size, (tuple, list)) and len(current_page_size) == 2:
                # 自定义尺寸
                page_width, page_height = current_page_size
            elif page_size_preset:
                # 使用全局预设
                page_width, page_height = PAGE_SIZES[page_size_preset]
            elif page_size:
                # 使用全局自定义尺寸
                page_width, page_height = page_size
            else:
                # 使用图片原始尺寸
                page_width = img_width
                page_height = img_height
            
            # 创建页面
            pdf_page = pdf_doc.new_page(width=page_width, height=page_height)
            
            # 计算图片位置和尺寸
            img_rect = calculate_image_rect(
                img_width, img_height,
                page_width, page_height,
                fit_mode=current_fit_mode,
                custom_rect=current_custom_rect,
                margin=current_margin
            )
            
            # 插入图片
            pdf_page.insert_image(img_rect, filename=str(image_path))
            
            logger.debug(f"已添加图片: {image_path.name}, 页面尺寸: {page_width}x{page_height}, "
                        f"适应模式: {current_fit_mode}, 图片区域: {img_rect}")
        
        # 保存PDF
        pdf_doc.save(output_pdf_path)
        logger.info(f"PDF已生成: {output_pdf_path}, 共 {len(pdf_doc)} 页")
        return output_pdf_path
        
    except Exception as e:
        logger.error(f"合并图片为PDF失败: {str(e)}")
        raise
    finally:
        pdf_doc.close()

