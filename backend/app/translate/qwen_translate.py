# -*- coding: utf-8 -*-
"""
阿里云Qwen-MT翻译模型集成
"""
import logging
import os
import time
import re
from openai import OpenAI
from app.utils.api_key_helper import get_dashscope_key, get_current_tenant_id_from_request

# 兼容旧代码：保持全局变量
dashscope_key = os.environ.get('DASH_SCOPE_KEY', '')

# 在模块级别缓存 API Key（以 tenant_id 为 key）
_api_key_cache = {}

def is_pure_symbol(text: str) -> bool:
    """
    检查文本是否为纯符号（不包含有意义的文字内容）
    """
    if not text or not text.strip():
        return True
    
    # 去除空白字符
    cleaned_text = text.strip()
    
    # 如果文本长度很短且只包含符号，认为是纯符号
    if len(cleaned_text) <= 3:
        # 检查是否只包含常见符号
        symbol_pattern = r'^[^\w\u4e00-\u9fff]+$'  # 不包含字母、数字、中文字符
        if re.match(symbol_pattern, cleaned_text):
            return True
    
    # 检查是否只包含单个符号
    if len(cleaned_text) == 1 and not cleaned_text.isalnum() and not '\u4e00' <= cleaned_text <= '\u9fff':
        return True
    
    return False

# 请求频率控制 - 线程安全版本
import threading

# 已解锁到1000次/分钟
class QwenRateLimiter:
    def __init__(self):
        self.request_times = []  # 记录最近1000次请求的时间戳
        self.last_request_time = 0  # 上次请求时间
        self.lock = threading.Lock()
    
    def wait_for_rate_limit(self):
        """保证每分钟持续1000次请求"""
        with self.lock:
            current_time = time.time()
            
            # 清理超过60秒的记录
            self.request_times = [t for t in self.request_times if current_time - t < 60]
            
            # 计算理论上的最小间隔（60秒/1000次 = 0.06秒/次）
            min_interval = 0.06
            # min_interval = 0.1

            
            # 如果最近60秒内已经有1000次请求，需要等待
            if len(self.request_times) >= 1000:
                # 等待到最早请求过期
                wait_time = self.request_times[0] + 60 - current_time
                if wait_time > 0:
                    logging.warning(f"达到每分钟1000次限制，等待 {wait_time:.1f} 秒...")
                    time.sleep(wait_time)
                    # 重新清理过期记录
                    current_time = time.time()
                    self.request_times = [t for t in self.request_times if current_time - t < 60]
            
            # 动态调整间隔，确保持续1000次/分钟
            if len(self.request_times) > 0:
                # 计算当前窗口的剩余时间
                window_start = self.request_times[0]
                remaining_time = 60 - (current_time - window_start)
                remaining_requests = 1000 - len(self.request_times)
                
                if remaining_requests > 0 and remaining_time > 0:
                    # 计算理论间隔
                    theoretical_interval = remaining_time / remaining_requests
                    # 使用理论间隔和最小间隔的较大值
                    actual_interval = max(theoretical_interval, min_interval)
                    
                    # 确保请求间隔
                    if self.last_request_time > 0:
                        time_since_last = current_time - self.last_request_time
                        if time_since_last < actual_interval:
                            sleep_time = actual_interval - time_since_last
                            if sleep_time > 0.01:  # 只有当需要等待超过0.01秒时才等待
                                time.sleep(sleep_time)
                                current_time = time.time()
            else:
                # 第一个请求，不需要等待
                pass
            
            # 添加当前请求时间戳
            self.request_times.append(current_time)
            self.last_request_time = current_time
            
            # 计算当前速率
            if len(self.request_times) > 1:
                elapsed = current_time - self.request_times[0]
                if elapsed > 0:
                    current_rate = len(self.request_times) / (elapsed / 60)
                    logging.debug(f"Qwen请求计数: {len(self.request_times)}/1000, 当前速率: {current_rate:.1f}次/分钟")
                else:
                    logging.debug(f"Qwen请求计数: {len(self.request_times)}/1000")
            else:
                logging.debug(f"Qwen请求计数: {len(self.request_times)}/1000")
    
    def get_current_rate(self):
        """获取当前请求速率（次/分钟）"""
        current_time = time.time()
        # 清理过期记录
        self.request_times = [t for t in self.request_times if current_time - t < 60]
        if len(self.request_times) > 1:
            elapsed = current_time - self.request_times[0]
            if elapsed > 0:
                return len(self.request_times) / (elapsed / 60)
        return len(self.request_times)

# 创建全局的速率限制器实例
qwen_rate_limiter = QwenRateLimiter()

def wait_for_rate_limit():
    """等待请求间隔，确保不超过每分钟1000次限制"""
    qwen_rate_limiter.wait_for_rate_limit()

def get_current_request_rate():
    """获取当前请求速率"""
    return qwen_rate_limiter.get_current_rate()

def print_rate_stats():
    """打印当前速率统计"""
    current_rate = get_current_request_rate()
    print(f"当前Qwen API请求速率: {current_rate}次/分钟")

def handle_429_error(attempt, error_msg):
    """
    处理429频率限制错误
    返回是否应该继续重试
    """
    if attempt < 100:  # 429错误最多重试100次
        wait_time = (attempt + 1) * 2  # 递增等待时间：2秒、4秒、6秒、8秒、10秒、12秒、14秒、16秒、18秒、20秒
        logging.warning(f"遇到429频率限制 (尝试 {attempt + 1}/100)，等待 {wait_time} 秒后重试...")
        time.sleep(wait_time)
        return True  # 继续重试
    else:
        logging.warning("达到429错误最大重试次数 (100)，返回原文")
        return False  # 停止重试

def qwen_translate(text, target_language, source_lang="auto", tm_list=None, terms=None, domains=None, prompt=None, prompt_id=None, max_retries=10, texts=None, index=None, tenant_id=None, api_key=None, translate_id=None, customer_id=None, uuid=None):
    """
    使用阿里云Qwen-MT翻译模型进行翻译
    
    根据官方文档，支持两种翻译方式：
    1. 使用提示词方式：当提供prompt时，将文本插入提示词模板中发送
    2. 使用translation_options方式：当没有prompt时，使用原有的translation_options参数
    
    Args:
        text: 要翻译的文本
        target_language: 目标语言（当使用translation_options方式时）
        source_lang: 源语言，默认为"auto"（当使用translation_options方式时）
        tm_list: 术语库列表（当使用translation_options方式时）
        terms: 自定义术语（当使用translation_options方式时）
        domains: 领域提示（当使用translation_options方式时）
        prompt: 提示词模板（当使用提示词方式时）
        max_retries: 最大重试次数
    """
    
    # 翻译日志已关闭（调试时可打开）
    # logging.info("🚀 QWEN_TRANSLATE 函数被调用")
    # logging.info(f"📝 参数信息: texts={texts is not None}, index={index}, prompt_id={prompt_id}")
    
    # 输入验证
    if not text or not text.strip():
        logging.warning("输入文本为空，跳过翻译")
        return text
    
    if not target_language:
        logging.error("目标语言未指定")
        return text
    
    # 记录开始时间
    start_time = time.time()
    # 翻译日志已关闭（调试时可打开）
    # logging.info(f"🚀 开始Qwen翻译: {text[:100]}... -> {target_language}")
    
    # 初始化术语表token数量（用于统计）
    terms_tokens = 0
    
    for attempt in range(max_retries):
        try:
            # 使用传入的api_key（已在启动接口中从数据库获取并传入）
            if not api_key:
                # 如果没有传入，尝试从环境变量获取（兼容旧逻辑）
                api_key = os.environ.get('DASH_SCOPE_KEY', '')
            
            if not api_key:
                logging.error("❌ DASH_SCOPE_KEY未设置或为空")
                return "[错误: 未配置翻译模型，请联系管理员]"
                
            # 翻译日志已关闭（调试时可打开）
            # logging.info(f"🔄 Qwen翻译尝试 {attempt + 1}/{max_retries}")
            
            # 初始化 OpenAI 客户端
            client = OpenAI(
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                api_key=api_key,
                timeout=60.0  # 增加超时时间
            ) 
            
            # 添加调试日志，查看prompt_id参数的实际值
            # logging.info(f"🔍 调试信息 - prompt_id参数:")
            # logging.info(f"  prompt_id类型: {type(prompt_id)}")
            # logging.info(f"  prompt_id值: {repr(prompt_id)}")
            # logging.info(f"  prompt_id是否为空: {not prompt_id}")
            # logging.info(f"  prompt_id是否大于0: {prompt_id and int(prompt_id) > 0}")
            # logging.info(f"  判断结果 - 是否使用prompt方式: {bool(prompt_id and int(prompt_id) > 0)}")
            
            # 根据是否有prompt_id选择翻译方式
            # 检查prompt_id是否存在且大于0
            if prompt_id and int(prompt_id) > 0:
                # 方式一：使用提示词方式（根据官方文档）
                # 翻译日志已关闭（调试时可打开）
                # logging.info(f"🎯 使用提示词方式翻译")
                
                # 检查待翻译文本是否为纯符号，如果是则跳过
                if is_pure_symbol(text):
                    # 翻译日志已关闭（调试时可打开）
                    # logging.info(f"⚠️ 待翻译文本为纯符号，跳过翻译: {repr(text)}")
                    return text
                
                # 翻译日志已关闭（调试时可打开）
                # logging.info(f"🔍 上下文功能调试 - 开始处理")
                
                # 添加上下文信息（如果提供了texts和index）
                context_info = ""
                # 翻译日志已关闭（调试时可打开）
                # logging.info(f"🔍 上下文处理调试信息:")
                # logging.info(f"  texts参数: {texts is not None}")
                # logging.info(f"  index参数: {index}")
                # logging.info(f"  texts长度: {len(texts) if texts else 'None'}")
                
                if texts and index is not None:
                    context_before = ""
                    context_after = ""
                    
                    # 获取前文
                    if index > 0:
                        prev_text_item = texts[index-1]
                        # 翻译日志已关闭（调试时可打开）
                        # logging.info(f"🔍 前文调试: index-1={index-1}, 前文项类型={type(prev_text_item)}")
                        
                        # 处理字符串类型的前文项
                        if isinstance(prev_text_item, str) and prev_text_item.strip():
                            if not is_pure_symbol(prev_text_item):
                                context_before = prev_text_item.strip()[:200]  # 限制长度200字符
                                # 翻译日志已关闭（调试时可打开）
                                # logging.info(f"📖 获取前文上下文: {context_before[:50]}...")
                            # else:
                            #     logging.info(f"📝 前文为纯符号，跳过: {repr(prev_text_item.strip())}")
                        # 处理字典类型的前文项
                        elif isinstance(prev_text_item, dict) and 'text' in prev_text_item and prev_text_item['text']:
                            if not is_pure_symbol(prev_text_item['text']):
                                context_before = prev_text_item['text'][:200]  # 限制长度200字符
                                # 翻译日志已关闭（调试时可打开）
                                # logging.info(f"📖 获取前文上下文: {context_before[:50]}...")
                            # else:
                            #     logging.info(f"📝 前文为纯符号，跳过: {repr(prev_text_item['text'])}")
                        # else:
                        #     logging.info(f"📝 前文无有效内容")
                    # else:
                    #     logging.info(f"📝 当前是第一个文本，无前文")
                    
                    # 获取后文  
                    if index < len(texts)-1:
                        next_text_item = texts[index+1]
                        # 翻译日志已关闭（调试时可打开）
                        # logging.info(f"🔍 后文调试: index+1={index+1}, 后文项类型={type(next_text_item)}")
                        
                        # 处理字符串类型的后文项
                        if isinstance(next_text_item, str) and next_text_item.strip():
                            if not is_pure_symbol(next_text_item):
                                context_after = next_text_item.strip()[:200]  # 限制长度200字符
                                # 翻译日志已关闭（调试时可打开）
                                # logging.info(f"📖 获取后文上下文: {context_after[:50]}...")
                            # else:
                            #     logging.info(f"📝 后文为纯符号，跳过: {repr(next_text_item.strip())}")
                        # 处理字典类型的后文项
                        elif isinstance(next_text_item, dict) and 'text' in next_text_item and next_text_item['text']:
                            if not is_pure_symbol(next_text_item['text']):
                                context_after = next_text_item['text'][:200]  # 限制长度200字符
                                # 翻译日志已关闭（调试时可打开）
                                # logging.info(f"📖 获取后文上下文: {context_after[:50]}...")
                            # else:
                            #     logging.info(f"📝 后文为纯符号，跳过: {repr(next_text_item['text'])}")
                        # else:
                        #     logging.info(f"📝 后文无有效内容")
                    # else:
                    #     logging.info(f"📝 当前是最后一个文本，无后文")
                    
                    # 构建上下文信息并硬编码到prompt后面
                    if context_before or context_after:
                        if context_before and context_after:
                            # 既有上文又有下文
                            context_info = f"\n# 上下文参考\n1. **参考上文**：{context_before}\n2. **下文**：{context_after}"
                            # 翻译日志已关闭（调试时可打开）
                            # logging.info(f"🔗 添加上下文信息（前文+后文）到prompt后面，当前文本索引: {index}")
                        elif context_before:
                            # 只有上文
                            context_info = f"\n# 上下文参考\n1. **参考上文**：{context_before}"
                            # 翻译日志已关闭（调试时可打开）
                            # logging.info(f"🔗 添加上下文信息（仅前文）到prompt后面，当前文本索引: {index}")
                        elif context_after:
                            # 只有下文
                            context_info = f"\n# 上下文参考\n1. **请参考下文**：{context_after}"
                            # 翻译日志已关闭（调试时可打开）
                            # logging.info(f"🔗 添加上下文信息（仅后文）到prompt后面，当前文本索引: {index}")
                    # else:
                    #     logging.info(f"📝 无上下文信息，当前文本索引: {index}")
                # else:
                #     logging.info("📝 未提供texts或index，跳过上下文处理")
                
                # 将上下文信息插入到待翻译文本之前
                if context_info:
                    # 构建包含上下文的待翻译文本，每个部分都有独立的#标题
                    enhanced_text = context_info + "\n\n# 待翻译文本\n" + text
                    final_prompt = prompt.format(text_to_translate=enhanced_text)
                else:
                    # 没有上下文，直接使用原始文本
                    final_prompt = prompt.format(text_to_translate=text)
                
                # 翻译日志已关闭（调试时可打开）
                # if context_info:
                #     logging.info(f"🔗 最终提示词包含上下文:")
                #     logging.info(f"  上下文部分: {context_info[:100]}...")
                #     logging.info(f"  原始文本: {text[:100]}...")
                #     logging.info(f"  增强文本: {enhanced_text[:200]}...")
                #     logging.info(f"  完整内容: {final_prompt[:200]}...")
                # else:
                #     logging.info(f"📝 最终提示词不包含上下文: {final_prompt[:200]}...")
                
                # 构建messages
                messages = [{"role": "user", "content": final_prompt}]
                
                # 添加详细的请求参数日志
                # logging.info(f"🔧 Qwen翻译请求参数:")
                # logging.info(f"  model: qwen-mt-plus")
                # logging.info(f"  use_prompt: True")
                # logging.info(f"  prompt_template: {prompt[:100]}...")
                # logging.info(f"  text: {text[:100]}...")
                
                # 打印完整的请求内容
                # print("=" * 80)
                # print("🚀 QWEN-MT-PLUS 提示词翻译请求")
                # print("=" * 80)
                # print(f"📝 原始文本: {text}")
                # print(f"📋 提示词模板: {prompt}")
                
                # 明确显示上下文信息
                # if context_info:
                #     print(f"🔗 上下文信息:")
                #     print(f"   - 前文: {context_before[:100] if 'context_before' in locals() and context_before else '♂'}")
                #     print(f"   - 后文: {context_after[:100] if 'context_after' in locals() and context_after else '♂'}")
                #     print(f"   - 上下文信息: {context_info}")
                
                # print(f"🔗 最终请求内容: {final_prompt}")
                # print(f"📡 API请求参数:")
                # print(f"   - model: qwen-mt-plus")
                # print(f"   - messages: {messages}")
                # print("=" * 80)
                
                # 等待请求间隔
                wait_for_rate_limit()
                
                # 记录API调用开始时间
                api_start_time = time.time()
                
                # 调用API（不使用translation_options）
                # 翻译日志已关闭（调试时可打开）
                # logging.info(f"📡 发送API请求...")
                completion = client.chat.completions.create(
                    model="qwen-mt-plus",
                    messages=messages
                )
                
                # 计算API调用用时
                api_end_time = time.time()
                api_duration = api_end_time - api_start_time
            else:
                # 方式二：使用translation_options方式（原有方式）
                # 翻译日志已关闭（调试时可打开）
                # logging.info(f"🎯 使用translation_options方式翻译")
                
                # 设置翻译参数 - 根据官方文档格式
                translation_options = {
                    "source_lang": source_lang,
                    "target_lang": target_language
                }
                
                # 计算术语表的token数量（用于统计）
                terms_tokens = 0
                
                # 添加可选参数
                # 注意：只有当术语列表非空时才添加terms参数（官方API不接受空列表）
                if tm_list is not None and len(tm_list) > 0:
                    translation_options["terms"] = tm_list
                    logging.info(f"📚 使用术语库: {len(tm_list)} 个术语")
                    
                    # 计算术语表的token数量（将术语表序列化为JSON字符串后计算）
                    try:
                        import json
                        from app.utils.token_counter import count_qwen_tokens
                        terms_json = json.dumps(tm_list, ensure_ascii=False)
                        terms_tokens = count_qwen_tokens(terms_json, "qwen-mt-plus")
                        logging.debug(f"📊 术语表token数量: {terms_tokens}")
                    except Exception as e:
                        logging.warning(f"⚠️ 计算术语表token失败: {e}")
                        
                elif terms is not None and len(terms) > 0:
                    translation_options["terms"] = terms
                    logging.info(f"📚 使用自定义术语: {len(terms)} 个术语")
                    
                    # 计算术语表的token数量
                    try:
                        import json
                        from app.utils.token_counter import count_qwen_tokens
                        terms_json = json.dumps(terms, ensure_ascii=False)
                        terms_tokens = count_qwen_tokens(terms_json, "qwen-mt-plus")
                        logging.debug(f"📊 术语表token数量: {terms_tokens}")
                    except Exception as e:
                        logging.warning(f"⚠️ 计算术语表token失败: {e}")
                else:
                    # 如果没有术语或术语列表为空，不添加terms参数
                    if tm_list is not None or terms is not None:
                        logging.debug(f"术语列表为空，不添加terms参数 (tm_list长度: {len(tm_list) if tm_list else 0}, terms长度: {len(terms) if terms else 0})")
                
                # 硬编码domains参数 - 工程车辆和政府文件领域
                # translation_options["domains"] = "This text is from the engineering vehicle and construction machinery domain, as well as government and official document domain. It involves heavy machinery, construction equipment, industrial vehicles, administrative procedures, policy documents, and official notices. The content includes professional terminology related to vehicle design, mechanical engineering, hydraulic systems, electrical controls, safety standards, operational procedures, formal language, official terminology, administrative procedures, legal references, and institutional communication. Pay attention to technical accuracy, industry-specific terminology, professional engineering language, formal and authoritative tone, bureaucratic language patterns, official document structure, and administrative terminology. Maintain formal and precise technical descriptions suitable for engineering documentation and technical manuals, as well as the serious, formal, and official style appropriate for government communications and administrative documents."
                # 针对占位符特殊优化
                translation_options["domains"] = "The text originates from the domains of engineering vehicles, machinery, as well as government and official documents. It covers heavy machinery, construction equipment, industrial vehicles, administrative procedures, policy documents, and official notices, encompassing professional terminologies related to vehicle design, mechanical engineering, hydraulic systems, electrical control, safety standards, operating procedures, official wording, bureaucratic terminologies, administrative processes, legal citations, and institutional communication. Attention should be paid to technical accuracy, industry-specific jargon, professional engineering expressions, a formal and authoritative tone, bureaucratic sentence patterns, document structure, and administrative nomenclature. Do not translate the symbol '♂' during translation; retain it as is. The translation should conform to the formal and precise technical description style applicable to engineering documents and technical manuals, as well as the rigorous, formal, and official style suitable for government communication and administrative document fields."
                # logging.info(f"🎯 使用硬编码领域提示: 工程车辆和政府文件")
                    
                # # 添加详细的请求参数日志
                # logging.info(f"🔧 Qwen翻译请求参数:")
                # logging.info(f"  model: qwen-mt-plus")
                # logging.info(f"  use_prompt: False")
                # logging.info(f"  source_lang: {source_lang}")
                # logging.info(f"  target_lang: {target_language}")
                # logging.info(f"  translation_options: {translation_options}")
                # logging.info(f"  text: {text[:100]}...")
                
                # 等待请求间隔
                wait_for_rate_limit()
                
                # 记录API调用开始时间
                api_start_time = time.time()
                
                # 调用API
                # 翻译日志已关闭（调试时可打开）
                # logging.info(f"📡 发送API请求...")
                completion = client.chat.completions.create(
                    model="qwen-mt-plus",
                    messages=[{"role": "user", "content": text}],
                    extra_body={"translation_options": translation_options}
                )
                
                # 计算API调用用时
                api_end_time = time.time()
                api_duration = api_end_time - api_start_time
            
            # 提取翻译结果
            if not completion.choices or len(completion.choices) == 0:
                logging.warning(f"⚠️ API返回结果为空，跳过此文本: {text[:50]}...")
                return ""  # 直接返回空字符串，不重试
                
            translated_text = completion.choices[0].message.content
            if not translated_text or not translated_text.strip():
                logging.warning(f"⚠️ 翻译结果为空，跳过此文本: {text[:50]}...")
                return ""  # 直接返回空字符串，不重试
            
            # 打印响应结果
            # if prompt:  # 只有使用提示词时才打印
            #     print("=" * 80)
            #     print("✅ QWEN-MT-PLUS 提示词翻译响应")
            #     print("=" * 80)
            #     print(f"📝 原始文本: {text}")
            #     print(f"🎯 翻译结果: {translated_text}")
            #     print(f"⏱️ API调用用时: {api_duration:.3f}秒")
            #     print("=" * 80)
            
            # 检查翻译结果质量（暂时注释掉）
            # if _is_translation_result_abnormal(translated_text):
            #     logging.warning(f"⚠️  检测到异常翻译结果: {translated_text[:100]}...")
            #     raise Exception("翻译结果异常，可能包含重复字符或错误内容")
            
            # 计算API调用用时
            api_end_time = time.time()
            api_duration = api_end_time - api_start_time
            api_duration_ms = int(api_duration * 1000)  # 转换为毫秒
            total_duration = api_end_time - start_time
            
            # 记录token使用情况（如果提供了必要的参数）
            # customer_id 必须存在，不能为 None（用于溯源）
            if translate_id and customer_id is not None and tenant_id is not None:
                try:
                    from app.utils.token_recorder import record_token_usage
                    record_token_usage(
                        translate_id=translate_id,
                        customer_id=customer_id,
                        tenant_id=tenant_id,
                        uuid=uuid or "",
                        completion=completion,
                        input_text=text,
                        translated_text=translated_text,
                        model="qwen-mt-plus",
                        server="qwen",
                        api_duration_ms=api_duration_ms,
                        status="success",
                        retry_count=attempt,
                        terms_tokens=terms_tokens  # 传入术语表的token数量
                    )
                except Exception as e:
                    # token记录失败不应该影响翻译流程
                    logging.warning(f"⚠️ 记录token使用失败: {e}", exc_info=True)
            else:
                # 记录参数缺失的情况，便于调试
                logging.warning(f"⚠️ Token记录跳过: translate_id={translate_id}, customer_id={customer_id}, tenant_id={tenant_id}, uuid={uuid}")
            
            # 翻译成功日志已关闭（调试时可打开）
            # logging.info(f"✅ 翻译成功: {translated_text[:100]}...")
            # logging.info(f"⏱️ API调用用时: {api_duration:.3f}秒, 总用时: {total_duration:.3f}秒")
            return translated_text
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # 记录失败的token使用（如果提供了必要的参数）
            if translate_id and customer_id and tenant_id:
                try:
                    from app.utils.token_recorder import record_token_usage
                    api_duration_ms = int((time.time() - api_start_time) * 1000) if 'api_start_time' in locals() else None
                    record_token_usage(
                        translate_id=translate_id,
                        customer_id=customer_id,
                        tenant_id=tenant_id,
                        uuid=uuid or "",
                        completion=None,  # 失败时没有completion对象
                        input_text=text,
                        translated_text=None,
                        model="qwen-mt-plus",
                        server="qwen",
                        api_duration_ms=api_duration_ms,
                        status="failed",
                        error_message=f"{error_type}: {error_msg}",
                        retry_count=attempt,
                        terms_tokens=terms_tokens  # 传入术语表的token数量（即使失败也要统计）
                    )
                except Exception as record_error:
                    logging.warning(f"⚠️ 记录失败token使用失败: {record_error}")
            
            logging.error(f"❌ Qwen翻译API调用失败 (尝试 {attempt + 1}/{max_retries})")
            logging.error(f"   错误类型: {error_type}")
            logging.error(f"   错误信息: {error_msg}")
            logging.error(f"   输入文本: {text[:100]}...")
            
            # 检查是否是data_inspection_failed错误
            if "data_inspection_failed" in error_msg.lower() or "inappropriate content" in error_msg.lower():
                logging.warning(f"⚠️  检测到内容检查失败，跳过此内容: {text[:50]}...")
                return ""  # 直接返回空字符串，不进行重试
            
            # 检查是否是空结果相关的错误
            if "翻译结果为空" in error_msg or "API返回结果为空" in error_msg:
                logging.warning(f"⚠️ 检测到空结果错误，跳过此内容: {text[:50]}...")
                return ""  # 直接返回空字符串，不进行重试
            
            # 检查是否是频率限制错误
            if "429" in error_msg or "limit_requests" in error_msg or "rate limit" in error_msg.lower():
                logging.warning(f"⏰ 遇到频率限制错误 (429)")
                # 429错误使用专门的重试策略
                if handle_429_error(attempt, error_msg):
                    continue
                else:
                    logging.warning(f"🚫 达到429错误最大重试次数，返回原文")
                    return text
            else:
                # 非频率限制错误，使用原始重试策略
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 递增等待时间：2秒、4秒、6秒
                    logging.warning(f"⏳ 遇到非频率限制错误，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    logging.error(f"🚫 达到最大重试次数，返回原文")
                    return text
    
    # 如果所有重试都失败了
    logging.error(f"💥 所有重试都失败了，返回原文")
    return text

def _is_translation_result_abnormal(translated_text: str) -> bool:
    """
    检查翻译结果是否异常
    
    Args:
        translated_text: 翻译后的文本
        
    Returns:
        bool: 是否异常
    """
    if not translated_text:
        return True
    
    # 检查重复字符模式（如"方案方案方案方案"）
    import re
    
    # 检查是否有连续重复的字符或词组
    # 匹配模式：同一个字符或词组连续出现4次以上
    repeated_pattern = re.compile(r'(.{1,10})\1{3,}')
    if repeated_pattern.search(translated_text):
        return True
    
    # 检查是否包含大量特殊字符
    special_char_ratio = len(re.findall(r'[♂☼⚡]', translated_text)) / len(translated_text) if translated_text else 0
    if special_char_ratio > 0.1:  # 如果特殊字符占比超过10%
        return True
    
    # 检查是否全是重复的标点符号
    if re.match(r'^[，。！？、；：""''（）【】]+$', translated_text.strip()):
        return True
    
    return False

def check_qwen_availability():
    """
    检查Qwen翻译服务是否可用
    """
    try:
        if not dashscope_key:
            return False, "DASH_SCOPE_KEY未设置"
        
        # 测试连接
        client = OpenAI(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=dashscope_key
        )
        
        # 简单测试
        completion = client.chat.completions.create(
            model="qwen-mt-plus",
            messages=[{"role": "user", "content": "Hello"}],
            extra_body={"translation_options": {"source_lang": "auto", "target_lang": "zh"}}
        )
        
        return True, "Qwen翻译服务正常"
        
    except Exception as e:
        return False, f"Qwen翻译服务检查失败: {str(e)}" 