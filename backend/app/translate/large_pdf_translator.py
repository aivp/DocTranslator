#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大文件PDF翻译器
基于big_pdf_trans项目集成，支持多线程翻译，每5页分批处理，最后合并成完整PDF
"""

import fitz
from app.utils.pymupdf_queue import (
    safe_fitz_open, safe_fitz_close, safe_fitz_save, 
    safe_fitz_new_document, safe_fitz_insert_pdf,
    safe_fitz_get_text_blocks, safe_fitz_insert_text,
    safe_fitz_insert_textbox, safe_fitz_new_rect,
    PyMuPDFContext
)
import os
import json
import logging
import tempfile
import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from multiprocessing import Process, Queue, cpu_count
from multiprocessing import set_start_method
import ctypes

# 设置进程启动方法（仅在主进程中设置一次）
try:
    set_start_method('spawn', force=True)
except RuntimeError:
    pass  # 已经设置过了

logger = logging.getLogger(__name__)

def force_memory_release():
    """强制释放内存到操作系统"""
    try:
        import gc
        gc.collect()
        # 尝试调用glibc的malloc_trim释放未使用的内存
        try:
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
            logger.info("🧹 已调用malloc_trim释放内存")
        except Exception as e:
            logger.debug(f"malloc_trim不可用: {e}")
    except Exception as e:
        logger.warning(f"强制释放内存失败: {e}")

# 全局进程池管理器
_process_pool = None
_process_pool_lock = threading.Lock()

def get_process_pool():
    """获取全局进程池（单例模式）"""
    global _process_pool
    with _process_pool_lock:
        if _process_pool is None:
            # 限制进程池大小为CPU核心数，避免资源耗尽
            max_processes = min(cpu_count(), 4)  # 最多4个进程
            _process_pool = ThreadPoolExecutor(max_workers=max_processes)
            logger.info(f"创建进程池，最大进程数: {max_processes}")
        return _process_pool

def shutdown_process_pool():
    """关闭全局进程池"""
    global _process_pool
    with _process_pool_lock:
        if _process_pool is not None:
            try:
                _process_pool.shutdown(wait=True)
                logger.info("全局进程池已关闭")
            except Exception as e:
                logger.warning(f"关闭进程池失败: {e}")
            finally:
                _process_pool = None


def _merge_pdfs_in_process(batch_results, output_path, input_pdf_path, temp_dir):
    """
    在独立进程中合并PDF（避免阻塞主线程）
    
    Args:
        batch_results: 批次处理结果列表
        output_path: 最终输出路径
        input_pdf_path: 原始PDF路径
        temp_dir: 临时文件目录
    """
    try:
        logger.info("进程开始合并翻译后的PDF...")
        
        # 过滤成功的批次
        successful_batches = [r for r in batch_results if r["status"] == "success"]
        
        if not successful_batches:
            raise Exception("没有成功的批次可以合并")
        
        successful_batches.sort(key=lambda x: x["start_page"])
        
        # 创建合并文档
        merged_doc = safe_fitz_new_document()
        batch_docs = []
        
        # 流式合并，避免同时打开所有PDF
        for batch_result in successful_batches:
            translated_pdf_path = batch_result["translated_pdf_path"]
            if os.path.exists(translated_pdf_path):
                batch_doc = safe_fitz_open(translated_pdf_path)
                batch_docs.append(batch_doc)
                safe_fitz_insert_pdf(merged_doc, batch_doc, 0, batch_doc.page_count)
                logger.info(f"合并批次 {batch_result['batch_num']}: 页面 {batch_result['start_page']}-{batch_result['end_page']-1}")
                
                # 每合并几个批次后强制垃圾回收
                if len(batch_docs) % 5 == 0:
                    import gc
                    gc.collect()
                    logger.debug(f"已合并 {len(batch_docs)} 个批次，执行垃圾回收")
        
        # 保存合并后的PDF
        merged_doc.save(output_path)
        
        # 删除原始文件
        if os.path.exists(input_pdf_path) and input_pdf_path != output_path:
            try:
                os.remove(input_pdf_path)
                logger.info(f"已删除原始文件: {input_pdf_path}")
            except Exception as e:
                logger.warning(f"删除原始文件失败: {e}")
        
        # 清理临时文件
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"已清理临时目录: {temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")
        
        logger.info(f"进程完成PDF合并: {output_path}")
        
    except Exception as e:
        logger.error(f"进程PDF合并失败: {e}")
    finally:
        # 确保所有文档对象被正确关闭
        if 'merged_doc' in locals() and merged_doc is not None:
            try:
                merged_doc.close()
            except Exception as e:
                logger.warning(f"关闭合并PDF文档时出错: {e}")
        
        for batch_doc in batch_docs:
            try:
                safe_fitz_close(batch_doc)
            except Exception as e:
                logger.warning(f"关闭批次PDF文档时出错: {e}")


def _compress_pdf_in_process(input_pdf_path, output_pdf_path):
    """
    在独立进程中压缩PDF（避免阻塞主线程）
    
    Args:
        input_pdf_path: 输入PDF路径
        output_pdf_path: 输出PDF路径
    """
    doc = None
    try:
        original_size = os.path.getsize(input_pdf_path)
        
        doc = fitz.open(input_pdf_path)
        doc.save(
            output_pdf_path,
            garbage=4,
            deflate=True,
            clean=True,
            encryption=fitz.PDF_ENCRYPT_NONE
        )
        
        compressed_size = os.path.getsize(output_pdf_path)
        compression_ratio = (1 - compressed_size / original_size) * 100
        
        logger.info(f"进程完成PDF压缩: {original_size:,} → {compressed_size:,} 字节 (压缩率: {compression_ratio:.1f}%)")
        return True
        
    except Exception as e:
        logger.error(f"进程PDF压缩失败: {e}")
        return False
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception as e:
                logger.warning(f"关闭压缩PDF文档时出错: {e}")


class LargePDFTranslator:
    def __init__(self, input_pdf_path, batch_size=5, max_workers=10, target_lang='zh', temp_dir=None, user_id=None):
        """
        初始化大文件PDF翻译器
        
        Args:
            input_pdf_path: 输入PDF文件路径
            batch_size: 每批处理的页数，默认5页
            max_workers: 最大线程数，默认10
            target_lang: 目标语言，默认中文
            temp_dir: 临时文件目录，默认为系统临时目录
            user_id: 用户ID，用于临时文件隔离
        """
        self.input_pdf_path = input_pdf_path
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.target_lang = target_lang
        self.user_id = user_id
        self.doc = None
        self.total_pages = 0
        self.processed_batches = []
        
        # 创建临时目录，按用户ID隔离
        if temp_dir is None:
            # 获取uploads基础目录（避免在用户的上传文件目录中创建临时文件）
            # 输入文件路径格式：/app/storage/uploads/tenant_1/user_2/2025-10-21/file.pdf
            # 临时文件应创建在：/app/storage/uploads/temp_user_2/translate_xxx/
            base_dir = os.path.dirname(input_pdf_path)  # /app/storage/uploads/tenant_1/user_2/2025-10-21
            date_dir = os.path.dirname(base_dir)  # /app/storage/uploads/tenant_1/user_2
            user_dir = os.path.dirname(date_dir)  # /app/storage/uploads/tenant_1
            uploads_base = os.path.dirname(user_dir)  # /app/storage/uploads
            
            if user_id:
                # 使用用户ID创建隔离目录
                temp_dir = os.path.join(uploads_base, f"temp_user_{user_id}", f"translate_{uuid.uuid4().hex[:8]}")
            else:
                # 如果没有用户ID，使用默认方式
                temp_dir = os.path.join(uploads_base, f"temp_translate_{uuid.uuid4().hex[:8]}")
        
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)
        logger.info(f"临时文件目录: {self.temp_dir}")
        logger.info(f"用户ID: {user_id if user_id else 'N/A'}")
        logger.info(f"批处理大小: {self.batch_size} 页/批")
        logger.info(f"最大线程数: {self.max_workers}")
        
        # 线程安全锁
        self.lock = threading.Lock()
    
    def __del__(self):
        """清理临时文件"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"已清理临时目录: {self.temp_dir}")
                
                # 如果用户隔离目录为空，也清理掉
                if self.user_id:
                    user_temp_dir = os.path.dirname(self.temp_dir)
                    if os.path.exists(user_temp_dir) and not os.listdir(user_temp_dir):
                        shutil.rmtree(user_temp_dir)
                        logger.info(f"已清理空的用户隔离目录: {user_temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")
    
    def get_total_pages(self):
        """获取PDF总页数"""
        try:
            doc = fitz.open(self.input_pdf_path)
            total_pages = doc.page_count
            doc.close()
            return total_pages
        except Exception as e:
            logger.error(f"获取PDF页数失败: {e}")
            raise
    
    def extract_texts_from_pages(self, start_page, end_page):
        """
        从指定页面范围提取文本
        
        Args:
            start_page: 起始页（从0开始）
            end_page: 结束页（不包含）
        
        Returns:
            list: 提取的文本数据
        """
        doc = None
        try:
            doc = fitz.open(self.input_pdf_path)
            extracted_texts = []
            
            for page_num in range(start_page, min(end_page, doc.page_count)):
                page = doc[page_num]
                logger.info(f"提取第 {page_num + 1} 页文本...")
                
                # 提取文本块
                text_blocks = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)["blocks"]
                page_texts = []
                
                for block in text_blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text = span["text"].strip()
                                if text:
                                    text_info = {
                                        "text": text,
                                        "bbox": span["bbox"],
                                        "size": span["size"],
                                        "color": span["color"],
                                        "font": span["font"]
                                    }
                                    page_texts.append(text_info)
                
                page_data = {
                    "page_number": page_num,
                    "texts": page_texts
                }
                extracted_texts.append(page_data)
                logger.info(f"第 {page_num + 1} 页提取了 {len(page_texts)} 个文本块")
            
            return extracted_texts
            
        except Exception as e:
            logger.error(f"提取文本失败: {e}")
            raise
        finally:
            # 确保文档对象被正确关闭
            if doc is not None:
                try:
                    doc.close()
                    logger.debug("PDF文档已关闭")
                except Exception as close_error:
                    logger.warning(f"关闭PDF文档时出错: {close_error}")
    
    def translate_texts_batch(self, extracted_texts, trans):
        """
        多线程翻译文本批次
        
        Args:
            extracted_texts: 提取的文本数据
            trans: 翻译任务信息
        
        Returns:
            list: 翻译后的文本数据
        """
        try:
            translated_texts = []
            
            # 收集所有需要翻译的文本，去重
            unique_texts = []
            text_to_index = {}
            
            for page_data in extracted_texts:
                page_num = page_data["page_number"]
                for text_info in page_data["texts"]:
                    original_text = text_info["text"]
                    if original_text and original_text.strip():
                        if original_text not in text_to_index:
                            text_to_index[original_text] = len(unique_texts)
                            unique_texts.append(original_text)
            
            logger.info(f"批次中共有 {len(unique_texts)} 个唯一文本需要翻译")
            
            # 多线程翻译唯一文本
            translated_results = {}
            if unique_texts:
                # 记录翻译开始时间
                start_time = time.time()
                
                # 使用配置的线程数
                actual_workers = min(self.max_workers, len(unique_texts))
                logger.info(f"使用 {actual_workers} 个线程进行翻译")
                
                # 使用与小PDF完全相同的并发方式，但避免进度冲突
                import threading
                from .to_translate import get
                
                # 标记为大PDF翻译，避免 to_translate.py 中的进度更新
                trans['is_large_pdf'] = True
                
                # 创建文本数组，格式与小PDF一致
                texts = []
                for text in unique_texts:
                    texts.append({'text': text, 'complete': False})
                
                # 线程启动控制变量，与小PDF保持一致
                event = threading.Event()
                run_index = 0
                active_count = threading.activeCount()
                max_threads = actual_workers
                
                logger.info(f"开始翻译 {len(texts)} 个文本片段，使用 {max_threads} 个线程")
                
                # 启动线程，与小PDF保持完全一致的方式
                while run_index < len(texts):
                    if threading.activeCount() < max_threads + active_count and not event.is_set():
                        thread = threading.Thread(
                            target=get,
                            args=(trans, event, texts, run_index)
                        )
                        thread.start()
                        logger.info(f"启动翻译线程 {run_index}")
                        run_index += 1
                    time.sleep(0.1)  # 与小PDF保持相同的延迟
                
                # 等待翻译完成，与小PDF保持一致
                while not all(t.get('complete') for t in texts) and not event.is_set():
                    time.sleep(0.1)
                
                # 收集翻译结果
                for i, text_item in enumerate(texts):
                    original_text = unique_texts[i]
                    translated_text = text_item['text']
                    translated_results[original_text] = translated_text
                    
                    # 添加详细的调试日志
                    if original_text != translated_text:
                        logger.info(f"翻译成功 ({i+1}/{len(texts)}): '{original_text[:20]}...' -> '{translated_text[:20]}...'")
                    else:
                        logger.warning(f"翻译结果与原文相同 ({i+1}/{len(texts)}): '{original_text[:20]}...'")
                
                # 注意：这里不调用 to_translate.py 的 process 函数，避免进度冲突
                # 大PDF翻译有自己的进度更新机制
                
                total_time = time.time() - start_time
                logger.info(f"批次翻译完成，共 {len(unique_texts)} 个文本，总用时: {total_time:.1f}s")
            
            # 重新组织翻译结果
            for page_data in extracted_texts:
                page_num = page_data["page_number"]
                translated_page_data = {"page_number": page_num, "texts": []}
                
                for text_info in page_data["texts"]:
                    original_text = text_info["text"]
                    if original_text and original_text.strip():
                        # 获取翻译结果
                        translated_text = translated_results.get(original_text, original_text)
                        
                        # 添加调试日志
                        if original_text != translated_text:
                            logger.debug(f"翻译映射: '{original_text[:30]}...' -> '{translated_text[:30]}...'")
                        else:
                            logger.warning(f"未找到翻译结果，使用原文: '{original_text[:30]}...'")
                        
                        # 创建翻译后的文本信息
                        translated_text_info = text_info.copy()
                        translated_text_info["text"] = translated_text
                        translated_text_info["original_text"] = original_text
                        translated_page_data["texts"].append(translated_text_info)
                    else:
                        translated_page_data["texts"].append(text_info)
                
                translated_texts.append(translated_page_data)
            
            return translated_texts
            
        except Exception as e:
            logger.error(f"翻译文本失败: {e}")
            raise
    
    def translate_single_text_with_delay(self, text, trans, delay):
        """
        带延迟的翻译单个文本
        
        Args:
            text: 要翻译的文本
            trans: 翻译任务信息
            delay: 延迟时间（秒）
        
        Returns:
            str: 翻译后的文本
        """
        thread_id = threading.current_thread().ident
        logger.debug(f"[线程{thread_id}] 延迟 {delay} 秒后开始翻译: '{text[:30]}...'")
        
        # 延迟启动
        if delay > 0:
            time.sleep(delay)
        
        # 这个方法已经不再使用，直接返回原文
        return text
    
    
    def create_no_text_pdf(self, start_page, end_page, output_path):
        """
        创建无文本PDF
        
        Args:
            start_page: 起始页（从0开始）
            end_page: 结束页（不包含）
            output_path: 输出文件路径
        """
        doc = None
        no_text_doc = None
        try:
            doc = fitz.open(self.input_pdf_path)
            no_text_doc = fitz.open()
            
            for page_num in range(start_page, min(end_page, doc.page_count)):
                page = doc[page_num]
                new_page = no_text_doc.new_page(width=page.rect.width, height=page.rect.height)
                
                # 复制页面内容（图片、背景等）- 保留原文本，不删除
                # 这样可以避免高内存消耗的redaction操作，降低崩溃风险
                new_page.show_pdf_page(page.rect, doc, page_num)
                
                # 注意：不再执行删除文本操作（redaction），因为：
                # 1. redaction操作会消耗大量内存
                # 2. 可能导致PyMuPDF底层崩溃
                # 3. 保留原文本不会影响翻译结果（翻译文本会覆盖在原文上方）
                logger.debug(f"第 {page_num + 1} 页已复制（保留原文本，不删除）")
            
            no_text_doc.save(output_path)
            logger.info(f"[no_text] 无文本PDF保存完成: {output_path}")
            
            # 验证文件是否正常
            if not os.path.exists(output_path):
                logger.error(f"[no_text] 文件保存后不存在: {output_path}")
                return False
            
            file_size = os.path.getsize(output_path)
            logger.info(f"[no_text] 保存后文件大小: {file_size} 字节")
            
            # 尝试验证PDF是否可以正常打开（但不保留引用，避免内存泄漏）
            test_doc = None
            try:
                test_doc = fitz.open(output_path)
                test_page_count = test_doc.page_count
                logger.info(f"[no_text] PDF验证成功，页数: {test_page_count}")
            except Exception as verify_error:
                logger.error(f"[no_text] PDF验证失败，文件可能损坏: {verify_error}")
                return False
            finally:
                # 立即关闭验证文档，释放内存
                if test_doc is not None:
                    try:
                        test_doc.close()
                    except:
                        pass
                # 验证后立即清理内存
                import gc
                gc.collect()
            
            return True
            
        except Exception as e:
            logger.error(f"创建无文本PDF失败: {e}")
            return False
        finally:
            # 确保所有文档对象被正确关闭
            if no_text_doc is not None:
                try:
                    no_text_doc.close()
                    logger.debug("无文本PDF文档已关闭")
                except Exception as close_error:
                    logger.warning(f"关闭无文本PDF文档时出错: {close_error}")
            
            if doc is not None:
                try:
                    doc.close()
                    logger.debug("原始PDF文档已关闭")
                except Exception as close_error:
                    logger.warning(f"关闭原始PDF文档时出错: {close_error}")
    
    def fill_translated_texts_to_pdf(self, translated_texts, no_text_pdf_path, output_path):
        """
        将翻译后的文本填充到PDF
        
        Args:
            translated_texts: 翻译后的文本数据
            no_text_pdf_path: 无文本PDF路径
            output_path: 输出PDF路径
        """
        doc = None
        try:
            # 添加详细日志，定位崩溃点
            logger.info(f"[fill] 准备打开无文本PDF: {no_text_pdf_path}")
            logger.info(f"[fill] 文件是否存在: {os.path.exists(no_text_pdf_path)}")
            if os.path.exists(no_text_pdf_path):
                file_size = os.path.getsize(no_text_pdf_path)
                logger.info(f"[fill] 文件大小: {file_size} 字节")
            
            doc = fitz.open(no_text_pdf_path)
            logger.info(f"[fill] PDF打开成功，页数: {doc.page_count}")
            
            # 创建页面索引映射：原始页面号 -> 批次内页面索引
            page_index_map = {}
            for i, page_data in enumerate(translated_texts):
                original_page_num = page_data["page_number"]
                page_index_map[original_page_num] = i
            
            # 批量处理文本插入，每处理一定数量后清理内存
            text_insert_count = 0
            for page_data in translated_texts:
                original_page_num = page_data["page_number"]
                batch_page_index = page_index_map[original_page_num]
                page = doc[batch_page_index]
                logger.info(f"填充第 {original_page_num + 1} 页翻译文本 (批次内索引: {batch_page_index})...")
                
                # 先收集这一页所有需要删除的文本区域和要插入的文本
                redact_rects = []
                text_insertions = []
                
                for text_info in page_data["texts"]:
                    # 使用翻译后的文本
                    text = text_info["text"]
                    if text and text.strip():
                        bbox = text_info["bbox"]
                        font_size = text_info["size"]
                        color = text_info["color"]
                        
                        # 标准化颜色
                        if isinstance(color, (int, float)):
                            if color == 0:
                                color = (0, 0, 0)  # 黑色
                            elif color == 16777215:
                                color = (1, 1, 1)  # 白色
                            else:
                                # 转换为RGB
                                r = ((color >> 16) & 0xFF) / 255.0
                                g = ((color >> 8) & 0xFF) / 255.0
                                b = (color & 0xFF) / 255.0
                                color = (r, g, b)
                        elif isinstance(color, (list, tuple)) and len(color) >= 3:
                            color = tuple(color[:3])
                        else:
                            color = (0, 0, 0)  # 默认黑色
                        
                        # 创建文本框矩形
                        textbox = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
                        
                        # 收集需要删除的区域（避免文本重叠）
                        redact_rects.append(textbox)
                        
                        # 准备HTML文本
                        html_text = f"""
                        <div style="
                            font-size: {font_size}px;
                            color: rgb({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)});
                            font-family: sans-serif;
                            line-height: 1.0;
                            margin: 0;
                            padding: 0;
                            background: none;
                            background-color: transparent;
                            background-image: none;
                            border: none;
                            outline: none;
                            box-shadow: none;
                        ">
                            {text}
                        </div>
                        """
                        
                        text_insertions.append({
                            'textbox': textbox,
                            'html_text': html_text,
                            'text': text
                        })
                
                # 先删除原始文本，避免重叠
                if redact_rects:
                    try:
                        # 为每个文本区域添加redaction标注
                        for rect in redact_rects:
                            try:
                                # 使用透明填充，避免白色遮挡
                                page.add_redact_annot(rect, fill=None)
                            except Exception as e:
                                logger.debug(f"添加redaction标注失败（可能已被删除）: {e}")
                                # 如果失败，尝试透明填充
                                try:
                                    page.add_redact_annot(rect, fill=(0, 0, 0, 0))
                                except Exception as e2:
                                    logger.debug(f"透明填充redaction也失败: {e2}")
                        
                        # 应用redaction，真正删除文本
                        page.apply_redactions()
                        logger.debug(f"第 {original_page_num + 1} 页已删除 {len(redact_rects)} 个原始文本区域")
                    except Exception as e:
                        logger.warning(f"删除原始文本失败，继续插入翻译文本: {e}")
                
                # 然后插入翻译后的文本
                for insertion in text_insertions:
                    try:
                        page.insert_htmlbox(insertion['textbox'], insertion['html_text'])
                        text_insert_count += 1
                        # 每插入50个文本清理一次内存，避免内存过载
                        if text_insert_count % 50 == 0:
                            import gc
                            gc.collect()
                            logger.debug(f"[fill] 已插入{text_insert_count}个文本，执行内存清理")
                        logger.info(f"文本插入成功: '{insertion['text'][:20]}...'")
                    except Exception as e:
                        logger.error(f"文本插入失败: {e}")
                
                # 每页处理完后清理临时数据，避免内存累积
                redact_rects.clear()
                text_insertions.clear()
                import gc
                gc.collect()
                logger.debug(f"[fill] 第 {original_page_num + 1} 页处理完成，已清理内存")
            
            # 保存前添加日志和内存检查
            logger.info(f"[fill] 准备保存PDF到: {output_path}")
            import gc
            gc.collect()  # 保存前清理内存
            
            doc.save(output_path)
            logger.info(f"[fill] PDF保存成功: {output_path}")
            logger.info(f"[fill] 保存后文件大小: {os.path.getsize(output_path) if os.path.exists(output_path) else 0} 字节")
            return True
            
        except Exception as e:
            logger.error(f"填充翻译文本失败: {e}")
            return False
        finally:
            # 确保文档对象被正确关闭
            if doc is not None:
                try:
                    doc.close()
                    logger.debug("填充PDF文档已关闭")
                except Exception as close_error:
                    logger.warning(f"关闭填充PDF文档时出错: {close_error}")
    
    def compress_pdf(self, input_pdf_path, output_pdf_path, cancel_event=None):
        """
        压缩PDF文件（使用独立进程执行，避免阻塞其他任务）
        
        Args:
            input_pdf_path: 输入PDF路径
            output_pdf_path: 输出PDF路径
            cancel_event: 取消事件
        
        Returns:
            bool: 压缩是否成功
        """
        try:
            logger.info("开始压缩PDF（使用独立进程）...")
            
            # 检查是否已被取消
            if cancel_event and cancel_event.is_set():
                logger.info("PDF压缩被取消")
                return False
            
            # 使用独立进程执行压缩操作，避免阻塞其他翻译任务
            # 虽然当前任务会等待压缩完成，但其他任务不会受影响
            process = Process(
                target=_compress_pdf_in_process,
                args=(input_pdf_path, output_pdf_path)
            )
            process.start()
            
            # 等待进程完成，但定期检查取消事件
            while process.is_alive():
                if cancel_event and cancel_event.is_set():
                    logger.info("PDF压缩被取消，终止进程")
                    process.terminate()
                    process.join(timeout=5)  # 等待5秒让进程优雅退出
                    if process.is_alive():
                        process.kill()  # 强制杀死进程
                    return False
                time.sleep(0.1)  # 短暂等待
            
            process.join()  # 确保进程完全结束
            
            if process.exitcode == 0:
                logger.info("PDF压缩完成")
                return True
            else:
                logger.error(f"PDF压缩进程失败，退出码: {process.exitcode}")
                return False
            
        except Exception as e:
            logger.error(f"PDF压缩失败: {e}")
            return False
    
    def process_batch_with_delay(self, batch_num, start_page, end_page, trans, delay):
        """
        带延迟的批次处理
        
        Args:
            batch_num: 批次号
            start_page: 起始页
            end_page: 结束页
            trans: 翻译任务信息
            delay: 延迟时间（秒）
        
        Returns:
            dict: 处理结果
        """
        thread_id = threading.current_thread().ident
        logger.info(f"[线程{thread_id}] 批次 {batch_num} 延迟 {delay} 秒后开始处理")
        
        # 延迟启动
        if delay > 0:
            time.sleep(delay)
        
        return self.process_batch(batch_num, start_page, end_page, trans)
    
    def process_batch(self, batch_num, start_page, end_page, trans):
        """
        处理单个批次
        
        Args:
            batch_num: 批次号
            start_page: 起始页
            end_page: 结束页
            trans: 翻译任务信息
        
        Returns:
            dict: 处理结果
        """
        try:
            thread_id = threading.current_thread().ident
            logger.info(f"[线程{thread_id}] 开始处理批次 {batch_num}: 页面 {start_page}-{end_page-1}")
            
            # 1. 提取文本
            extracted_texts = self.extract_texts_from_pages(start_page, end_page)
            
            # 2. 多线程翻译文本
            translated_texts = self.translate_texts_batch(extracted_texts, trans)
            
            # 3. 创建无文本PDF
            no_text_pdf_path = os.path.join(self.temp_dir, f"batch_{batch_num}_no_text.pdf")
            if not self.create_no_text_pdf(start_page, end_page, no_text_pdf_path):
                raise Exception("创建无文本PDF失败")
            
            # 4. 填充翻译文本
            translated_pdf_path = os.path.join(self.temp_dir, f"batch_{batch_num}_translated.pdf")
            if not self.fill_translated_texts_to_pdf(translated_texts, no_text_pdf_path, translated_pdf_path):
                raise Exception("填充翻译文本失败")
            
            # 5. 压缩单个批次PDF
            compressed_pdf_path = os.path.join(self.temp_dir, f"batch_{batch_num}_compressed.pdf")
            if not self.compress_pdf(translated_pdf_path, compressed_pdf_path, trans.get('cancel_event')):
                logger.warning(f"批次 {batch_num} 压缩失败，使用原文件")
                compressed_pdf_path = translated_pdf_path
            
            # 6. 删除中间文件，只保留压缩文件
            try:
                # 删除无文本PDF
                if os.path.exists(no_text_pdf_path):
                    os.remove(no_text_pdf_path)
                    logger.debug(f"已删除无文本PDF: {no_text_pdf_path}")
                
                # 删除翻译PDF
                if os.path.exists(translated_pdf_path) and compressed_pdf_path != translated_pdf_path:
                    os.remove(translated_pdf_path)
                    logger.debug(f"已删除翻译PDF: {translated_pdf_path}")
                
                logger.info(f"批次 {batch_num} 中间文件已清理，保留压缩文件")
            except Exception as e:
                logger.warning(f"删除中间文件失败: {e}")
            
            result = {
                "batch_num": batch_num,
                "start_page": start_page,
                "end_page": end_page,
                "translated_pdf_path": compressed_pdf_path,
                "status": "success",
                "thread_id": thread_id
            }
            
            logger.info(f"[线程{thread_id}] 批次 {batch_num} 处理完成")
            return result
            
        except Exception as e:
            thread_id = threading.current_thread().ident
            logger.error(f"[线程{thread_id}] 批次 {batch_num} 处理失败: {e}")
            return {
                "batch_num": batch_num,
                "start_page": start_page,
                "end_page": end_page,
                "status": "failed",
                "error": str(e),
                "thread_id": thread_id
            }
    
    def merge_translated_pdfs(self, batch_results, output_path, cancel_event=None):
        """
        合并所有翻译后的PDF（使用独立进程执行，避免阻塞其他任务）
        
        Args:
            batch_results: 批次处理结果列表
            output_path: 最终输出路径
            cancel_event: 取消事件
        """
        try:
            logger.info("开始合并翻译后的PDF（使用独立进程）...")
            
            # 检查是否已被取消
            if cancel_event and cancel_event.is_set():
                logger.info("PDF合并被取消")
                return False
            
            # 过滤成功的批次
            successful_batches = [r for r in batch_results if r["status"] == "success"]
            
            if not successful_batches:
                raise Exception("没有成功的批次可以合并")
            
            # 使用独立进程执行合并操作，避免阻塞其他翻译任务
            # 虽然当前任务会等待合并完成，但其他任务不会受影响
            process = Process(
                target=_merge_pdfs_in_process,
                args=(successful_batches, output_path, self.input_pdf_path, self.temp_dir)
            )
            process.start()
            
            # 等待进程完成，但定期检查取消事件
            while process.is_alive():
                if cancel_event and cancel_event.is_set():
                    logger.info("PDF合并被取消，终止进程")
                    process.terminate()
                    process.join(timeout=5)  # 等待5秒让进程优雅退出
                    if process.is_alive():
                        process.kill()  # 强制杀死进程
                    return False
                time.sleep(0.1)  # 短暂等待
            
            process.join()  # 确保进程完全结束
            
            if process.exitcode == 0:
                logger.info(f"PDF合并完成: {output_path}")
                return output_path
            else:
                logger.error(f"PDF合并进程失败，退出码: {process.exitcode}")
                return False
            
        except Exception as e:
            logger.error(f"PDF合并失败: {e}")
            return False
    
    def _cleanup_temp_files(self, temp_files=None, temp_dir=None):
        """清理临时文件和目录，与小PDF保持一致"""
        logger.info("🧹 开始清理临时文件...")
        cleaned_count = 0
        
        # 清理临时文件
        if temp_files:
            for temp_file in temp_files:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                        logger.info(f"✅ 已删除临时文件: {os.path.basename(temp_file)}")
                        cleaned_count += 1
                    except Exception as e:
                        logger.warning(f"删除临时文件失败: {temp_file} - {e}")
        
        # 清理临时目录
        cleanup_dir = temp_dir or (hasattr(self, 'temp_dir') and self.temp_dir)
        if cleanup_dir and os.path.exists(cleanup_dir):
            try:
                import shutil
                shutil.rmtree(cleanup_dir)
                logger.info(f"✅ 已删除临时目录: {os.path.basename(cleanup_dir)}")
                cleaned_count += 1
                
                # 如果用户临时目录为空，也删除
                if hasattr(self, 'user_id') and self.user_id:
                    user_temp_dir = os.path.dirname(cleanup_dir)
                    if os.path.exists(user_temp_dir) and not os.listdir(user_temp_dir):
                        shutil.rmtree(user_temp_dir)
                        logger.info(f"✅ 已清理空用户临时目录: {os.path.basename(user_temp_dir)}")
                        cleaned_count += 1
                        
            except Exception as e:
                logger.warning(f"删除临时目录失败: {cleanup_dir} - {e}")
        
        logger.info(f"🧹 临时文件清理完成，共清理 {cleaned_count} 个文件/目录")
    
    def update_progress(self, trans, progress_percentage):
        """更新翻译进度"""
        try:
            from .to_translate import db
            db.execute("update translate set process=%s where id=%s", 
                     str(format(progress_percentage, '.1f')), 
                     trans['id'])
            logger.info(f"进度更新: {progress_percentage:.1f}%")
        except Exception as e:
            logger.error(f"更新进度失败: {str(e)}")
    
    def run_complete_translation(self, trans, output_file):
        """
        运行完整的多线程翻译流程
        
        Args:
            trans: 翻译任务信息
            output_file: 输出文件路径
        
        Returns:
            str: 最终输出文件路径
        """
        try:
            print("🚀 开始大文件多线程PDF翻译")
            print("=" * 60)
            
            # 获取取消事件
            cancel_event = trans.get('cancel_event')
            
            # 检查是否已被取消
            if cancel_event and cancel_event.is_set():
                print("翻译任务已被取消")
                return False
            
            # 获取总页数
            self.total_pages = self.get_total_pages()
            print(f"PDF总页数: {self.total_pages}")
            print(f"批处理大小: {self.batch_size} 页/批")
            print(f"最大线程数: {self.max_workers}")
            
            # 计算批次数
            total_batches = (self.total_pages + self.batch_size - 1) // self.batch_size
            print(f"总批次数: {total_batches}")
            
            # 计算每个批次应该占的百分比（合并前占90%）
            batch_progress_percentage = 90.0 / total_batches
            print(f"每个批次进度: {batch_progress_percentage:.1f}%")
            print("=" * 60)
            
            # 顺序处理每个批次，避免批次间并发
            batch_results = []
            start_time = time.time()
            successful_pages = 0
            
            # 逐个处理批次，确保一个批次完全处理完后再处理下一个
            for batch_num in range(total_batches):
                # 检查是否已被取消
                if cancel_event and cancel_event.is_set():
                    print("翻译任务已被取消，停止处理")
                    return False
                
                start_page = batch_num * self.batch_size
                end_page = min(start_page + self.batch_size, self.total_pages)
                
                print(f"\n🔄 开始处理批次 {batch_num + 1}/{total_batches} (第{start_page + 1}-{end_page}页)")
                print("=" * 60)
                
                try:
                    # 处理当前批次
                    batch_result = self.process_single_batch(
                        batch_num, 
                        start_page, 
                        end_page,
                        trans
                    )
                    
                    if batch_result:
                        batch_results.append(batch_result)
                        successful_pages += (end_page - start_page)
                        print(f"✅ 批次 {batch_num + 1} 处理完成")
                        
                        # 显示进度并更新数据库（合并前最多90%）
                        # 使用预先计算的每个批次百分比
                        completed_batches = len(batch_results)
                        batch_progress = min(completed_batches * batch_progress_percentage, 90.0)
                        elapsed_time = time.time() - start_time
                        
                        print(f"📊 进度计算: {completed_batches} × {batch_progress_percentage:.1f}% = {batch_progress:.1f}% - 已用时: {elapsed_time:.1f}s")
                        
                        # 更新数据库进度
                        self.update_progress(trans, batch_progress)
                    else:
                        print(f"❌ 批次 {batch_num + 1} 处理失败")
                        
                except Exception as e:
                    print(f"❌ 批次 {batch_num + 1} 处理出错: {str(e)}")
                    logger.error(f"批次 {batch_num + 1} 处理出错: {str(e)}")
                    continue
            
            # 合并所有翻译后的PDF
            print(f"\n🔄 合并所有翻译后的PDF...")
            # 合并开始，进度应该是90%（所有批次完成）
            print(f"📊 进度: 合并中 (90.0%)")
            
            # 在合并过程中更新进度为95%，让用户知道系统还在工作
            self.update_progress(trans, 95.0)
            print(f"📊 进度: 合并中 (95.0%)")
            
            final_output_file = self.merge_translated_pdfs(batch_results, output_file, cancel_event)
            
            # 内存优化：合并后立即清理batch_results
            try:
                successful_batches_count = len(batch_results)
                batch_results.clear()
                del batch_results
                import gc
                gc.collect()
                logger.info("🧹 合并后立即清理batch_results")
            except Exception as cleanup_error:
                logger.warning(f"清理batch_results时出错: {cleanup_error}")
                successful_batches_count = 0
            
            if final_output_file:
                # 合并完成，更新为100%
                self.update_progress(trans, 100.0)
                total_time = time.time() - start_time
                print(f"✅ 大文件多线程翻译完成! 输出文件: {final_output_file}")
                print(f"📊 进度: 完成 (100.0%)")
                print(f"⏱️ 总处理时间: {total_time:.2f} 秒")
                
                # 统计结果
                successful_batches = successful_batches_count
                failed_batches = total_batches - successful_batches
                
                print("\n" + "=" * 60)
                print("📊 处理结果统计:")
                print(f"   总批次数: {total_batches}")
                print(f"   成功批次: {successful_batches}")
                print(f"   失败批次: {failed_batches}")
                print(f"   成功率: {successful_batches/total_batches*100:.1f}%")
                print(f"   总处理时间: {total_time:.2f} 秒")
                print(f"   平均每批时间: {total_time/total_batches:.2f} 秒")
                print(f"   使用线程数: {self.max_workers}")
                print("=" * 60)
                
                return final_output_file
            else:
                raise Exception("PDF合并失败")
                
        except Exception as e:
            logger.error(f"大文件多线程翻译失败: {e}")
            raise
        finally:
            # 清理资源
            if self.doc:
                self.doc.close()
            
            # 内存优化：翻译完成后彻底清理所有数据结构
            try:
                # 清理已处理批次列表
                if hasattr(self, 'processed_batches'):
                    self.processed_batches.clear()
                    del self.processed_batches
                
                # 强制垃圾回收
                import gc
                gc.collect()
                
                # 强制释放内存到操作系统
                force_memory_release()
                
                logger.info("🧹 翻译完成后内存已彻底清理")
            except Exception as cleanup_error:
                logger.warning(f"清理翻译完成后的内存时出错: {cleanup_error}")
    
    def process_single_batch(self, batch_num, start_page, end_page, trans):
        """
        处理单个批次：提取文本 -> 翻译 -> 生成PDF -> 压缩 -> 删除临时文件
        
        Args:
            batch_num: 批次号
            start_page: 起始页
            end_page: 结束页
            trans: 翻译任务信息
            
        Returns:
            dict: 批次处理结果
        """
        try:
            print(f"📄 提取第{start_page+1}-{end_page}页文本...")
            
            # 1. 提取文本
            extracted_texts = self.extract_texts_from_pages(start_page, end_page)
            if not extracted_texts:
                print(f"⚠️ 第{start_page+1}-{end_page}页没有提取到文本")
                return None
            
            # 2. 翻译文本
            print(f"🔄 开始翻译第{start_page+1}-{end_page}页...")
            translated_texts = self.translate_texts_batch(extracted_texts, trans)
            
            # 3. 生成翻译后的PDF
            batch_output_path = os.path.join(self.temp_dir, f"batch_{batch_num}_translated.pdf")
            print(f"📝 生成翻译后的PDF: {batch_output_path}")
            
            # 先创建无文本PDF
            no_text_pdf_path = os.path.join(self.temp_dir, f"batch_{batch_num}_no_text.pdf")
            logger.info(f"[batch_{batch_num}] 开始创建附加文本PDF...")
            if not self.create_no_text_pdf(start_page, end_page, no_text_pdf_path):
                raise Exception("创建无文本PDF失败")
            
            # 创建完成后立即清理内存，避免后续步骤内存不足
            logger.info(f"[batch_{batch_num}] 无文本PDF创建完成，清理内存...")
            import gc
            gc.collect()
            logger.info(f"[batch_{batch_num}] 内存清理完成，开始填充翻译文本...")
            
            # 填充翻译文本
            if not self.fill_translated_texts_to_pdf(translated_texts, no_text_pdf_path, batch_output_path):
                raise Exception("填充翻译文本失败")
            
            logger.info(f"[batch_{batch_num}] 翻译文本填充完成")
            
            # 4. 压缩PDF
            compressed_path = batch_output_path.replace('.pdf', '_compressed.pdf')
            print(f"🗜️ 压缩PDF: {compressed_path}")
            
            self.compress_pdf(batch_output_path, compressed_path, trans.get('cancel_event'))
            
            # 5. 删除未压缩的临时文件，只保留压缩文件
            if os.path.exists(batch_output_path):
                os.remove(batch_output_path)
                print(f"🗑️ 已删除未压缩的临时文件: {batch_output_path}")
            
            # 删除无文本PDF文件
            if os.path.exists(no_text_pdf_path):
                os.remove(no_text_pdf_path)
                print(f"🗑️ 已删除无文本PDF文件: {no_text_pdf_path}")
            
            # 内存优化：立即清理批次处理中的临时数据
            try:
                # 清理文本数据
                extracted_texts.clear()
                del extracted_texts
                translated_texts.clear()
                del translated_texts
                
                # 强制垃圾回收
                import gc
                gc.collect()
                
                print(f"🧹 批次 {batch_num + 1} 内存已清理")
            except Exception as cleanup_error:
                print(f"⚠️ 清理批次内存时出错: {cleanup_error}")
            
            print(f"✅ 批次处理完成，保留压缩文件: {compressed_path}")
            
            print(f"✅ 批次 {batch_num + 1} 处理完成: {compressed_path}")
            
            return {
                "batch_num": batch_num,
                "start_page": start_page,
                "end_page": end_page,
                "translated_pdf_path": compressed_path,  # 使用与big_pdf_trans一致的字段名
                "status": "success"
            }
            
        except Exception as e:
            print(f"❌ 批次 {batch_num + 1} 处理失败: {str(e)}")
            logger.error(f"批次 {batch_num + 1} 处理失败: {str(e)}")
            return {
                "batch_num": batch_num,
                "start_page": start_page,
                "end_page": end_page,
                "status": "failed",
                "error": str(e)
            }
            # 清理临时文件
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                    logger.info(f"已清理临时目录: {self.temp_dir}")
                except Exception as e:
                    logger.warning(f"清理临时目录失败: {e}")
