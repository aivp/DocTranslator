"""
术语筛选模块

根据文本内容筛选最相关的术语，解决API Token限制问题。
保留现有术语库格式，动态选择最相关的术语。

作者：Claude
版本：1.0.0
"""

import re
import logging
from typing import Dict, List, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

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

def filter_relevant_terms(text: str, all_terms: Dict[str, str], max_terms: int = 50) -> List[Dict[str, str]]:
    """
    根据文本内容筛选最相关的术语（按词汇匹配）
    
    Args:
        text: 要翻译的文本
        all_terms: 所有术语字典 {source: target}
        max_terms: 最大术语数量（默认50个）
        
    Returns:
        List[Dict]: 筛选后的术语列表 [{"source": "...", "target": "..."}]
    """
    if not text or not all_terms:
        logger.debug("文本或术语库为空，返回空列表")
        return []
    
    logger.info(f"开始词汇匹配筛选术语，文本长度: {len(text)}, 术语库大小: {len(all_terms)}")
    
    # 分词处理（简单按空格和标点符号分词）
    import re
    words = re.findall(r'\b\w+\b', text.lower())
    logger.debug(f"文本分词结果: {words}")
    
    # 为每个词汇找到最相关的术语
    word_term_mapping = {}  # {word: [terms]}
    
    for word in words:
        if len(word) < 2:  # 跳过太短的词
            continue
            
        word_terms = []
        for source, target in all_terms.items():
            # 计算词汇与术语的匹配度
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
                # 如果已存在，取最高分
                if term['score'] > all_scored_terms[term_key]['score']:
                    all_scored_terms[term_key] = term
    
    # 转换为列表并排序
    scored_terms = list(all_scored_terms.values())
    scored_terms.sort(key=lambda x: x['score'], reverse=True)
    
    # 限制总数不超过max_terms
    selected_terms = scored_terms[:max_terms]
    
    # 转换为标准格式
    result = []
    for term in selected_terms:
        result.append({
            'source': term['source'],
            'target': term['target']
        })
    
    # logger.info(f"术语筛选完成: {len(all_terms)} -> {len(result)} 个术语")
    
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

def optimize_terms_for_api(text: str, all_terms: Dict[str, str], max_terms: int = 50) -> List[Dict[str, str]]:
    """
    为API调用优化术语库
    
    Args:
        text: 要翻译的文本
        all_terms: 所有术语字典 {source: target}
        max_terms: 最大术语数量
        
    Returns:
        List[Dict]: 优化后的术语列表，格式与Qwen API兼容
    """
    # 筛选相关术语
    relevant_terms = filter_relevant_terms(text, all_terms, max_terms)
    
    # 检查术语库大小
    total_chars = sum(len(term['source']) + len(term['target']) for term in relevant_terms)
    # 如果术语库太大，进一步优化
    if total_chars > 2000:  # 假设2000字符为安全限制
        # logger.info(f"术语库过大({total_chars}字符)，进行优化")
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
            if current_chars + term_chars <= 2000:
                optimized_terms.append(term)
                current_chars += term_chars
            else:
                break
        
        # logger.info(f"术语库优化完成: {len(optimized_terms)}个术语")
        return optimized_terms
    
    return relevant_terms

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