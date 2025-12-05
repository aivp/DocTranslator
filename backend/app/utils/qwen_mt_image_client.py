# -*- coding: utf-8 -*-
"""
Qwen-MT-Image API 客户端
统一管理图片翻译API调用，参考阿里云百炼API文档优化
"""
import requests
import logging
from typing import Dict, Optional, Tuple
from flask import current_app

logger = logging.getLogger(__name__)


class QwenMTImageClient:
    """Qwen-MT-Image API 客户端"""
    
    # API配置常量
    API_BASE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis"
    MODEL_NAME = "qwen-mt-image"
    REQUEST_TIMEOUT = 30  # 秒
    MAX_RETRIES = 3  # 最大重试次数
    
    # 支持的响应字段路径（兼容不同的响应格式）
    TASK_ID_PATHS = [
        'task_id',
        'output.task_id',
        'data.task_id',
        'result.task_id'
    ]
    
    @classmethod
    def create_translation_task(
        cls,
        api_key: str,
        image_url: str,
        source_language: str,
        target_language: str,
        enable_async: bool = True
    ) -> Dict:
        """
        创建图片翻译任务
        
        Args:
            api_key: DashScope API Key
            image_url: 图片URL（必须是公网可访问的HTTP/HTTPS URL）
            source_language: 源语言代码（如：zh, en, ja等）
            target_language: 目标语言代码（如：zh, en, ja等）
            enable_async: 是否启用异步模式（默认True）
            
        Returns:
            dict: {
                'success': bool,
                'task_id': str (如果成功),
                'error': str (如果失败)
            }
        """
        # 参数验证
        validation_error = cls._validate_params(api_key, image_url, source_language, target_language)
        if validation_error:
            return {
                'success': False,
                'error': validation_error
            }
        
        # 构建请求参数
        payload = cls._build_payload(image_url, source_language, target_language)
        headers = cls._build_headers(api_key, enable_async)
        
        # 记录请求（简化日志）
        logger.info(
            f"创建Qwen-MT-Image翻译任务: {source_language}->{target_language}, "
            f"image_url={cls._mask_url(image_url)}"
        )
        
        # 发送请求（带重试机制）
        return cls._send_request(payload, headers)
    
    @classmethod
    def _validate_params(
        cls,
        api_key: str,
        image_url: str,
        source_language: str,
        target_language: str
    ) -> Optional[str]:
        """验证请求参数"""
        if not api_key or not api_key.strip():
            return 'API Key不能为空'
        
        if not image_url or not image_url.strip():
            return '图片URL不能为空'
        
        # 验证URL格式
        if not (image_url.startswith('http://') or image_url.startswith('https://')):
            return '图片URL必须是HTTP或HTTPS协议'
        
        if not source_language or not source_language.strip():
            return '源语言不能为空'
        
        if not target_language or not target_language.strip():
            return '目标语言不能为空'
        
        return None
    
    @classmethod
    def _build_payload(
        cls,
        image_url: str,
        source_language: str,
        target_language: str
    ) -> Dict:
        """构建请求Payload"""
        return {
            "model": cls.MODEL_NAME,
            "input": {
                "image_url": image_url,
                "source_lang": source_language,
                "target_lang": target_language
            }
        }
    
    @classmethod
    def _build_headers(cls, api_key: str, enable_async: bool) -> Dict:
        """构建请求Headers"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        if enable_async:
            headers["X-DashScope-Async"] = "enable"
        
        return headers
    
    @classmethod
    def _send_request(cls, payload: Dict, headers: Dict) -> Dict:
        """发送HTTP请求（带重试机制）"""
        last_error = None
        
        for attempt in range(1, cls.MAX_RETRIES + 1):
            try:
                response = requests.post(
                    cls.API_BASE_URL,
                    json=payload,
                    headers=headers,
                    timeout=cls.REQUEST_TIMEOUT
                )
                
                # 处理响应
                return cls._handle_response(response, attempt)
                
            except requests.exceptions.Timeout:
                last_error = '请求超时'
                if attempt < cls.MAX_RETRIES:
                    logger.warning(f"请求超时，第{attempt}次重试...")
                    continue
                else:
                    return {
                        'success': False,
                        'error': '请求超时，请稍后重试'
                    }
                    
            except requests.exceptions.RequestException as e:
                last_error = f'网络请求失败: {str(e)}'
                if attempt < cls.MAX_RETRIES:
                    logger.warning(f"网络请求失败，第{attempt}次重试: {str(e)}")
                    continue
                else:
                    logger.error(f"API请求异常（已重试{cls.MAX_RETRIES}次）: {str(e)}")
                    return {
                        'success': False,
                        'error': last_error
                    }
                    
            except Exception as e:
                logger.error(f"创建Qwen-MT-Image任务异常: {str(e)}", exc_info=True)
                return {
                    'success': False,
                    'error': f'创建任务失败: {str(e)}'
                }
        
        return {
            'success': False,
            'error': last_error or '请求失败'
        }
    
    @classmethod
    def _handle_response(cls, response: requests.Response, attempt: int) -> Dict:
        """处理API响应"""
        status_code = response.status_code
        
        # 成功响应
        if status_code == 200:
            try:
                result = response.json()
                logger.debug(f"Qwen-MT-Image API响应: {result}")
                
                # 提取task_id（支持多种响应格式）
                task_id = cls._extract_task_id(result)
                
                if task_id:
                    logger.info(f"✅ 翻译任务创建成功: task_id={task_id}")
                    return {
                        'success': True,
                        'task_id': task_id
                    }
                else:
                    logger.error(f"❌ 未找到task_id，响应: {result}")
                    return {
                        'success': False,
                        'error': 'API返回格式异常，未找到task_id'
                    }
                    
            except ValueError as e:
                logger.error(f"响应JSON解析失败: {str(e)}, 响应内容: {response.text[:200]}")
                return {
                    'success': False,
                    'error': 'API响应格式错误'
                }
        
        # 错误响应
        else:
            error_msg = cls._extract_error_message(response, status_code)
            logger.error(f"❌ Qwen-MT-Image API错误 (状态码: {status_code}): {error_msg}")
            return {
                'success': False,
                'error': error_msg
            }
    
    @classmethod
    def _extract_task_id(cls, result: Dict) -> Optional[str]:
        """从响应中提取task_id（支持多种响应格式）"""
        # 直接获取
        if 'task_id' in result:
            return result['task_id']
        
        # 从output中获取
        if 'output' in result and isinstance(result['output'], dict):
            if 'task_id' in result['output']:
                return result['output']['task_id']
        
        # 从data中获取
        if 'data' in result and isinstance(result['data'], dict):
            if 'task_id' in result['data']:
                return result['data']['task_id']
        
        # 从result中获取
        if 'result' in result and isinstance(result['result'], dict):
            if 'task_id' in result['result']:
                return result['result']['task_id']
        
        return None
    
    @classmethod
    def _extract_error_message(cls, response: requests.Response, status_code: int) -> str:
        """从错误响应中提取错误信息"""
        try:
            error_data = response.json()
            # 尝试多种可能的错误字段
            error_msg = (
                error_data.get('message') or
                error_data.get('error') or
                error_data.get('error_message') or
                error_data.get('msg') or
                str(error_data)
            )
            return error_msg or f"API请求失败: {status_code}"
        except:
            # 如果无法解析JSON，返回原始文本或状态码
            text = response.text
            if text:
                return f"API错误 ({status_code}): {text[:200]}"
            return f"API请求失败: {status_code}"
    
    @classmethod
    def _mask_url(cls, url: str) -> str:
        """掩码URL（隐藏敏感信息，用于日志）"""
        if not url or len(url) < 50:
            return url
        # 只显示前30个字符和后20个字符
        return f"{url[:30]}...{url[-20:]}"

