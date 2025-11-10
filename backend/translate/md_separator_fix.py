import os
import threading
import datetime
import time
import re
from . import to_translate
from . import common

def start(trans):
    """专门修复表格分隔行的markdown翻译函数"""
    # 允许的最大线程
    threads = trans['threads']
    if threads is None or int(threads) < 0:
        max_threads = 10
    else:
        max_threads = int(threads)
    
    run_index = 0
    start_time = datetime.datetime.now()

    try:
        with open(trans['file_path'], 'r', encoding='utf-8') as file:
            content = file.read()
    except Exception as e:
        print(f"无法读取文件 {trans['file_path']}: {e}")
        return False

    trans_type = trans['type']
    keepBoth = True
    if trans_type in ["trans_text_only_inherit", "trans_text_only_new", "trans_all_only_new", "trans_all_only_inherit"]:
        keepBoth = False

    # 使用专门修复表格分隔行的解析器
    parsed_elements = parse_markdown_separator_fix(content)
    
    # 支持最多单词量
    max_word = 1000
    texts = []
    
    for element in parsed_elements:
        # 检查是否需要翻译
        if element['type'] == 'text' and check_text(element['content']):
            # 普通文本内容需要翻译
            if len(element['content']) > max_word:
                # 分割长文本
                sub_paragraphs = split_paragraph(element['content'], max_word)
                for sub_paragraph in sub_paragraphs:
                    append_text(sub_paragraph, texts, True, element)
            else:
                append_text(element['content'], texts, False, element)
        elif element['type'] == 'table_row' and check_text(element['content']):
            # 表格数据行需要翻译
            if len(element['content']) > max_word:
                # 分割长文本
                sub_paragraphs = split_paragraph(element['content'], max_word)
                for sub_paragraph in sub_paragraphs:
                    append_text(sub_paragraph, texts, True, element)
            else:
                append_text(element['content'], texts, False, element)
        else:
            # 其他元素（表格分隔行、标题等）直接保留
            append_text(element['content'], texts, False, element, preserve=True)

    # 多线程翻译处理
    max_run = max_threads if len(texts) > max_threads else len(texts)
    before_active_count = threading.activeCount()
    event = threading.Event()
    
    # 进度更新相关变量
    completed_count = 0
    total_count = len(texts)
    progress_lock = threading.Lock()
    
    def update_progress():
        """更新翻译进度"""
        nonlocal completed_count
        with progress_lock:
            completed_count += 1
            progress_percentage = min((completed_count / total_count) * 100, 100.0)
            print(f"翻译进度: {completed_count}/{total_count} ({progress_percentage:.1f}%)")
            
            # 更新数据库进度
            try:
                from .to_translate import db
                db.execute("update translate set process=%s where id=%s", 
                         str(format(progress_percentage, '.1f')), 
                         trans['id'])
                
                if progress_percentage >= 100.0:
                    from datetime import datetime
                    import pytz
                    end_time = datetime.now(pytz.timezone('Asia/Shanghai'))
                    db.execute(
                        "update translate set status='done',end_at=%s,process=100 where id=%s",
                        end_time, trans['id']
                    )
                    print("✅ 翻译完成，状态已更新为已完成")
                    
            except Exception as e:
                print(f"更新进度失败: {str(e)}")
    
    # 启动翻译线程
    while run_index <= len(texts) - 1:
        if threading.activeCount() < max_run + before_active_count:
            if not event.is_set():
                thread = threading.Thread(target=to_translate.get, args=(trans, event, texts, run_index))
                thread.start()
                run_index += 1
            else:
                return False
    
    # 等待翻译完成
    while True:
        complete = True
        for text in texts:
            if not text['complete']:
                complete = False
                break
        if complete:
            break
        else:
            time.sleep(1)

    # 将翻译结果写入文件，保持原有结构
    try:
        with open(trans['target_file'], 'w', encoding='utf-8') as file:
            for i, item in enumerate(texts):
                if item.get('preserve', False):
                    # 保留格式的内容直接写入
                    file.write(item['text'])
                    # 如果不是最后一个项目，添加换行符
                    if i < len(texts) - 1:
                        file.write('\n')
                else:
                    # 翻译的内容
                    if keepBoth and item["origin"].strip() != "":
                        file.write(item["origin"] + '\n')
                    file.write(item["text"])
                    # 如果不是最后一个项目，添加换行符
                    if i < len(texts) - 1:
                        file.write('\n')
    except Exception as e:
        print(f"无法写入文件 {trans['target_file']}: {e}")
        return False

    end_time = datetime.datetime.now()
    spend_time = common.display_spend(start_time, end_time)
    to_translate.complete(trans, len(texts), spend_time)
    return True

def parse_markdown_separator_fix(content):
    """专门修复表格分隔行的markdown解析"""
    elements = []
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 检测各种markdown元素
        element = detect_markdown_element_separator_fix(line, lines, i)
        
        if element:
            elements.append(element)
            i += element.get('lines_consumed', 1)
        else:
            # 普通文本行
            elements.append({
                'type': 'text',
                'content': line,
                'format': 'paragraph',
                'lines_consumed': 1
            })
            i += 1
    
    return elements

def detect_markdown_element_separator_fix(line, lines, index):
    """专门修复表格分隔行的markdown元素检测"""
    line_stripped = line.strip()
    
    # 空行
    if not line_stripped:
        return {
            'type': 'empty',
            'content': line,
            'format': 'empty',
            'lines_consumed': 1,
            'force_preserve': True
        }
    
    # 标题
    if re.match(r'^#{1,6}\s+', line_stripped):
        return {
            'type': 'heading',
            'content': line,
            'format': 'heading',
            'level': len(line_stripped) - len(line_stripped.lstrip('#')),
            'lines_consumed': 1,
            'force_preserve': True
        }
    
    # 代码块
    if line_stripped.startswith('```') or line_stripped.startswith('~~~'):
        code_block = [line]
        i = index + 1
        while i < len(lines):
            code_block.append(lines[i])
            if lines[i].strip().startswith('```') or lines[i].strip().startswith('~~~'):
                break
            i += 1
        return {
            'type': 'code_block',
            'content': '\n'.join(code_block),
            'format': 'code_block',
            'lines_consumed': len(code_block),
            'force_preserve': True
        }
    
    # 无序列表
    if re.match(r'^[\*\-\+]\s+', line_stripped):
        return {
            'type': 'list_item',
            'content': line,
            'format': 'unordered_list',
            'lines_consumed': 1,
            'force_preserve': True
        }
    
    # 有序列表
    if re.match(r'^\d+\.\s+', line_stripped):
        return {
            'type': 'list_item',
            'content': line,
            'format': 'ordered_list',
            'lines_consumed': 1,
            'force_preserve': True
        }
    
    # 引用
    if line_stripped.startswith('>'):
        return {
            'type': 'quote',
            'content': line,
            'format': 'quote',
            'lines_consumed': 1,
            'force_preserve': True
        }
    
    # 水平线
    if re.match(r'^[-*_]{3,}$', line_stripped):
        return {
            'type': 'horizontal_rule',
            'content': line,
            'format': 'horizontal_rule',
            'lines_consumed': 1,
            'force_preserve': True
        }
    
    # 表格 - 专门修复表格分隔行检测
    if '|' in line and line.count('|') >= 2:
        # 检查是否是表格分隔行 - 使用更严格的正则表达式
        # 匹配格式：| ---- | ---- | ---- | 或 |:---|:---|:---| 等
        if re.match(r'^\s*\|[\s\-\|:]+\|\s*$', line_stripped) and line_stripped.count('|') == 5:
            return {
                'type': 'table_separator',
                'content': line,
                'format': 'table_separator',
                'lines_consumed': 1,
                'force_preserve': True,
                'table_element': True
            }
        else:
            # 表格数据行 - 需要翻译内容，但保留表格结构
            return {
                'type': 'table_row',
                'content': line,
                'format': 'table_row',
                'lines_consumed': 1,
                'force_preserve': False,  # 表格数据行需要翻译
                'table_element': True
            }
    
    # 链接和图片
    if re.search(r'\[.*?\]\(.*?\)', line) or re.search(r'!\[.*?\]\(.*?\)', line):
        return {
            'type': 'link_image',
            'content': line,
            'format': 'link_image',
            'lines_consumed': 1,
            'force_preserve': True
        }
    
    return None

def split_paragraph(paragraph, max_length):
    """将段落分割成多个部分，每部分不超过 max_length 字符，并考虑断句"""
    sentences = re.split(r'(?<=[.!?。！？;；:：…—]) +|(?<=[。！？；：…—])\s*', paragraph)
    current_length = 0
    current_part = []
    parts = []

    for sentence in sentences:
        if current_length + len(sentence) > max_length:
            if current_part:
                parts.append(' '.join(current_part))
                current_part = [sentence]
                current_length = len(sentence)
            else:
                parts.append(sentence)
                current_part = []
                current_length = 0
        else:
            current_part.append(sentence)
            current_length += len(sentence)

    if current_part:
        parts.append(' '.join(current_part))

    return parts

def append_text(text, texts, sub=False, element=None, preserve=False):
    """添加文本到翻译队列"""
    # 检查是否强制保留格式
    if element and element.get('force_preserve', False):
        preserve = True
    
    if preserve or not check_text(text):
        texts.append({
            "text": text, 
            "origin": text, 
            "complete": True, 
            "sub": sub, 
            "ext": "md",
            "preserve": preserve,
            "element_type": element['type'] if element else 'text',
            "format": element['format'] if element else 'paragraph'
        })
    else:
        texts.append({
            "text": text, 
            "origin": text, 
            "complete": False, 
            "sub": sub, 
            "ext": "md",
            "preserve": preserve,
            "element_type": element['type'] if element else 'text',
            "format": element['format'] if element else 'paragraph'
        })

def check_text(text):
    """检查文本是否需要翻译"""
    return text is not None and text != "\n" and len(text) > 0 and not common.is_all_punc(text)
