# -*- coding: utf-8 -*-
"""
图片合并为PDF示例
使用PyMuPDF将多个图片合并成一个PDF文件

支持功能：
1. 多种适应模式：适应、拉伸、居中、自定义
2. 预设页面尺寸：A4, A3, Letter等
3. 自定义页面尺寸
4. 每张图片单独设置尺寸和位置
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Optional, Tuple, Literal
import logging

logger = logging.getLogger(__name__)

# 预设页面尺寸（单位：点，72 DPI）
PAGE_SIZES = {
    'A4': (595, 842),      # 210mm x 297mm
    'A3': (842, 1191),     # 297mm x 420mm
    'A5': (420, 595),      # 148mm x 210mm
    'Letter': (612, 792),  # 8.5" x 11"
    'Legal': (612, 1008),  # 8.5" x 14"
    'Tabloid': (792, 1224), # 11" x 17"
}


def images_to_pdf_method1(
    image_paths: List[str],
    output_pdf_path: str,
    page_size: Optional[tuple] = None
) -> str:
    """
    方法1：使用 fitz.open(image_file) + show_pdf_page()
    适合：图片尺寸不统一，需要保持原始尺寸
    
    Args:
        image_paths: 图片文件路径列表
        output_pdf_path: 输出PDF文件路径
        page_size: 页面尺寸 (width, height)，如果为None则使用图片原始尺寸
    
    Returns:
        str: 生成的PDF文件路径
    """
    pdf_doc = fitz.open()
    
    try:
        for image_path in image_paths:
            image_path = Path(image_path)
            if not image_path.exists():
                logger.warning(f"图片文件不存在，跳过: {image_path}")
                continue
            
            # 打开图片文件
            img_doc = fitz.open(str(image_path))
            
            try:
                # 获取图片尺寸
                img_rect = img_doc[0].rect
                
                # 确定页面尺寸
                if page_size:
                    width, height = page_size
                else:
                    width = img_rect.width
                    height = img_rect.height
                
                # 创建新页面
                pdf_page = pdf_doc.new_page(width=width, height=height)
                
                # 在页面上显示图片
                pdf_page.show_pdf_page(img_rect, img_doc, 0)
                
                logger.debug(f"已添加图片: {image_path.name}")
            finally:
                img_doc.close()
        
        # 保存PDF
        pdf_doc.save(output_pdf_path)
        logger.info(f"PDF已生成: {output_pdf_path}, 共 {len(pdf_doc)} 页")
        return output_pdf_path
        
    except Exception as e:
        logger.error(f"合并图片为PDF失败: {str(e)}")
        raise
    finally:
        pdf_doc.close()


def images_to_pdf_method2(
    image_paths: List[str],
    output_pdf_path: str,
    page_size: Optional[tuple] = None,
    fit_to_page: bool = True
) -> str:
    """
    方法2：使用 page.insert_image()
    适合：需要统一页面尺寸，或需要调整图片大小
    
    Args:
        image_paths: 图片文件路径列表
        output_pdf_path: 输出PDF文件路径
        page_size: 页面尺寸 (width, height)，如果为None则使用A4尺寸 (595, 842)
        fit_to_page: 是否将图片适应页面大小，True=适应，False=保持原始尺寸
    
    Returns:
        str: 生成的PDF文件路径
    """
    pdf_doc = fitz.open()
    
    # 默认A4尺寸 (72 DPI)
    if page_size is None:
        page_size = (595, 842)  # A4: 210mm x 297mm at 72 DPI
    
    width, height = page_size
    
    try:
        for image_path in image_paths:
            image_path = Path(image_path)
            if not image_path.exists():
                logger.warning(f"图片文件不存在，跳过: {image_path}")
                continue
            
            # 创建新页面
            pdf_page = pdf_doc.new_page(width=width, height=height)
            
            # 确定图片插入区域
            if fit_to_page:
                # 适应页面大小
                rect = fitz.Rect(0, 0, width, height)
            else:
                # 保持原始尺寸（居中显示）
                # 需要先获取图片尺寸
                img_doc = fitz.open(str(image_path))
                img_rect = img_doc[0].rect
                img_doc.close()
                
                # 计算居中位置
                x0 = (width - img_rect.width) / 2
                y0 = (height - img_rect.height) / 2
                x1 = x0 + img_rect.width
                y1 = y0 + img_rect.height
                rect = fitz.Rect(x0, y0, x1, y1)
            
            # 插入图片
            pdf_page.insert_image(rect, filename=str(image_path))
            
            logger.debug(f"已添加图片: {image_path.name}")
        
        # 保存PDF
        pdf_doc.save(output_pdf_path)
        logger.info(f"PDF已生成: {output_pdf_path}, 共 {len(pdf_doc)} 页")
        return output_pdf_path
        
    except Exception as e:
        logger.error(f"合并图片为PDF失败: {str(e)}")
        raise
    finally:
        pdf_doc.close()


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


def images_to_pdf_advanced(
    image_paths: List[str],
    output_pdf_path: str,
    page_size: Optional[Tuple[float, float]] = None,
    page_size_preset: Optional[str] = None,
    fit_mode: Literal["fit", "stretch", "center", "custom"] = "fit",
    margin: float = 0,
    custom_settings: Optional[List[dict]] = None
) -> str:
    """
    将多个图片合并为一个PDF文件（高级版本，支持自定义调整）
    
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
        custom_settings: 每张图片的自定义设置列表，格式：
            [
                {
                    "page_size": (width, height) 或 "A4"等,
                    "fit_mode": "fit" | "stretch" | "center" | "custom",
                    "custom_rect": (x0, y0, x1, y1),  # 仅当fit_mode="custom"时使用
                    "margin": 0
                },
                ...
            ]
    
    Returns:
        str: 生成的PDF文件路径
    
    Example:
        # 示例1：统一A4尺寸，所有图片适应页面
        images_to_pdf_advanced(
            ["img1.png", "img2.jpg"],
            "output.pdf",
            page_size_preset="A4",
            fit_mode="fit",
            margin=20
        )
        
        # 示例2：每张图片使用不同设置
        images_to_pdf_advanced(
            ["img1.png", "img2.jpg"],
            "output.pdf",
            fit_mode="custom",
            custom_settings=[
                {"page_size": "A4", "fit_mode": "fit", "margin": 20},
                {"page_size": (800, 600), "fit_mode": "stretch", "margin": 0}
            ]
        )
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


def images_to_pdf(
    image_paths: List[str],
    output_pdf_path: str,
    page_size: Optional[tuple] = None,
    method: str = "auto"
) -> str:
    """
    将多个图片合并为一个PDF文件（简单版本，向后兼容）
    
    Args:
        image_paths: 图片文件路径列表
        output_pdf_path: 输出PDF文件路径
        page_size: 页面尺寸 (width, height)，如果为None则使用图片原始尺寸
        method: 合并方法，"auto"=自动选择，"method1"=保持原始尺寸，"method2"=统一页面尺寸
    
    Returns:
        str: 生成的PDF文件路径
    """
    if method == "auto":
        # 自动选择：如果有指定page_size，使用方法2；否则使用方法1
        method = "method2" if page_size else "method1"
    
    if method == "method1":
        return images_to_pdf_method1(image_paths, output_pdf_path, page_size)
    elif method == "method2":
        fit_to_page = page_size is not None
        return images_to_pdf_method2(image_paths, output_pdf_path, page_size, fit_to_page)
    else:
        raise ValueError(f"不支持的方法: {method}")


if __name__ == "__main__":
    # 使用示例
    import sys
    
    image_files = [
        "test1.png",
        "test2.jpg",
        "test3.webp"
    ]
    
    # 示例1：保持图片原始尺寸
    print("=== 示例1：保持图片原始尺寸 ===")
    # images_to_pdf(image_files, "output_original.pdf", method="method1")
    
    # 示例2：统一A4尺寸，图片适应页面
    print("=== 示例2：统一A4尺寸 ===")
    # images_to_pdf(
    #     image_files,
    #     "output_a4.pdf",
    #     page_size=(595, 842),  # A4
    #     method="method2"
    # )
    
    # 示例3：A4尺寸，保持比例适应，带边距
    print("=== 示例3：A4尺寸，保持比例适应，带边距 ===")
    # images_to_pdf_advanced(
    #     image_files,
    #     "output_fit.pdf",
    #     page_size_preset="A4",
    #     fit_mode="fit",
    #     margin=20
    # )
    
    # 示例4：拉伸填满页面（不保持比例）
    print("=== 示例4：拉伸填满页面 ===")
    # images_to_pdf_advanced(
    #     image_files,
    #     "output_stretch.pdf",
    #     page_size_preset="A4",
    #     fit_mode="stretch"
    # )
    
    # 示例5：保持原始尺寸，居中显示
    print("=== 示例5：保持原始尺寸，居中显示 ===")
    # images_to_pdf_advanced(
    #     image_files,
    #     "output_center.pdf",
    #     page_size_preset="A4",
    #     fit_mode="center"
    # )
    
    # 示例6：每张图片使用不同设置
    print("=== 示例6：每张图片使用不同设置 ===")
    # images_to_pdf_advanced(
    #     image_files,
    #     "output_custom.pdf",
    #     fit_mode="custom",
    #     custom_settings=[
    #         {"page_size": "A4", "fit_mode": "fit", "margin": 20},
    #         {"page_size": (800, 600), "fit_mode": "stretch", "margin": 0},
    #         {"page_size": "Letter", "fit_mode": "center", "margin": 0}
    #     ]
    # )
    
    # 示例7：自定义尺寸和位置
    print("=== 示例7：自定义尺寸和位置 ===")
    # images_to_pdf_advanced(
    #     image_files,
    #     "output_custom_rect.pdf",
    #     page_size_preset="A4",
    #     fit_mode="custom",
    #     custom_settings=[
    #         {"fit_mode": "custom", "custom_rect": (50, 50, 300, 400)},  # 指定位置和尺寸
    #         {"fit_mode": "custom", "custom_rect": (350, 50, 545, 792)},  # 另一张图片
    #         {"fit_mode": "fit", "margin": 20}  # 第三张使用适应模式
    #     ]
    # )
    
    print("示例代码已准备就绪，取消注释即可运行")

