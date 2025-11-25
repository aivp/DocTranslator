"""
术语筛选模块

根据文本内容筛选最相关的术语，解决API Token限制问题。
保留现有术语库格式，动态选择最相关的术语。

作者：Claude
版本：2.0.0 - 性能优化版本（支持倒排索引）
"""

import re
import time
import logging
import hashlib
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
from functools import lru_cache

logger = logging.getLogger(__name__)

# 全局倒排索引缓存：{comparison_id: inverted_index}
_inverted_index_cache: Dict[str, Dict[str, List[Tuple[str, str]]]] = {}
# 倒排索引缓存访问时间：{comparison_id: last_access_time}
_inverted_index_cache_time: Dict[str, float] = {}

# 结果缓存：{text_hash: filtered_terms}
_result_cache: Dict[str, List[Dict[str, str]]] = {}
# 结果缓存访问时间：{text_hash: last_access_time}
_result_cache_time: Dict[str, float] = {}
_max_cache_size = 1000  # 最大缓存条目数

# 缓存过期时间（秒）：1小时未使用则过期
_cache_expire_time = 3600  # 1小时 = 3600秒

def calculate_similarity(text: str, term_source: str) -> float:
    """
    计算文本与术语的相似度分数
    
    Args:
        text: 要翻译的文本
        term_source: 术语原文
        
    Returns:
        float: 相似度分数 (0-100)
    """
    if not text or not term_source:
        return 0.0
    
    # 1. 精确匹配（最高分）
    if term_source in text:
        logger.debug(f"精确匹配: '{term_source}' in '{text[:50]}...'")
        return 100.0
    
    # 2. 忽略大小写的精确匹配
    if term_source.lower() in text.lower():
        logger.debug(f"忽略大小写匹配: '{term_source}' in '{text[:50]}...'")
        return 95.0
    
    # 3. 正则匹配
    try:
        if re.search(re.escape(term_source), text, re.IGNORECASE):
            logger.debug(f"正则匹配: '{term_source}' in '{text[:50]}...'")
            return 90.0
    except re.error:
        # 如果正则表达式有错误，跳过正则匹配
        pass
    
    # 4. 词频匹配（计算共同词汇）
    text_words = set(text.lower().split())
    term_words = set(term_source.lower().split())
    common_words = text_words & term_words
    
    if common_words:
        # 计算词汇重叠度
        overlap_ratio = len(common_words) / len(term_words)
        score = overlap_ratio * 70.0  # 最高70分
        logger.debug(f"词汇匹配: '{term_source}' 与 '{text[:50]}...' 重叠度 {overlap_ratio:.2f}")
        return score
    
    # 5. 序列相似度（模糊匹配）
    similarity = SequenceMatcher(None, text.lower(), term_source.lower()).ratio()
    if similarity > 0.3:  # 只考虑相似度大于30%的
        score = similarity * 50.0  # 最高50分
        logger.debug(f"序列相似度: '{term_source}' 与 '{text[:50]}...' 相似度 {similarity:.2f}")
        return score
    
    return 0.0

def _cleanup_expired_cache():
    """
    清理过期的缓存（倒排索引和结果缓存）
    """
    global _inverted_index_cache, _inverted_index_cache_time, _result_cache, _result_cache_time
    
    current_time = time.time()
    
    # 清理过期的倒排索引缓存
    expired_keys = []
    for key, last_access in _inverted_index_cache_time.items():
        if current_time - last_access > _cache_expire_time:
            expired_keys.append(key)
    
    for key in expired_keys:
        if key in _inverted_index_cache:
            del _inverted_index_cache[key]
        if key in _inverted_index_cache_time:
            del _inverted_index_cache_time[key]
    
    if expired_keys:
        logger.info(f"清理了 {len(expired_keys)} 个过期的倒排索引缓存")
    
    # 清理过期的结果缓存
    expired_result_keys = []
    for key, last_access in _result_cache_time.items():
        if current_time - last_access > _cache_expire_time:
            expired_result_keys.append(key)
    
    for key in expired_result_keys:
        if key in _result_cache:
            del _result_cache[key]
        if key in _result_cache_time:
            del _result_cache_time[key]
    
    if expired_result_keys:
        logger.info(f"清理了 {len(expired_result_keys)} 个过期的结果缓存")


def build_inverted_index(all_terms: Dict[str, str], comparison_id: Optional[str] = None) -> Dict[str, List[Tuple[str, str]]]:
    """
    为术语库建立倒排索引
    
    Args:
        all_terms: 所有术语字典 {source: target}
        comparison_id: 术语库ID（用于缓存）
        
    Returns:
        Dict: 倒排索引 {word: [(source, target), ...]}
    """
    if not all_terms:
        return {}
    
    # 定期清理过期缓存（每10次调用清理一次，避免频繁清理）
    if len(_inverted_index_cache) > 0 and len(_inverted_index_cache) % 10 == 0:
        _cleanup_expired_cache()
    
    # 检查缓存
    cache_key = comparison_id or str(id(all_terms))
    if cache_key in _inverted_index_cache:
        # 检查是否过期
        if cache_key in _inverted_index_cache_time:
            current_time = time.time()
            if current_time - _inverted_index_cache_time[cache_key] <= _cache_expire_time:
                # 更新访问时间
                _inverted_index_cache_time[cache_key] = current_time
                logger.debug(f"使用缓存的倒排索引，术语库大小: {len(all_terms)}")
                return _inverted_index_cache[cache_key]
            else:
                # 缓存已过期，删除
                logger.debug(f"倒排索引缓存已过期，重新构建")
                del _inverted_index_cache[cache_key]
                del _inverted_index_cache_time[cache_key]
    
    logger.info(f"开始建立倒排索引，术语库大小: {len(all_terms)}")
    start_time = time.time()
    
    inverted_index: Dict[str, List[Tuple[str, str]]] = {}
    
    for source, target in all_terms.items():
        # 对术语原文进行分词
        words = re.findall(r'\b\w+\b', source.lower())
        
        for word in words:
            if len(word) < 2:  # 跳过太短的词
                continue
            
            if word not in inverted_index:
                inverted_index[word] = []
            
            # 避免重复添加相同的术语
            term_pair = (source, target)
            if term_pair not in inverted_index[word]:
                inverted_index[word].append(term_pair)
    
    # 缓存索引
    if cache_key:
        _inverted_index_cache[cache_key] = inverted_index
        _inverted_index_cache_time[cache_key] = time.time()  # 记录缓存时间
    
    elapsed = time.time() - start_time
    logger.info(f"倒排索引建立完成，用时: {elapsed:.3f}秒, 索引词汇数: {len(inverted_index)}")
    
    return inverted_index


def filter_relevant_terms(text: str, all_terms: Dict[str, str], max_terms: int = 10, 
                         comparison_id: Optional[str] = None, use_index: bool = True) -> List[Dict[str, str]]:
    """
    根据文本内容筛选最相关的术语（优化版本，支持倒排索引）
    
    Args:
        text: 要翻译的文本
        all_terms: 所有术语字典 {source: target}
        max_terms: 最大术语数量（默认50个）
        comparison_id: 术语库ID（用于缓存索引）
        use_index: 是否使用倒排索引（默认True）
        
    Returns:
        List[Dict]: 筛选后的术语列表 [{"source": "...", "target": "..."}]
    """
    if not text or not all_terms:
        logger.debug("文本或术语库为空，返回空列表")
        return []
    
    # 检查结果缓存
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    cache_key = f"{comparison_id or ''}_{text_hash}"
    if cache_key in _result_cache:
        # 检查是否过期
        if cache_key in _result_cache_time:
            current_time = time.time()
            if current_time - _result_cache_time[cache_key] <= _cache_expire_time:
                # 更新访问时间
                _result_cache_time[cache_key] = current_time
                logger.debug(f"使用缓存的筛选结果")
                return _result_cache[cache_key]
            else:
                # 缓存已过期，删除
                logger.debug(f"结果缓存已过期，重新筛选")
                del _result_cache[cache_key]
                del _result_cache_time[cache_key]
    
    term_count = len(all_terms)
    logger.debug(f"开始筛选术语，文本长度: {len(text)}, 术语库大小: {term_count}")
    
    start_time = time.time()
    
    # 分词处理
    words = re.findall(r'\b\w+\b', text.lower())
    words = [w for w in words if len(w) >= 2]  # 过滤太短的词
    
    if not words:
        return []
    
    # 使用倒排索引优化（当术语库大于1000条时）
    if use_index and term_count > 1000:
        inverted_index = build_inverted_index(all_terms, comparison_id)
        
        # 先尝试精确匹配（提前终止优化）
        exact_matches = []
        text_lower = text.lower()
        
        for source, target in all_terms.items():
            source_lower = source.lower()
            # 精确匹配（最高优先级）
            if source in text or source_lower in text_lower:
                exact_matches.append({
                    'source': source,
                    'target': target,
                    'score': 100.0 if source in text else 95.0
                })
                # 如果找到足够多的精确匹配，可以提前终止
                if len(exact_matches) >= max_terms:
                    logger.debug(f"找到 {len(exact_matches)} 个精确匹配，提前终止")
                    result = [
                        {'source': term['source'], 'target': term['target']}
                        for term in exact_matches[:max_terms]
                    ]
                    # 缓存结果
                    if len(_result_cache) >= _max_cache_size:
                        keys_to_remove = list(_result_cache.keys())[:_max_cache_size // 2]
                        for key in keys_to_remove:
                            if key in _result_cache:
                                del _result_cache[key]
                            if key in _result_cache_time:
                                del _result_cache_time[key]
                    _result_cache[cache_key] = result
                    _result_cache_time[cache_key] = time.time()  # 记录缓存时间
                    return result
        
        # 通过索引快速查找相关术语
        candidate_terms = {}  # {source: (target, max_score)}
        
        # 如果已有精确匹配，优先保留
        for match in exact_matches:
            candidate_terms[match['source']] = (match['target'], match['score'])
        
        # 通过索引查找其他相关术语
        for word in words:
            if word in inverted_index:
                # 从索引中获取包含该词汇的术语
                for source, target in inverted_index[word]:
                    # 跳过已找到的精确匹配
                    if source in candidate_terms and candidate_terms[source][1] >= 95.0:
                        continue
                    
                    # 计算相似度分数
                    score = calculate_word_similarity(word, source)
                    if score > 0:
                        term_key = source
                        if term_key not in candidate_terms or score > candidate_terms[term_key][1]:
                            candidate_terms[term_key] = (target, score)
        
        # 转换为列表并排序
        scored_terms = [
            {'source': source, 'target': target, 'score': score}
            for source, (target, score) in candidate_terms.items()
        ]
        scored_terms.sort(key=lambda x: x['score'], reverse=True)
        
        # 限制数量
        selected_terms = scored_terms[:max_terms]
        
        # 转换为标准格式
        result = [
            {'source': term['source'], 'target': term['target']}
            for term in selected_terms
        ]
        
    else:
        # 小术语库或禁用索引时，使用原始方法
        logger.debug("使用原始方法筛选术语（术语库较小或禁用索引）")
        
        # 为每个词汇找到最相关的术语
        word_term_mapping = {}  # {word: [terms]}
        
        for word in words:
            word_terms = []
            for source, target in all_terms.items():
                score = calculate_word_similarity(word, source)
                if score > 0:
                    word_terms.append({
                        'source': source,
                        'target': target,
                        'score': score,
                        'matched_word': word
                    })
            
            # 按分数排序，每个词汇最多取5个最相关的术语
            word_terms.sort(key=lambda x: x['score'], reverse=True)
            word_term_mapping[word] = word_terms[:5]
        
        # 合并所有词汇的术语，去重
        all_scored_terms = {}
        for word, terms in word_term_mapping.items():
            for term in terms:
                term_key = f"{term['source']}:{term['target']}"
                if term_key not in all_scored_terms:
                    all_scored_terms[term_key] = term
                else:
                    if term['score'] > all_scored_terms[term_key]['score']:
                        all_scored_terms[term_key] = term
        
        # 转换为列表并排序
        scored_terms = list(all_scored_terms.values())
        scored_terms.sort(key=lambda x: x['score'], reverse=True)
        
        # 限制总数不超过max_terms
        selected_terms = scored_terms[:max_terms]
        
        # 转换为标准格式
        result = [
            {'source': term['source'], 'target': term['target']}
            for term in selected_terms
        ]
    
    # 缓存结果
    if len(_result_cache) >= _max_cache_size:
        # 清除最旧的缓存（简单策略：清除一半）
        keys_to_remove = list(_result_cache.keys())[:_max_cache_size // 2]
        for key in keys_to_remove:
            if key in _result_cache:
                del _result_cache[key]
            if key in _result_cache_time:
                del _result_cache_time[key]
    
    _result_cache[cache_key] = result
    _result_cache_time[cache_key] = time.time()  # 记录缓存时间
    
    elapsed = time.time() - start_time
    logger.debug(f"术语筛选完成: {term_count} -> {len(result)} 个术语, 用时: {elapsed:.3f}秒")
    
    return result

def calculate_word_similarity(word: str, term_source: str) -> float:
    """
    计算单个词汇与术语的相似度
    
    Args:
        word: 单个词汇
        term_source: 术语原文
        
    Returns:
        float: 相似度分数 (0-100)
    """
    if not word or not term_source:
        return 0.0
    
    # 1. 精确匹配（最高分）
    if word == term_source.lower():
        logger.debug(f"词汇精确匹配: '{word}' == '{term_source}'")
        return 100.0
    
    # 2. 词汇包含关系
    if word in term_source.lower():
        logger.debug(f"词汇包含匹配: '{word}' in '{term_source}'")
        return 90.0
    
    # 3. 术语包含词汇
    if term_source.lower() in word:
        logger.debug(f"术语包含词汇: '{term_source}' in '{word}'")
        return 85.0
    
    # 4. 词汇重叠度
    word_chars = set(word)
    term_chars = set(term_source.lower())
    common_chars = word_chars & term_chars
    
    if common_chars:
        overlap_ratio = len(common_chars) / max(len(word_chars), len(term_chars))
        if overlap_ratio > 0.5:  # 字符重叠度大于50%
            score = overlap_ratio * 70.0
            logger.debug(f"字符重叠匹配: '{word}' 与 '{term_source}' 重叠度 {overlap_ratio:.2f}")
            return score
    
    # 5. 序列相似度（模糊匹配）
    similarity = SequenceMatcher(None, word, term_source.lower()).ratio()
    if similarity > 0.6:  # 相似度大于60%
        score = similarity * 60.0
        logger.debug(f"序列相似度: '{word}' 与 '{term_source}' 相似度 {similarity:.2f}")
        return score
    
    return 0.0

def optimize_terms_for_api(text: str, all_terms: Dict[str, str], max_terms: int = 10, 
                           comparison_id: Optional[str] = None) -> List[Dict[str, str]]:
    """
    为API调用优化术语库（优化版本，支持倒排索引和缓存）
    严格限制术语数量和字符数，避免API超时
    
    Args:
        text: 要翻译的文本
        all_terms: 所有术语字典 {source: target}
        max_terms: 最大术语数量（默认50，但会根据术语库大小和字符数进一步限制）
        comparison_id: 术语库ID（用于缓存索引和结果）
        
    Returns:
        List[Dict]: 优化后的术语列表，格式与Qwen API兼容
    """
    # 记录开始时间
    start_time = time.time()
    
    # 严格限制：避免传入过多术语导致API超时
    # 统一限制：最多10个术语（无论术语库大小）
    strict_max_terms = min(10, max_terms)
    if len(all_terms) > 1000:
        logger.info(f"术语库检测（{len(all_terms)}条），使用严格筛选：最多{strict_max_terms}个术语")
    
    # 使用优化版本的筛选函数（自动使用倒排索引）
    relevant_terms = filter_relevant_terms(text, all_terms, strict_max_terms, comparison_id, use_index=True)
    
    # 检查术语库大小和字符数，进一步优化以避免API超时
    # 统一限制：最多10个术语，最多1000字符
    MAX_TERMS_COUNT = 10  # 最多10个术语
    MAX_CHARS_LIMIT = 1000  # 最多1000字符
    
    # 先按相似度重新评分并排序
    scored_terms = []
    for term in relevant_terms:
        score = calculate_similarity(text, term['source'])
        scored_terms.append((term, score))
    
    scored_terms.sort(key=lambda x: x[1], reverse=True)
    
    # 根据字符数和数量限制，选择最相关的术语
    optimized_terms = []
    current_chars = 0
    term_count = 0
    
    for term, score in scored_terms:
        # 检查数量限制
        if term_count >= MAX_TERMS_COUNT:
            logger.debug(f"达到最大术语数量限制（{MAX_TERMS_COUNT}个），停止添加")
            break
        
        term_chars = len(term['source']) + len(term['target'])
        
        # 检查字符数限制
        if current_chars + term_chars > MAX_CHARS_LIMIT:
            logger.debug(f"达到最大字符数限制（{MAX_CHARS_LIMIT}字符），当前: {current_chars}，停止添加")
            break
        
        optimized_terms.append(term)
        current_chars += term_chars
        term_count += 1
    
    # 计算总用时
    end_time = time.time()
    duration = end_time - start_time
    
    if len(optimized_terms) < len(relevant_terms):
        logger.info(f"📚 术语库优化完成: {len(relevant_terms)} -> {len(optimized_terms)} 个术语, 字符数: {current_chars}, 用时: {duration:.3f}秒")
    else:
        logger.debug(f"📚 术语筛选完成: {len(optimized_terms)} 个术语, 字符数: {current_chars}, 用时: {duration:.3f}秒")
    
    return optimized_terms
    
    # 如果筛选后的术语仍然太多，进一步优化
    if len(relevant_terms) > 15:
        # 重新评分并只保留最相关的15个
        scored_terms = []
        for term in relevant_terms:
            score = calculate_similarity(text, term['source'])
            scored_terms.append((term, score))
        
        scored_terms.sort(key=lambda x: x[1], reverse=True)
        relevant_terms = [term for term, _ in scored_terms[:15]]
        logger.debug(f"进一步优化：限制为最相关的15个术语")
    
    # 检查字符数限制（1500字符）
    total_chars = sum(len(term['source']) + len(term['target']) for term in relevant_terms)
    if total_chars > 1500:
        # 按分数排序，优先保留高分术语
        scored_terms = []
        for term in relevant_terms:
            score = calculate_similarity(text, term['source'])
            scored_terms.append((term, score))
        
        scored_terms.sort(key=lambda x: x[1], reverse=True)
        
        # 逐步减少术语数量，直到满足字符限制
        optimized_terms = []
        current_chars = 0
        for term, score in scored_terms:
            term_chars = len(term['source']) + len(term['target'])
            if current_chars + term_chars <= 1500:
                optimized_terms.append(term)
                current_chars += term_chars
            else:
                break
        
        logger.debug(f"字符数优化：{len(relevant_terms)} -> {len(optimized_terms)} 个术语, {total_chars} -> {current_chars} 字符")
        relevant_terms = optimized_terms
    
    # 计算总用时
    end_time = time.time()
    duration = end_time - start_time
    logger.debug(f"📚 术语筛选算法用时: {duration:.3f}秒, 筛选结果: {len(relevant_terms)}个术语")
    
    return relevant_terms


def clear_term_cache(comparison_id: Optional[str] = None):
    """
    清除术语库缓存
    
    Args:
        comparison_id: 术语库ID，如果为None则清除所有缓存
    """
    global _inverted_index_cache, _inverted_index_cache_time, _result_cache, _result_cache_time
    
    if comparison_id:
        if comparison_id in _inverted_index_cache:
            del _inverted_index_cache[comparison_id]
            logger.info(f"已清除术语库 {comparison_id} 的倒排索引缓存")
        if comparison_id in _inverted_index_cache_time:
            del _inverted_index_cache_time[comparison_id]
        
        # 清除相关的结果缓存
        keys_to_remove = [k for k in _result_cache.keys() if k.startswith(f"{comparison_id}_")]
        for key in keys_to_remove:
            if key in _result_cache:
                del _result_cache[key]
            if key in _result_cache_time:
                del _result_cache_time[key]
        logger.info(f"已清除术语库 {comparison_id} 的结果缓存，共 {len(keys_to_remove)} 条")
    else:
        _inverted_index_cache.clear()
        _inverted_index_cache_time.clear()
        _result_cache.clear()
        _result_cache_time.clear()
        logger.info("已清除所有术语库缓存")

def batch_filter_terms(texts: List[str], all_terms: Dict[str, str], max_terms: int = 10) -> List[List[Dict[str, str]]]:
    """
    批量筛选术语（用于多文本翻译）
    
    Args:
        texts: 要翻译的文本列表
        all_terms: 所有术语字典 {source: target}
        max_terms: 每个文本的最大术语数量
        
    Returns:
        List[List[Dict]]: 每个文本对应的术语列表
    """
    results = []
    for i, text in enumerate(texts):
        logger.debug(f"处理第 {i+1}/{len(texts)} 个文本")
        terms = optimize_terms_for_api(text, all_terms, max_terms)
        results.append(terms)
    
    return results 