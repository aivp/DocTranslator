# -*- coding: utf-8 -*-
"""
流式翻译管理器 - 避免大量译文存储在内存中
翻译一个文本块就立即写入临时文件
"""
import os
import json
import tempfile
import shutil
import logging
from typing import List, Dict, Any, Iterator
from pathlib import Path

logger = logging.getLogger(__name__)

class StreamingTranslator:
    """流式翻译管理器"""
    
    def __init__(self, task_id: int, target_file: str, chunk_size: int = 10):
        """
        初始化流式翻译器
        
        Args:
            task_id: 任务ID
            target_file: 目标文件路径
            chunk_size: 每批翻译的文本块数量
        """
        self.task_id = task_id
        self.target_file = target_file
        self.chunk_size = chunk_size
        self.temp_dir = None
        self.temp_files = []
        self.processed_count = 0
        self.total_count = 0
        
    def __enter__(self):
        """上下文管理器入口"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix=f"streaming_translate_{self.task_id}_")
        logger.info(f"创建流式翻译临时目录: {self.temp_dir}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        # 清理临时目录
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"清理流式翻译临时目录: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")
    
    def translate_in_chunks(self, texts: List[Dict], translate_func) -> bool:
        """
        分块翻译文本
        
        Args:
            texts: 待翻译的文本列表
            translate_func: 翻译函数
            
        Returns:
            bool: 翻译是否成功
        """
        try:
            self.total_count = len(texts)
            logger.info(f"开始流式翻译，总文本数: {self.total_count}, 块大小: {self.chunk_size}")
            
            # 分块处理
            for i in range(0, len(texts), self.chunk_size):
                chunk = texts[i:i + self.chunk_size]
                chunk_index = i // self.chunk_size
                
                logger.info(f"处理第 {chunk_index + 1} 块，文本数: {len(chunk)}")
                
                # 翻译当前块
                success = self._translate_chunk(chunk, chunk_index, translate_func)
                if not success:
                    logger.error(f"第 {chunk_index + 1} 块翻译失败")
                    return False
                
                # 更新进度
                self.processed_count += len(chunk)
                self._update_progress()
                
                # 清理当前块的内存
                del chunk
                
            # 合并所有临时文件
            return self._merge_temp_files()
            
        except Exception as e:
            logger.error(f"流式翻译失败: {e}")
            return False
    
    def _translate_chunk(self, chunk: List[Dict], chunk_index: int, translate_func) -> bool:
        """
        翻译单个文本块
        
        Args:
            chunk: 文本块
            chunk_index: 块索引
            translate_func: 翻译函数
            
        Returns:
            bool: 翻译是否成功
        """
        try:
            # 调用翻译函数
            translated_chunk = translate_func(chunk)
            
            # 保存到临时文件
            temp_file = os.path.join(self.temp_dir, f"chunk_{chunk_index:04d}.json")
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(translated_chunk, f, ensure_ascii=False, indent=2)
            
            self.temp_files.append(temp_file)
            logger.info(f"第 {chunk_index + 1} 块翻译完成，保存到: {temp_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"翻译第 {chunk_index + 1} 块失败: {e}")
            return False
    
    def _update_progress(self):
        """更新翻译进度"""
        try:
            from app.extensions import db
            from app.models.translate import Translate
            
            progress = (self.processed_count / self.total_count) * 100
            progress = min(progress, 100.0)
            
            # 更新数据库进度
            task = db.session.query(Translate).get(self.task_id)
            if task:
                task.process = progress
                db.session.commit()
                logger.debug(f"更新进度: {progress:.1f}% ({self.processed_count}/{self.total_count})")
                
        except Exception as e:
            logger.warning(f"更新进度失败: {e}")
    
    def _merge_temp_files(self) -> bool:
        """
        合并所有临时文件到最终文件
        
        Returns:
            bool: 合并是否成功
        """
        try:
            logger.info(f"开始合并 {len(self.temp_files)} 个临时文件")
            
            # 根据文件类型选择合并策略
            file_ext = Path(self.target_file).suffix.lower()
            
            if file_ext in ['.txt', '.md']:
                return self._merge_text_files()
            elif file_ext == '.json':
                return self._merge_json_files()
            else:
                # 默认按文本文件处理
                return self._merge_text_files()
                
        except Exception as e:
            logger.error(f"合并临时文件失败: {e}")
            return False
    
    def _merge_text_files(self) -> bool:
        """合并文本文件"""
        try:
            with open(self.target_file, 'w', encoding='utf-8') as output_file:
                for temp_file in sorted(self.temp_files):
                    with open(temp_file, 'r', encoding='utf-8') as input_file:
                        content = input_file.read()
                        output_file.write(content)
                        if not content.endswith('\n'):
                            output_file.write('\n')
            
            logger.info(f"文本文件合并完成: {self.target_file}")
            return True
            
        except Exception as e:
            logger.error(f"合并文本文件失败: {e}")
            return False
    
    def _merge_json_files(self) -> bool:
        """合并JSON文件"""
        try:
            merged_data = []
            
            for temp_file in sorted(self.temp_files):
                with open(temp_file, 'r', encoding='utf-8') as f:
                    chunk_data = json.load(f)
                    if isinstance(chunk_data, list):
                        merged_data.extend(chunk_data)
                    else:
                        merged_data.append(chunk_data)
            
            with open(self.target_file, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"JSON文件合并完成: {self.target_file}")
            return True
            
        except Exception as e:
            logger.error(f"合并JSON文件失败: {e}")
            return False


class StreamingTextProcessor:
    """流式文本处理器 - 用于处理大文本文件"""
    
    def __init__(self, file_path: str, chunk_size: int = 1000):
        """
        初始化流式文本处理器
        
        Args:
            file_path: 文件路径
            chunk_size: 每块的行数
        """
        self.file_path = file_path
        self.chunk_size = chunk_size
        
    def process_in_chunks(self, process_func) -> bool:
        """
        分块处理文本文件
        
        Args:
            process_func: 处理函数，接收文本块，返回处理结果
            
        Returns:
            bool: 处理是否成功
        """
        try:
            temp_dir = tempfile.mkdtemp(prefix="streaming_text_")
            temp_files = []
            
            with open(self.file_path, 'r', encoding='utf-8') as file:
                chunk_lines = []
                chunk_index = 0
                
                for line in file:
                    chunk_lines.append(line)
                    
                    if len(chunk_lines) >= self.chunk_size:
                        # 处理当前块
                        result = process_func(chunk_lines)
                        
                        # 保存到临时文件
                        temp_file = os.path.join(temp_dir, f"chunk_{chunk_index:04d}.txt")
                        with open(temp_file, 'w', encoding='utf-8') as f:
                            f.writelines(result)
                        
                        temp_files.append(temp_file)
                        chunk_index += 1
                        chunk_lines = []
                
                # 处理最后一块
                if chunk_lines:
                    result = process_func(chunk_lines)
                    temp_file = os.path.join(temp_dir, f"chunk_{chunk_index:04d}.txt")
                    with open(temp_file, 'w', encoding='utf-8') as f:
                        f.writelines(result)
                    temp_files.append(temp_file)
            
            # 合并临时文件
            output_file = self.file_path + '.processed'
            with open(output_file, 'w', encoding='utf-8') as out_f:
                for temp_file in sorted(temp_files):
                    with open(temp_file, 'r', encoding='utf-8') as in_f:
                        out_f.write(in_f.read())
            
            # 清理临时目录
            shutil.rmtree(temp_dir)
            
            # 替换原文件
            shutil.move(output_file, self.file_path)
            
            logger.info(f"流式文本处理完成: {self.file_path}")
            return True
            
        except Exception as e:
            logger.error(f"流式文本处理失败: {e}")
            return False


def create_streaming_translator(task_id: int, target_file: str, chunk_size: int = 10) -> StreamingTranslator:
    """
    创建流式翻译器
    
    Args:
        task_id: 任务ID
        target_file: 目标文件路径
        chunk_size: 块大小
        
    Returns:
        StreamingTranslator: 流式翻译器实例
    """
    return StreamingTranslator(task_id, target_file, chunk_size)


def create_streaming_text_processor(file_path: str, chunk_size: int = 1000) -> StreamingTextProcessor:
    """
    创建流式文本处理器
    
    Args:
        file_path: 文件路径
        chunk_size: 块大小
        
    Returns:
        StreamingTextProcessor: 流式文本处理器实例
    """
    return StreamingTextProcessor(file_path, chunk_size)
