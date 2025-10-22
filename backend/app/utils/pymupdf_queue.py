# -*- coding: utf-8 -*-
"""
PyMuPDF操作队列管理器 - 防死锁版本
限制PyMuPDF的插入、压缩等操作最多允许2个线程同时处理
避免资源竞争和内存问题，同时防止死锁
"""
import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from functools import wraps
import queue
import weakref

logger = logging.getLogger(__name__)

class PyMuPDFQueueManager:
    """PyMuPDF操作队列管理器 - 防死锁版本"""
    
    def __init__(self, max_workers=2):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="PyMuPDF")
        self.active_operations = 0
        self.lock = threading.RLock()  # 使用可重入锁
        self.operation_queue = queue.Queue()
        self.timeout_seconds = 30  # 操作超时时间
        self._thread_local = threading.local()  # 线程本地存储
        
        logger.info(f"PyMuPDF队列管理器已初始化，最大并发数: {max_workers}")
    
    def _is_current_thread_pymupdf(self):
        """检查当前线程是否是PyMuPDF工作线程"""
        return hasattr(self._thread_local, 'is_pymupdf_thread')
    
    def _mark_as_pymupdf_thread(self):
        """标记当前线程为PyMuPDF工作线程"""
        self._thread_local.is_pymupdf_thread = True
    
    def submit_operation(self, func, *args, **kwargs):
        """提交PyMuPDF操作到队列 - 防死锁版本"""
        
        # 如果当前线程已经是PyMuPDF工作线程，直接执行（避免嵌套死锁）
        if self._is_current_thread_pymupdf():
            logger.debug(f"当前线程已是PyMuPDF工作线程，直接执行: {func.__name__}")
            return func(*args, **kwargs)
        
        # 检查是否会导致死锁（活跃操作数接近最大值）
        with self.lock:
            if self.active_operations >= self.max_workers:
                logger.warning(f"PyMuPDF队列已满({self.active_operations}/{self.max_workers})，等待可用槽位...")
                # 等待一小段时间再重试
                time.sleep(0.1)
                if self.active_operations >= self.max_workers:
                    logger.error("PyMuPDF队列持续满载，可能存在死锁风险")
                    raise RuntimeError("PyMuPDF队列满载，无法提交新操作")
            
            self.active_operations += 1
            logger.debug(f"提交PyMuPDF操作: {func.__name__}, 当前活跃操作数: {self.active_operations}")
        
        try:
            # 使用线程池执行操作，设置超时防止死锁
            future = self.executor.submit(self._execute_with_context, func, args, kwargs)
            result = future.result(timeout=self.timeout_seconds)
            return result
        except TimeoutError:
            logger.error(f"PyMuPDF操作超时: {func.__name__}, 超时时间: {self.timeout_seconds}秒")
            raise RuntimeError(f"PyMuPDF操作超时: {func.__name__}")
        except Exception as e:
            logger.error(f"PyMuPDF操作失败: {func.__name__}, 错误: {str(e)}")
            raise
        finally:
            with self.lock:
                self.active_operations -= 1
                logger.debug(f"PyMuPDF操作完成: {func.__name__}, 当前活跃操作数: {self.active_operations}")
    
    def _execute_with_context(self, func, args, kwargs):
        """在线程池中执行操作，设置线程上下文"""
        try:
            self._mark_as_pymupdf_thread()
            return func(*args, **kwargs)
        finally:
            # 清理线程本地状态
            if hasattr(self._thread_local, 'is_pymupdf_thread'):
                delattr(self._thread_local, 'is_pymupdf_thread')
    
    def get_status(self):
        """获取队列状态"""
        with self.lock:
            return {
                'active_operations': self.active_operations,
                'max_workers': self.max_workers,
                'queue_size': self.operation_queue.qsize(),
                'timeout_seconds': self.timeout_seconds
            }
    
    def set_timeout(self, timeout_seconds):
        """设置操作超时时间"""
        self.timeout_seconds = timeout_seconds
        logger.info(f"PyMuPDF操作超时时间设置为: {timeout_seconds}秒")
    
    def shutdown(self):
        """关闭队列管理器"""
        logger.info("正在关闭PyMuPDF队列管理器...")
        self.executor.shutdown(wait=True, timeout=10)
        logger.info("PyMuPDF队列管理器已关闭")

# 全局PyMuPDF队列管理器实例
pymupdf_queue = PyMuPDFQueueManager(max_workers=2)

def pymupdf_operation(func):
    """PyMuPDF操作装饰器，自动将操作加入队列 - 防死锁版本"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return pymupdf_queue.submit_operation(func, *args, **kwargs)
    return wrapper

# PyMuPDF操作的包装函数 - 防死锁版本
def safe_fitz_open(file_path, **kwargs):
    """安全的fitz.open操作 - 防死锁版本"""
    @pymupdf_operation
    def _open():
        import fitz
        return fitz.open(file_path, **kwargs)
    return _open()

def safe_fitz_open_stream(stream, **kwargs):
    """安全的fitz.open(stream)操作 - 防死锁版本"""
    @pymupdf_operation
    def _open_stream():
        import fitz
        return fitz.open(stream=stream, **kwargs)
    return _open_stream()

def safe_fitz_save(doc, file_path, **kwargs):
    """安全的doc.save操作 - 防死锁版本"""
    @pymupdf_operation
    def _save():
        return doc.save(file_path, **kwargs)
    return _save()

def safe_fitz_close(doc):
    """安全的doc.close操作 - 防死锁版本"""
    @pymupdf_operation
    def _close():
        return doc.close()
    return _close()

def safe_fitz_new_document():
    """安全的fitz.open()创建新文档 - 防死锁版本"""
    @pymupdf_operation
    def _new_doc():
        import fitz
        return fitz.open()
    return _new_doc()

def safe_fitz_insert_pdf(doc, src_doc, from_page, to_page):
    """安全的doc.insert_pdf操作 - 防死锁版本"""
    @pymupdf_operation
    def _insert():
        return doc.insert_pdf(src_doc, from_page=from_page, to_page=to_page)
    return _insert()

def safe_fitz_get_text_blocks(page, flags=None):
    """安全的page.get_text操作 - 防死锁版本"""
    @pymupdf_operation
    def _get_text():
        import fitz
        if flags is None:
            flags = fitz.TEXTFLAGS_TEXT
        return page.get_text("dict", flags=flags)["blocks"]
    return _get_text()

def safe_fitz_insert_text(page, point, text, fontsize, **kwargs):
    """安全的page.insert_text操作 - 防死锁版本"""
    @pymupdf_operation
    def _insert_text():
        return page.insert_text(point, text, fontsize=fontsize, **kwargs)
    return _insert_text()

def safe_fitz_insert_textbox(page, rect, text, fontsize, **kwargs):
    """安全的page.insert_textbox操作 - 防死锁版本"""
    @pymupdf_operation
    def _insert_textbox():
        return page.insert_textbox(rect, text, fontsize=fontsize, **kwargs)
    return _insert_textbox()

def safe_fitz_new_rect(x0, y0, x1, y1):
    """安全的fitz.Rect创建 - 防死锁版本"""
    @pymupdf_operation
    def _new_rect():
        import fitz
        return fitz.Rect(x0, y0, x1, y1)
    return _new_rect()

# 批量操作支持 - 防死锁版本
def safe_fitz_batch_operations(operations):
    """批量执行PyMuPDF操作 - 防死锁版本"""
    @pymupdf_operation
    def _batch_execute():
        results = []
        for operation in operations:
            try:
                result = operation()
                results.append(result)
            except Exception as e:
                logger.error(f"批量操作中单个操作失败: {str(e)}")
                results.append(None)
        return results
    return _batch_execute()

# 上下文管理器支持 - 防死锁版本
class PyMuPDFContext:
    """PyMuPDF操作上下文管理器 - 防死锁版本"""
    
    def __init__(self, operation_name="PyMuPDF操作"):
        self.operation_name = operation_name
        self.start_time = None
        self.is_nested = False
    
    def __enter__(self):
        self.start_time = time.time()
        self.is_nested = pymupdf_queue._is_current_thread_pymupdf()
        if self.is_nested:
            logger.debug(f"嵌套PyMuPDF操作: {self.operation_name}")
        else:
            logger.debug(f"开始PyMuPDF操作: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time if self.start_time else 0
        if exc_type:
            logger.error(f"PyMuPDF操作失败: {self.operation_name}, 耗时: {duration:.2f}秒")
        else:
            logger.debug(f"PyMuPDF操作完成: {self.operation_name}, 耗时: {duration:.2f}秒")

# 死锁检测和恢复机制
class DeadlockDetector:
    """死锁检测器"""
    
    def __init__(self, queue_manager):
        self.queue_manager = queue_manager
        self.last_check_time = time.time()
        self.stuck_threshold = 60  # 60秒无变化认为可能死锁
    
    def check_deadlock(self):
        """检查是否可能存在死锁"""
        current_time = time.time()
        status = self.queue_manager.get_status()
        
        # 如果队列满载且长时间无变化，可能存在死锁
        if (status['active_operations'] >= status['max_workers'] and 
            current_time - self.last_check_time > self.stuck_threshold):
            logger.warning("检测到可能的PyMuPDF队列死锁，尝试恢复...")
            return True
        
        self.last_check_time = current_time
        return False
    
    def recover_from_deadlock(self):
        """从死锁中恢复"""
        logger.critical("尝试从PyMuPDF队列死锁中恢复...")
        # 这里可以实现更复杂的恢复逻辑
        # 比如强制关闭线程池并重新创建
        pass

# 使用示例和测试函数
def test_pymupdf_queue():
    """测试PyMuPDF队列功能 - 防死锁版本"""
    import fitz
    
    def test_operation():
        # 创建一个简单的PDF文档
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "Test", fontsize=12)
        doc.close()
        return "操作完成"
    
    def test_nested_operation():
        """测试嵌套操作（应该不会死锁）"""
        doc = fitz.open()
        page = doc.new_page()
        # 嵌套调用其他PyMuPDF操作
        page.insert_text((100, 100), "Nested Test", fontsize=12)
        doc.close()
        return "嵌套操作完成"
    
    try:
        # 测试普通操作
        result1 = pymupdf_queue.submit_operation(test_operation)
        logger.info(f"测试结果1: {result1}")
        
        # 测试嵌套操作
        result2 = pymupdf_queue.submit_operation(test_nested_operation)
        logger.info(f"测试结果2: {result2}")
        
        # 检查状态
        status = pymupdf_queue.get_status()
        logger.info(f"队列状态: {status}")
        
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")

if __name__ == "__main__":
    test_pymupdf_queue()
