# -*- coding: utf-8 -*-
"""
PyMuPDF队列使用示例
展示如何使用PyMuPDF队列管理器来限制并发操作
"""

from app.utils.pymupdf_queue import (
    pymupdf_queue, safe_fitz_open, safe_fitz_close, 
    safe_fitz_save, PyMuPDFContext
)

def example_pdf_operations():
    """示例：使用PyMuPDF队列进行PDF操作"""
    
    # 示例1：简单的PDF操作
    def simple_pdf_operation():
        with PyMuPDFContext("简单PDF操作"):
            # 打开PDF
            doc = safe_fitz_open("example.pdf")
            
            # 获取页数
            page_count = doc.page_count
            print(f"PDF页数: {page_count}")
            
            # 关闭文档
            safe_fitz_close(doc)
            return page_count
    
    # 示例2：批量PDF操作
    def batch_pdf_operations():
        pdf_files = ["file1.pdf", "file2.pdf", "file3.pdf"]
        results = []
        
        for pdf_file in pdf_files:
            try:
                with PyMuPDFContext(f"处理{pdf_file}"):
                    doc = safe_fitz_open(pdf_file)
                    page_count = doc.page_count
                    safe_fitz_close(doc)
                    results.append(page_count)
            except Exception as e:
                print(f"处理{pdf_file}失败: {e}")
                results.append(0)
        
        return results
    
    # 示例3：检查队列状态
    def check_queue_status():
        status = pymupdf_queue.get_status()
        print(f"PyMuPDF队列状态: {status}")
        return status
    
    # 执行示例
    try:
        print("=== PyMuPDF队列使用示例 ===")
        
        # 检查队列状态
        check_queue_status()
        
        # 执行简单操作
        # page_count = simple_pdf_operation()  # 需要实际PDF文件
        # print(f"PDF页数: {page_count}")
        
        # 执行批量操作
        # results = batch_pdf_operations()  # 需要实际PDF文件
        # print(f"批量操作结果: {results}")
        
        print("示例完成")
        
    except Exception as e:
        print(f"示例执行失败: {e}")

if __name__ == "__main__":
    example_pdf_operations()

