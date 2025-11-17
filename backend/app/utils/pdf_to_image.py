# -*- coding: utf-8 -*-
"""
PDF转PNG工具
使用PyMuPDF将PDF页面转换为PNG图片
"""
import fitz  # PyMuPDF
import os
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


def pdf_to_images(
    pdf_path: str,
    output_dir: Optional[str] = None,
    dpi: int = 200,
    page_range: Optional[tuple] = None,
    prefix: str = "page",
    image_format: str = "png"
) -> List[str]:
    """
    将PDF转换为图片（支持多种格式）
    
    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录，如果为None则使用PDF所在目录
        dpi: 图片分辨率，默认200（推荐值：150-300）
        page_range: 页面范围，格式为(start, end)，从1开始。如果为None则转换所有页面
        prefix: 输出文件名前缀，默认"page"
        image_format: 图片格式，支持 "png", "jpg", "jpeg", "webp"，默认"png"
    
    Returns:
        List[str]: 生成的图片文件路径列表
    
    Example:
        # 转换所有页面为PNG
        images = pdf_to_images("document.pdf", dpi=200, image_format="png")
        
        # 转换为JPG格式
        images = pdf_to_images("document.pdf", dpi=200, image_format="jpg")
        
        # 转换为WEBP格式
        images = pdf_to_images("document.pdf", dpi=200, image_format="webp")
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    # 确定输出目录
    if output_dir is None:
        output_dir = pdf_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    doc = None
    image_paths = []
    
    try:
        # 打开PDF
        doc = fitz.open(str(pdf_path))
        total_pages = doc.page_count
        
        # 确定要转换的页面范围
        if page_range:
            start_page, end_page = page_range
            start_page = max(1, start_page) - 1  # 转换为0索引
            end_page = min(end_page, total_pages)
        else:
            start_page = 0
            end_page = total_pages
        
        # 验证图片格式
        image_format = image_format.lower()
        supported_formats = ["png", "jpg", "jpeg", "webp"]
        if image_format not in supported_formats:
            raise ValueError(f"不支持的图片格式: {image_format}，支持的格式: {supported_formats}")
        
        # 统一jpg和jpeg
        if image_format == "jpeg":
            image_format = "jpg"
        
        logger.info(f"开始转换PDF: {pdf_path.name}, 页数: {end_page - start_page}/{total_pages}, DPI: {dpi}, 格式: {image_format.upper()}")
        
        # 计算缩放因子（DPI转换为缩放比例）
        # PyMuPDF使用72 DPI作为基准，所以缩放因子 = dpi / 72
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        
        # 逐页转换
        for page_num in range(start_page, end_page):
            page = doc[page_num]
            
            # 渲染页面为图片
            pix = page.get_pixmap(matrix=mat)
            
            # 生成输出文件名
            output_filename = f"{prefix}_{page_num + 1:04d}.{image_format}"
            output_path = output_dir / output_filename
            
            # 根据格式保存
            if image_format == "jpg":
                # JPG需要RGB模式
                if pix.alpha:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                pix.save(str(output_path), output="jpeg", jpg_quality=95)
            elif image_format == "webp":
                pix.save(str(output_path), output="webp")
            else:  # PNG
                pix.save(str(output_path))
            
            image_paths.append(str(output_path))
            logger.debug(f"已转换第 {page_num + 1} 页: {output_filename}")
        
        logger.info(f"PDF转换完成，共生成 {len(image_paths)} 张图片")
        return image_paths
        
    except Exception as e:
        logger.error(f"PDF转图片失败: {str(e)}")
        raise
    finally:
        if doc:
            doc.close()


# 保持向后兼容的别名
def pdf_to_png(
    pdf_path: str,
    output_dir: Optional[str] = None,
    dpi: int = 200,
    page_range: Optional[tuple] = None,
    prefix: str = "page"
) -> List[str]:
    """向后兼容的别名，默认转换为PNG"""
    return pdf_to_images(pdf_path, output_dir, dpi, page_range, prefix, "png")


def pdf_to_png_single_page(
    pdf_path: str,
    page_num: int,
    output_path: Optional[str] = None,
    dpi: int = 200
) -> str:
    """
    将PDF的指定页面转换为PNG图片
    
    Args:
        pdf_path: PDF文件路径
        page_num: 页码（从1开始）
        output_path: 输出文件路径，如果为None则自动生成
        dpi: 图片分辨率，默认200
    
    Returns:
        str: 生成的PNG文件路径
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    doc = None
    try:
        doc = fitz.open(str(pdf_path))
        
        if page_num < 1 or page_num > doc.page_count:
            raise ValueError(f"页码超出范围: {page_num} (总页数: {doc.page_count})")
        
        # 计算缩放因子
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        
        # 获取指定页面
        page = doc[page_num - 1]  # 转换为0索引
        
        # 渲染为图片
        pix = page.get_pixmap(matrix=mat)
        
        # 确定输出路径
        if output_path is None:
            output_path = pdf_path.parent / f"{pdf_path.stem}_page_{page_num:04d}.png"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存
        pix.save(str(output_path))
         
        logger.info(f"已转换PDF第 {page_num} 页: {output_path}")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"转换PDF页面失败: {str(e)}")
        raise
    finally:
        if doc:
            doc.close()


def pdf_to_png_bytes(
    pdf_path: str,
    page_num: int,
    dpi: int = 200
) -> bytes:
    """
    将PDF的指定页面转换为PNG字节数据（不保存文件）
    
    Args:
        pdf_path: PDF文件路径
        page_num: 页码（从1开始）
        dpi: 图片分辨率，默认200
    
    Returns:
        bytes: PNG图片的字节数据
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    doc = None
    try:
        doc = fitz.open(str(pdf_path))
        
        if page_num < 1 or page_num > doc.page_count:
            raise ValueError(f"页码超出范围: {page_num} (总页数: {doc.page_count})")
        
        # 计算缩放因子
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        
        # 获取指定页面并渲染
        page = doc[page_num - 1]
        pix = page.get_pixmap(matrix=mat)
        
        # 转换为PNG字节数据
        png_bytes = pix.tobytes("png")
        
        return png_bytes
        
    except Exception as e:
        logger.error(f"转换PDF页面为字节失败: {str(e)}")
        raise
    finally:
        if doc:
            doc.close()


if __name__ == "__main__":
    # 使用示例
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python pdf_to_image.py <pdf_file> [output_dir] [dpi]")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    
    try:
        images = pdf_to_png(pdf_file, output_dir=output_dir, dpi=dpi)
        print(f"成功转换 {len(images)} 张图片:")
        for img in images:
            print(f"  - {img}")
    except Exception as e:
        print(f"转换失败: {e}")
        sys.exit(1)

