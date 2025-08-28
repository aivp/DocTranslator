"""
阿里云Qwen-MT翻译模型集成
"""
import logging
import os
import time
from openai import OpenAI

# 从环境变量获取API密钥
dashscope_key = os.environ.get('DASH_SCOPE_KEY', '')

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
        logging.error("达到429错误最大重试次数 (100)，返回原文")
        return False  # 停止重试

def qwen_translate(text, target_language, source_lang="auto", tm_list=None, terms=None, domains=None, max_retries=10):
    """
    使用阿里云Qwen-MT翻译模型进行翻译
    """
    
    # 输入验证
    if not text or not text.strip():
        logging.warning("输入文本为空，跳过翻译")
        return text
    
    if not target_language:
        logging.error("目标语言未指定")
        return text
    
    # 记录开始时间
    start_time = time.time()
    logging.info(f"🚀 开始Qwen翻译: {text[:100]}... -> {target_language}")
    
    for attempt in range(max_retries):
        try:
            # 检查API密钥
            if not dashscope_key:
                logging.error("❌ DASH_SCOPE_KEY未设置或为空")
                return text
                
            logging.info(f"🔄 Qwen翻译尝试 {attempt + 1}/{max_retries}")
            
            # 初始化 OpenAI 客户端
            client = OpenAI(
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                api_key=dashscope_key,
                timeout=60.0  # 增加超时时间
            ) 
            
            # 设置翻译参数 - 根据官方文档格式
            translation_options = {
                "source_lang": source_lang,
                "target_lang": target_language
            }
            
            # 添加可选参数
            if tm_list is not None:
                translation_options["terms"] = tm_list
                logging.info(f"📚 使用术语库: {len(tm_list)} 个术语")
            elif terms is not None:
                translation_options["terms"] = terms
                logging.info(f"📚 使用自定义术语: {len(terms)} 个术语")
            
            # 硬编码domains参数 - 工程车辆和政府文件领域
            translation_options["domains"] = "This text is from the engineering vehicle and construction machinery domain, as well as government and official document domain. It involves heavy machinery, construction equipment, industrial vehicles, administrative procedures, policy documents, and official notices. The content includes professional terminology related to vehicle design, mechanical engineering, hydraulic systems, electrical controls, safety standards, operational procedures, formal language, official terminology, administrative procedures, legal references, and institutional communication. Pay attention to technical accuracy, industry-specific terminology, professional engineering language, formal and authoritative tone, bureaucratic language patterns, official document structure, and administrative terminology. Maintain formal and precise technical descriptions suitable for engineering documentation and technical manuals, as well as the serious, formal, and official style appropriate for government communications and administrative documents."
            logging.info(f"🎯 使用硬编码领域提示: 工程车辆和政府文件")
                
            # 添加详细的请求参数日志
            logging.info(f"🔧 Qwen翻译请求参数:")
            logging.info(f"  model: qwen-mt-plus")
            logging.info(f"  source_lang: {source_lang}")
            logging.info(f"  target_lang: {target_language}")
            logging.info(f"  translation_options: {translation_options}")
            logging.info(f"  text: {text[:100]}...")
            
            # 等待请求间隔
            wait_for_rate_limit()
            
            # 记录API调用开始时间
            api_start_time = time.time()
            
            # 调用API
            logging.info(f"📡 发送API请求...")
            completion = client.chat.completions.create(
                model="qwen-mt-plus",
                messages=[{"role": "user", "content": text}],
                extra_body={"translation_options": translation_options}
            )
            
            # 提取翻译结果
            if not completion.choices or len(completion.choices) == 0:
                logging.warning(f"⚠️ API返回结果为空，跳过此文本: {text[:50]}...")
                return ""  # 直接返回空字符串，不重试
                
            translated_text = completion.choices[0].message.content
            if not translated_text or not translated_text.strip():
                logging.warning(f"⚠️ 翻译结果为空，跳过此文本: {text[:50]}...")
                return ""  # 直接返回空字符串，不重试
            
            # 检查翻译结果质量（暂时注释掉）
            # if _is_translation_result_abnormal(translated_text):
            #     logging.warning(f"⚠️  检测到异常翻译结果: {translated_text[:100]}...")
            #     raise Exception("翻译结果异常，可能包含重复字符或错误内容")
            
            # 计算API调用用时
            api_end_time = time.time()
            api_duration = api_end_time - api_start_time
            total_duration = api_end_time - start_time
            
            logging.info(f"✅ 翻译成功: {translated_text[:100]}...")
            logging.info(f"⏱️ API调用用时: {api_duration:.3f}秒, 总用时: {total_duration:.3f}秒")
            return translated_text
            
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
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
                    logging.error(f"🚫 达到429错误最大重试次数，返回原文")
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