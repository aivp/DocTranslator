#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试PDF压缩功能
"""

import os
import sys
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_pdf_compression_simple():
    """简单测试PDF压缩功能"""
    print("🧪 简单测试PDF压缩功能")
    print("=" * 60)
    
    try:
        # 直接导入PyMuPDF
        import fitz
        
        # 测试文件路径
        test_pdf = "/workspace/DocTranslator/pdf-translator-final/test.pdf"
        
        if os.path.exists(test_pdf):
            print("📄 测试文件: " + test_pdf)
            
            # 获取原始文件大小
            original_size = os.path.getsize(test_pdf)
            print("📊 原始文件大小: " + str(original_size) + " 字节 (" + str(original_size/1024/1024) + " MB)")
            
            # 设置输出文件名
            base_name = os.path.splitext(test_pdf)[0]
            output_pdf_path = base_name + "_optimized.pdf"
            
            # 打开PDF
            print("\n1. 打开PDF...")
            doc = fitz.open(test_pdf)
            print("   打开了 " + str(doc.page_count) + " 页的PDF")
            
            # 优化选项
            print("\n2. 应用优化选项...")
            print("   方法1: 使用压缩选项...")
            doc.save(
                output_pdf_path,
                garbage=4,        # 垃圾回收
                deflate=True,     # 压缩
                clean=True,       # 清理
                encryption=fitz.PDF_ENCRYPT_NONE  # 无加密
            )
            
            # 检查优化后的文件大小
            optimized_size = os.path.getsize(output_pdf_path)
            print("   优化后文件大小: " + str(optimized_size) + " 字节 (" + str(optimized_size/1024/1024) + " MB)")
            
            # 计算压缩率
            compression_ratio = (1 - optimized_size / original_size) * 100
            print("   压缩率: " + str(compression_ratio) + "%")
            
            doc.close()
            
            print("\n✅ 压缩成功!")
            print("📊 文件大小对比:")
            print("   原始: " + str(original_size) + " 字节 (" + str(original_size/1024/1024) + " MB)")
            print("   优化: " + str(optimized_size) + " 字节 (" + str(optimized_size/1024/1024) + " MB)")
            print("   节省: " + str(original_size - optimized_size) + " 字节 (" + str((1 - optimized_size/original_size)*100) + "%)")
            
            # 清理测试文件
            try:
                os.remove(output_pdf_path)
                print("🧹 已清理测试文件")
            except:
                pass
                
        else:
            print("❌ 测试文件不存在: " + test_pdf)
            
    except ImportError as e:
        print("❌ 导入失败: " + str(e))
        print("请确保已安装PyMuPDF: pip install PyMuPDF")
    except Exception as e:
        print("❌ 测试失败: " + str(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pdf_compression_simple()
