# -*- coding: utf-8 -*-
"""
Token计算工具
使用 transformers 库精确计算 Qwen 模型的 token 数量
"""
import logging

# 全局缓存 tokenizer，避免重复加载
_tokenizer_cache = {}


def get_qwen_tokenizer(model_name="Qwen/Qwen-7B"):
    """
    获取 Qwen tokenizer（带缓存）
    
    Args:
        model_name: 模型名称，默认为 Qwen/Qwen-7B
        
    Returns:
        tokenizer: Qwen tokenizer 对象
    """
    global _tokenizer_cache
    
    if model_name not in _tokenizer_cache:
        try:
            # 先检查 transformers 库是否可用
            try:
                import transformers
                from transformers import AutoTokenizer
            except ImportError as import_error:
                logging.warning(f"⚠️ transformers 库不可用: {import_error}，将使用降级方案计算token")
                _tokenizer_cache[model_name] = None
                return None
            
            logging.info(f"正在加载 Qwen tokenizer: {model_name}")
            _tokenizer_cache[model_name] = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            logging.info(f"✅ Qwen tokenizer 加载成功: {model_name}")
        except Exception as e:
            logging.warning(f"⚠️ 加载 Qwen tokenizer 失败: {model_name}, 错误: {e}，将使用降级方案计算token")
            # 如果加载失败，返回 None，后续会使用降级方案
            _tokenizer_cache[model_name] = None
    
    return _tokenizer_cache[model_name]


def count_qwen_tokens(text: str, model_name: str = "Qwen/Qwen-7B") -> int:
    """
    计算 Qwen 模型的 token 数量（精确计算）
    
    Args:
        text: 要计算的文本
        model_name: 模型名称，默认为 Qwen/Qwen-7B
        
    Returns:
        token_count: token 数量
    """
    if not text or not text.strip():
        return 0
    
    try:
        # 尝试使用 transformers 库精确计算
        tokenizer = get_qwen_tokenizer(model_name)
        if tokenizer:
            token_ids = tokenizer.encode(text, add_special_tokens=False)
            return len(token_ids)
    except ImportError:
        # transformers 库不可用，直接使用降级方案
        pass
    except Exception as e:
        logging.debug(f"使用 transformers 计算 token 失败: {e}，使用降级方案")
    
    # 降级方案：使用简单估算（中文1字符=1token，英文1字符=0.5token）
    try:
        from app.translate import common
        count = 0
        for char in text:
            if common.is_chinese(char):
                count += 1
            elif char and char != " ":
                count += 0.5
        return int(count)
    except Exception as e:
        logging.warning(f"降级方案计算 token 失败: {e}")
        # 最后的降级：简单字符数估算
        return len(text) // 2


def count_tokens_from_api_response(completion, input_text: str = None, model_name: str = "qwen-mt-plus") -> dict:
    """
    从 API 响应中提取 token 使用信息，如果响应中没有则计算
    
    Args:
        completion: OpenAI API 响应对象
        input_text: 输入文本（如果响应中没有 token 信息，用于计算）
        model_name: 模型名称
        
    Returns:
        dict: 包含 input_tokens, output_tokens, total_tokens 的字典
    """
    result = {
        'input_tokens': 0,
        'output_tokens': 0,
        'total_tokens': 0
    }
    
    # 优先从 API 响应中获取 token 使用信息
    if hasattr(completion, 'usage') and completion.usage:
        usage = completion.usage
        result['input_tokens'] = getattr(usage, 'prompt_tokens', 0) or 0
        result['output_tokens'] = getattr(usage, 'completion_tokens', 0) or 0
        result['total_tokens'] = getattr(usage, 'total_tokens', 0) or 0
        
        # 如果 total_tokens 为 0，计算一下
        if result['total_tokens'] == 0:
            result['total_tokens'] = result['input_tokens'] + result['output_tokens']
        
        return result
    
    # 如果 API 响应中没有 token 信息，则手动计算
    if input_text:
        # 计算输入 token
        result['input_tokens'] = count_qwen_tokens(input_text, model_name)
        
        # 如果有输出文本，计算输出 token
        if hasattr(completion, 'choices') and completion.choices:
            output_text = completion.choices[0].message.content if hasattr(completion.choices[0].message, 'content') else ""
            if output_text:
                result['output_tokens'] = count_qwen_tokens(output_text, model_name)
        
        result['total_tokens'] = result['input_tokens'] + result['output_tokens']
    
    return result

