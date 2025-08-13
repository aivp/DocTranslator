import threading
from docx import Document
from docx.oxml.ns import qn
from . import to_translate
from . import common
import os
import time
import datetime
import zipfile
import xml.etree.ElementTree as ET
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import tempfile
import shutil
import logging
from typing import List, Dict, Any, Optional
from ..utils.word_run_optimizer import SafeRunMerger, quick_optimize
from docx.text.paragraph import Paragraph

# 线程安全打印锁
print_lock = Lock()

def cleanup_temp_file(temp_path: str):
    """清理临时文件"""
    try:
        if temp_path and os.path.exists(temp_path) and 'optimized_' in os.path.basename(temp_path):
            # 删除临时文件
            os.remove(temp_path)
            # 删除临时目录
            temp_dir = os.path.dirname(temp_path)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        print(f"清理临时文件失败: {str(e)}")

# 特殊符号和数学符号的正则表达式
SPECIAL_SYMBOLS_PATTERN = re.compile(
    r'^[★☆♥♦♣♠♀♂☼☾☽♪♫♬☑☒✓✔✕✖✗✘⊕⊗∞∑∏πΠ±×÷√∛∜∫∮∇∂∆∏∑√∝∞∟∠∡∢∣∤∥∦∧∨∩∪∫∬∭∮∯∰∱∲∳∴∵∶∷∸∹∺∻∼∽∾∿≀≁≂≃≄≅≆≇≈≉≊≋≌≍≎≏≐≑≒≓≔≕≖≗≘≙≚≛≜≝≞≟≠≡≢≣≤≥≦≧≨≩≪≫≬≭≮≯≰≱≲≳≴≵≶≷≸≹≺≻≼≽≾≿⊀⊁⊂⊃⊄⊅⊆⊇⊈⊉⊊⊋⊌⊍⊎⊏⊐⊑⊒⊓⊔⊕⊖⊗⊘⊙⊚⊛⊜⊝⊞⊟⊠⊡⊢⊣⊤⊥⊦⊧⊨⊩⊪⊫⊬⊭⊮⊯⊰⊱⊲⊳⊴⊵⊶⊷⊸⊹⊺⊻⊼⊽⊾⊿⋀⋁⋂⋃⋄⋅⋆⋇⋈⋉⋊⋋⋌⋍⋎⋏⋐⋑⋒⋓⋔⋕⋖⋗⋘⋙⋚⋛⋜⋝⋞⋟⋠⋡⋢⋣⋤⋥⋦⋧⋨⋩⋪⋫⋬⋭⋮⋯⋰⋱⋲⋳⋴⋵⋶⋷⋸⋹⋺⋻⋼⋽⋾⋿]+$')

# 纯数字和简单标点的正则表达式
NUMBERS_PATTERN = re.compile(r'^[\d\s\.,\-\+\*\/\(\)\[\]\{\}]+$')

# 添加目录页码模式
TOC_PAGE_PATTERN = re.compile(r'[\s\-—_]+\d+$')


def check_if_image(run):
    """检查run是否包含图片"""
    namespaces = run.element.nsmap
    drawing = run.element.find('.//w:drawing', namespaces)
    if drawing is not None:
        blip = drawing.find('.//a:blip', {**namespaces, 'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'})
        if blip is not None:
            return True
    if run.element.find('.//w:object', namespaces) is not None:
        return True
    if run.element.find('.//w:pict', namespaces) is not None:
        return True
    return False

def check_if_textbox(run):
    """检查run是否包含文本框"""
    namespaces = {**run.element.nsmap, 'v': 'urn:schemas-microsoft-com:vml'}
    # 检查 DrawingML 文本框
    drawing = run.element.find('.//w:drawing', namespaces)
    if drawing is not None:
        txbx = drawing.find('.//w:txbxContent', {**namespaces, 'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})
        if txbx is not None:
            return True
    
    # 检查 VML 文本框
    vtextbox = run.element.find('.//v:textbox', namespaces)
    if vtextbox is not None:
        # VML 文本框内部通常有 w:txbxContent
        txbx = vtextbox.find('.//w:txbxContent', namespaces)
        if txbx is not None:
            return True
    
    return False


def clear_image(paragraph):
    """清除段落中的图片，但保留文本内容"""
    runs_to_remove = []
    for run in paragraph.runs:
        if check_if_image(run):
            runs_to_remove.append(run)
    
    # 从后往前删除，避免索引变化
    for run in reversed(runs_to_remove):
        try:
            run._element.getparent().remove(run._element)
        except:
            pass





def start(trans):
    """主入口函数，处理Word文档翻译"""
    # 初始化线程设置
    max_threads = 10 if not trans.get('threads') else int(trans['threads'])
    start_time = datetime.datetime.now()

    # ============== Word文档翻译配置 ==============
    print(f"Word文档翻译：使用 {trans.get('model', 'unknown')} 模型")
    
    # 如果用户选择了qwen-mt-plus，检查服务可用性
    if trans.get('model') == 'qwen-mt-plus':
        try:
            trans['server'] = 'qwen'
            # 建议线程数（Qwen并发已提升到840次/分钟）
            if max_threads > 20:
                print(f"建议: 当前线程数 {max_threads}，建议设置为 10-20 以获得最佳性能")
            elif max_threads < 5:
                print(f"建议: 当前线程数 {max_threads}，可以适当增加到 10-20 以提升翻译速度")
            from .qwen_translate import check_qwen_availability
            qwen_available, qwen_message = check_qwen_availability()
            print(f"Qwen服务检查: {qwen_message}")
            if not qwen_available:
                print("警告: Qwen服务不可用，但将继续尝试使用")
        except ImportError:
            print("警告: Qwen模块未找到，将使用默认翻译服务")
    


    # ============== 译文形式处理 ==============
    trans_type = trans.get('type', 'trans_text_only_inherit')  # 默认继承原版面
    print(f"译文形式: {trans_type}")
    # ===========================================

    # ============== Word文档预处理 ==============
    print("开始Word文档预处理...")
    
    # 创建临时文件路径
    temp_dir = tempfile.mkdtemp()
    base_name = os.path.basename(trans['file_path'])
    optimized_path = os.path.join(temp_dir, f"optimized_{base_name}")
    
    try:
        # 使用word-run-optimizer进行预处理
        stats = quick_optimize(trans['file_path'], optimized_path)
        print(f"Word预处理完成: {stats.get('merged_runs', 0)} 个runs被合并")
        optimized_doc_path = optimized_path
    except Exception as e:
        print(f"Word预处理失败，使用原文档: {str(e)}")
        optimized_doc_path = trans['file_path']
    # ===========================================
    # optimized_doc_path = trans['file_path'] #启用以跳过预处理

    # 加载Word文档
    try:
        document = Document(optimized_doc_path)
    except Exception as e:
        to_translate.error(trans['id'], f"文档加载失败: {str(e)}")
        # 清理临时文件
        cleanup_temp_file(optimized_doc_path)
        return False

    # 提取需要翻译的文本
    texts = []
    
    try:
        # 直接使用多线程提取，简化配置
        # extract_threads = min(4, max_threads)  # 文本提取使用较少的线程
        extract_threads = max_threads
        extract_content_for_translation(document, trans['file_path'], texts, extract_threads)
    except Exception as e:
        to_translate.error(trans['id'], f"文本提取失败: {str(e)}")
        # 清理临时文件
        cleanup_temp_file(optimized_doc_path)
        return False

    # 过滤掉特殊符号和纯数字
    filtered_texts = []
    for i, item in enumerate(texts):
        if should_translate(item['text']):
            filtered_texts.append(item)
        else:
            # 对于不需要翻译的内容，标记为已完成
            item['complete'] = True
            with print_lock:
                print(f"跳过翻译: {item['text'][:30]}..." if len(
                    item['text']) > 30 else f"跳过翻译: {item['text']}")

    # 多线程翻译
    run_translation(trans, filtered_texts, max_threads)

    # ============== 写入翻译结果 ==============
    # 检查是否启用自适应样式
    use_adaptive_styles = trans.get('adaptive_styles', False)  # 默认不启用
    
    if use_adaptive_styles:
        print("启用样式自适应功能：字体大小和行间距将根据翻译后文本长度自动调整")
        text_count = apply_translations_with_adaptive_styles(document, texts)
    else:
        print("使用原始样式：保持原始字体大小和行间距")
        text_count = apply_translations(document, texts)
    # ===========================================

    # 保存文档
    docx_path = trans['target_file']
    document.save(docx_path)

    # 处理批注等特殊元素
    update_special_elements(docx_path, texts)

    # 完成处理
    end_time = datetime.datetime.now()
    spend_time = common.display_spend(start_time, end_time)
    
    # 清理临时文件
    cleanup_temp_file(optimized_doc_path)
    
    if trans['run_complete']:
        to_translate.complete(trans, text_count, spend_time)
    return True


def should_translate(text):
    """判断文本是否需要翻译（过滤特殊符号和纯数字）"""
    if not text or len(text) == 0:
        return False

    # 过滤纯特殊符号
    if SPECIAL_SYMBOLS_PATTERN.match(text):
        return False

    # 过滤纯数字和简单标点
    if NUMBERS_PATTERN.match(text):
        return False

    # 过滤全是标点符号的文本
    if common.is_all_punc(text):
        return False

    return True


def extract_hyperlink_with_merge(hyperlink, texts):
    """提取超链接内容，使用保守run合并"""
    hyperlink_runs = list(hyperlink.runs)
    
    # 使用保守的run合并策略
    merged_runs = conservative_run_merge(hyperlink_runs)
    
    for merged_item in merged_runs:
        if not check_text(merged_item['text']):
            continue
        
        texts.append({
            "text": merged_item['text'],
            "type": "merged_run",
            "merged_item": merged_item,
            "complete": False,
            "context_type": "hyperlink"  # 标记为超链接
        })


def extract_paragraph_with_merge(paragraph, texts, context_type):
    """提取段落内容，使用保守run合并（不添加上下文）"""
    paragraph_runs = list(paragraph.runs)
    
    # 使用保守的run合并策略
    merged_runs = conservative_run_merge(paragraph_runs)
    
    for merged_item in merged_runs:
        if not check_text(merged_item['text']):
            continue
        
        # 检查是否包含图片，如果包含则跳过
        has_image = False
        for run in merged_item['runs']:
            if check_if_image(run):
                has_image = True
                break
        
        if has_image:
            continue
        
        # 过滤纯数字
        if NUMBERS_PATTERN.match(merged_item['text']):
            continue
        
        # 检查是否可能是目录项（以 -数字 或 —数字 结尾）
        match = TOC_PAGE_PATTERN.search(merged_item['text'])
        if match and context_type == "body":  # 假设目录在body
            page_num = match.group(0)
            main_text = merged_item['text'][:match.start()].rstrip()
            
            if main_text and should_translate(main_text):
                # 创建文本项
                texts.append({
                    "text": main_text,
                    "type": "merged_run",
                    "merged_item": merged_item,  # 共享runs，翻译后需小心替换
                    "complete": False,
                    "context_type": context_type,
                    "is_toc_text": True,
                    "original_page_num": page_num
                })
            
                # 创建页码项（不翻译）
                if should_translate(page_num):  # 额外检查，但纯数字应False
                    texts.append({
                        "text": page_num,
                        "type": "merged_run",
                        "merged_item": {'text': page_num, 'runs': merged_item['runs'][-1:], 'type': 'single'},  # 取最后一个run作为页码
                        "complete": False,  # 如果需要翻译
                        "context_type": context_type,
                        "is_toc_page": True
                    })
                else:
                    texts.append({
                        "text": page_num,
                        "type": "merged_run",
                        "merged_item": {'text': page_num, 'runs': merged_item['runs'][-1:], 'type': 'single'},
                        "complete": True,
                        "context_type": context_type,
                        "is_toc_page": True
                    })
        else:
            texts.append({
                "text": merged_item['text'],
                "type": "merged_run",
                "merged_item": merged_item,
                "complete": False,
                "context_type": context_type  # 标记类型
            })


def extract_content_for_translation(document, file_path, texts, max_threads=4):
    """提取需要翻译的内容，使用安全的多线程并行处理"""
    
    # 线程安全的文本列表
    from threading import Lock
    texts_lock = Lock()
    
    def add_text_safe(text_item):
        """线程安全地添加文本项"""
        with texts_lock:
            texts.append(text_item)
    
    def process_paragraphs_parallel():
        """并行处理段落（保持顺序）"""
        # 将段落分组，每组包含连续的段落
        paragraph_groups = []
        current_group = []
        
        for i, paragraph in enumerate(document.paragraphs):
            current_group.append((i, paragraph))
            
            # 每10个段落为一组，或者遇到表格时分组
            if len(current_group) >= 10 or (i < len(document.paragraphs) - 1 and 
                hasattr(document.paragraphs[i+1], '_element') and 
                document.paragraphs[i+1]._element.getnext() is not None):
                paragraph_groups.append(current_group)
                current_group = []
        
        if current_group:
            paragraph_groups.append(current_group)
        
        def process_paragraph_group(group):
            """处理一组连续的段落"""
            local_texts = []
            
            for index, paragraph in group:
                # 处理正文段落（跳过超链接run）
                extract_paragraph_with_context(paragraph, local_texts, "body")
                
                # 处理超链接
                for hyperlink in paragraph.hyperlinks:
                    extract_hyperlink_with_merge(hyperlink, local_texts)
                
                # 处理段落中的文本框
                for run in paragraph.runs:
                    if check_if_textbox(run):
                        # 处理 DrawingML
                        drawing_elem = run.element.find('.//w:drawing', run.element.nsmap)
                        if drawing_elem is not None:
                            txbx_elem = drawing_elem.find('.//w:txbxContent', drawing_elem.nsmap)
                            if txbx_elem is not None:
                                for p_elem in txbx_elem:
                                    if p_elem.tag == qn('w:p'):
                                        tb_para = Paragraph(p_elem, paragraph)
                                        extract_paragraph_with_merge(tb_para, local_texts, "textbox")
                        
                        # 处理 VML
                        namespaces = {**run.element.nsmap, 'v': 'urn:schemas-microsoft-com:vml'}
                        vtextbox_elem = run.element.find('.//v:textbox', namespaces)
                        if vtextbox_elem is not None:
                            txbx_elem = vtextbox_elem.find('.//w:txbxContent', namespaces)
                            if txbx_elem is not None:
                                for p_elem in txbx_elem:
                                    if p_elem.tag == qn('w:p'):
                                        tb_para = Paragraph(p_elem, paragraph)
                                        extract_paragraph_with_merge(tb_para, local_texts, "textbox")
            
            # 线程安全地添加到主列表
            for text_item in local_texts:
                add_text_safe(text_item)
        
        # 使用线程池并行处理段落组
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(process_paragraph_group, group) 
                      for group in paragraph_groups]
            for future in as_completed(futures):
                future.result()
    
    def process_tables_parallel():
        """并行处理表格（表格之间无依赖）"""
        def process_table(table):
            local_texts = []
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        extract_paragraph_with_merge(paragraph, local_texts, "table")
                        # 处理表格中的超链接
                        for hyperlink in paragraph.hyperlinks:
                            extract_hyperlink_with_merge(hyperlink, local_texts)
                        # 处理表格单元格中的文本框
                        for run in paragraph.runs:
                            if check_if_textbox(run):
                                # 处理 DrawingML
                                drawing_elem = run.element.find('.//w:drawing', run.element.nsmap)
                                if drawing_elem is not None:
                                    txbx_elem = drawing_elem.find('.//w:txbxContent', drawing_elem.nsmap)
                                    if txbx_elem is not None:
                                        for p_elem in txbx_elem:
                                            if p_elem.tag == qn('w:p'):
                                                tb_para = Paragraph(p_elem, paragraph)
                                                extract_paragraph_with_merge(tb_para, local_texts, "textbox")
                                
                                # 处理 VML
                                namespaces = {**run.element.nsmap, 'v': 'urn:schemas-microsoft-com:vml'}
                                vtextbox_elem = run.element.find('.//v:textbox', namespaces)
                                if vtextbox_elem is not None:
                                    txbx_elem = vtextbox_elem.find('.//w:txbxContent', namespaces)
                                    if txbx_elem is not None:
                                        for p_elem in txbx_elem:
                                            if p_elem.tag == qn('w:p'):
                                                tb_para = Paragraph(p_elem, paragraph)
                                                extract_paragraph_with_merge(tb_para, local_texts, "textbox")
            
            # 线程安全地添加到主列表
            for text_item in local_texts:
                add_text_safe(text_item)
        
        # 使用线程池并行处理表格
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(process_table, table) 
                      for table in document.tables]
            for future in as_completed(futures):
                future.result()
    
    def process_sections_parallel():
        """并行处理页眉页脚（section之间无依赖）"""
        def process_section(section):
            local_texts = []
            
            # 处理页眉
            for paragraph in section.header.paragraphs:
                extract_paragraph_with_merge(paragraph, local_texts, "header")
                # 处理页眉中的超链接
                for hyperlink in paragraph.hyperlinks:
                    extract_hyperlink_with_merge(hyperlink, local_texts)
                # 处理页眉中的文本框
                for run in paragraph.runs:
                    if check_if_textbox(run):
                        # 处理 DrawingML
                        drawing_elem = run.element.find('.//w:drawing', run.element.nsmap)
                        if drawing_elem is not None:
                            txbx_elem = drawing_elem.find('.//w:txbxContent', drawing_elem.nsmap)
                            if txbx_elem is not None:
                                for p_elem in txbx_elem:
                                    if p_elem.tag == qn('w:p'):
                                        tb_para = Paragraph(p_elem, paragraph)
                                        extract_paragraph_with_merge(tb_para, local_texts, "textbox")
                        
                        # 处理 VML
                        namespaces = {**run.element.nsmap, 'v': 'urn:schemas-microsoft-com:vml'}
                        vtextbox_elem = run.element.find('.//v:textbox', namespaces)
                        if vtextbox_elem is not None:
                            txbx_elem = vtextbox_elem.find('.//w:txbxContent', namespaces)
                            if txbx_elem is not None:
                                for p_elem in txbx_elem:
                                    if p_elem.tag == qn('w:p'):
                                        tb_para = Paragraph(p_elem, paragraph)
                                        extract_paragraph_with_merge(tb_para, local_texts, "textbox")

            # 处理页脚
            for paragraph in section.footer.paragraphs:
                extract_paragraph_with_merge(paragraph, local_texts, "footer")
                # 处理页脚中的超链接
                for hyperlink in paragraph.hyperlinks:
                    extract_hyperlink_with_merge(hyperlink, local_texts)
                # 处理页脚中的文本框
                for run in paragraph.runs:
                    if check_if_textbox(run):
                        # 处理 DrawingML
                        drawing_elem = run.element.find('.//w:drawing', run.element.nsmap)
                        if drawing_elem is not None:
                            txbx_elem = drawing_elem.find('.//w:txbxContent', drawing_elem.nsmap)
                            if txbx_elem is not None:
                                for p_elem in txbx_elem:
                                    if p_elem.tag == qn('w:p'):
                                        tb_para = Paragraph(p_elem, paragraph)
                                        extract_paragraph_with_merge(tb_para, local_texts, "textbox")
                        
                        # 处理 VML
                        namespaces = {**run.element.nsmap, 'v': 'urn:schemas-microsoft-com:vml'}
                        vtextbox_elem = run.element.find('.//v:textbox', namespaces)
                        if vtextbox_elem is not None:
                            txbx_elem = vtextbox_elem.find('.//w:txbxContent', namespaces)
                            if txbx_elem is not None:
                                for p_elem in txbx_elem:
                                    if p_elem.tag == qn('w:p'):
                                        tb_para = Paragraph(p_elem, paragraph)
                                        extract_paragraph_with_merge(tb_para, local_texts, "textbox")
            
            # 线程安全地添加到主列表
            for text_item in local_texts:
                add_text_safe(text_item)
        
        # 使用线程池并行处理sections
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(process_section, section) 
                      for section in document.sections]
            for future in as_completed(futures):
                future.result()
    
    def process_inline_shapes_parallel():
        """并行处理内嵌形状（inline shapes）"""
        def process_shape(shape):
            local_texts = []
            try:
                if hasattr(shape, 'has_text_frame') and shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        extract_paragraph_with_merge(paragraph, local_texts, "textbox")
                        # 处理形状中的超链接
                        for hyperlink in paragraph.hyperlinks:
                            extract_hyperlink_with_merge(hyperlink, local_texts)
            except Exception as e:
                print(f"处理内嵌形状时出错: {str(e)}")
            
            # 线程安全地添加到主列表
            for text_item in local_texts:
                add_text_safe(text_item)
        
        # 使用线程池并行处理形状
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = [executor.submit(process_shape, shape) 
                       for shape in document.inline_shapes]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"内嵌形状线程异常: {str(e)}")
    
    # 按顺序执行各个部分，避免依赖问题
    print("开始安全的多线程文本提取...")
    
    # 1. 并行处理段落（分组处理，保持顺序）
    process_paragraphs_parallel()
    
    # 2. 并行处理表格（表格之间无依赖）
    if document.tables:
        process_tables_parallel()
    
    # 3. 并行处理页眉页脚（section之间无依赖）
    if document.sections:
        process_sections_parallel()
    
    # 4. 处理内嵌形状（inline shapes，可能包含文本框）
    if document.inline_shapes:
        process_inline_shapes_parallel()
    
    # 5. 批注内容（单线程，因为需要ZIP操作）
    if hasattr(document, 'comments') and document.comments:
        extract_comments(file_path, texts)
    
    print(f"文本提取完成，共提取 {len(texts)} 个文本项")


# 已删除单线程版本，统一使用多线程提取


def get_run_format_key(run):
    """获取run的格式标识，用于快速比较"""
    try:
        font_name = run.font.name if run.font.name else None
        font_size = run.font.size if run.font.size else None
        bold = run.bold
        italic = run.italic
        underline = run.underline
        color = run.font.color.rgb if run.font.color.rgb else None
        
        return (font_name, font_size, bold, italic, underline, color)
    except:
        return None

def are_runs_compatible(run1, run2):
    """检查两个run是否格式兼容（优化版本）"""
    try:
        # 使用格式标识进行快速比较
        key1 = get_run_format_key(run1)
        key2 = get_run_format_key(run2)
        
        if key1 is None or key2 is None:
            return False
        
        return key1 == key2
    except:
        return False


def conservative_run_merge(paragraph_runs, max_merge_length=1000):
    """保守的run合并策略"""
    
    merged = []
    current_group = []
    current_length = 0
    original_count = len([r for r in paragraph_runs if check_text(r.text)])
    merged_count = 0
    
    for run in paragraph_runs:
        # 跳过包含图片的run
        if check_if_image(run):
            # 保存当前组
            if current_group:
                merged.append(merge_compatible_runs(current_group))
                if len(current_group) > 1:
                    merged_count += len(current_group) - 1
                current_group = []
                current_length = 0
            
            # 图片run单独处理，但不添加到翻译列表
            continue
        
        if not check_text(run.text):
            continue
        
        # 只合并较短的run（通常是空格、标点、短词、短语）
        if len(run.text) <= 20 and current_length < max_merge_length:
            # 检查格式兼容性
            if not current_group or are_runs_compatible(current_group[-1], run):
                current_group.append(run)
                current_length += len(run.text)
                continue
        
        # 保存当前组
        if current_group:
            merged.append(merge_compatible_runs(current_group))
            if len(current_group) > 1:
                merged_count += len(current_group) - 1  # 记录合并的run数量
            current_group = []
            current_length = 0
        
        # 当前run单独处理
        merged.append({
            'text': run.text,
            'runs': [run],
            'type': 'single'
        })
    
    if current_group:
        merged.append(merge_compatible_runs(current_group))
        if len(current_group) > 1:
            merged_count += len(current_group) - 1
    
    # 打印合并统计信息
    if merged_count > 0:
        with print_lock:
            print(f"Run合并优化: 原始{original_count}个run -> 合并后{len(merged)}个，减少了{merged_count}个API调用")
    
    return merged


def merge_compatible_runs(run_group):
    """合并兼容的run组"""
    
    # 合并文本
    merged_text = "".join(run.text for run in run_group)
    
    return {
        'text': merged_text,
        'runs': run_group,
        'type': 'merged'
    }


def extract_paragraph_with_context(paragraph, texts, context_type):
    """为正文段落添加上下文，使用保守的run合并策略"""
    
    # 过滤掉超链接的run，避免重复处理
    paragraph_runs = []
    for run in paragraph.runs:
        # 检查run是否属于超链接
        is_hyperlink_run = False
        for hyperlink in paragraph.hyperlinks:
            if run in hyperlink.runs:
                is_hyperlink_run = True
                break
        
        if not is_hyperlink_run:
            paragraph_runs.append(run)
    
    # 使用保守的run合并策略
    merged_runs = conservative_run_merge(paragraph_runs)
    
    for i, merged_item in enumerate(merged_runs):
        if not check_text(merged_item['text']):
            continue
        
        # 检查是否包含图片，如果包含图片则跳过，避免在图片后添加空行
        has_image = False
        for run in merged_item['runs']:
            if check_if_image(run):
                has_image = True
                break
        
        if has_image:
            continue
        
        # 判断是否是段落边界
        is_start = i == 0
        is_end = i == len(merged_runs) - 1
        
        # 根据边界情况获取上下文
        if is_start:
            # 段落开头：只要后文
            context_before = ""
            context_after = get_context_after_merged(merged_runs, i, 2)
        elif is_end:
            # 段落结尾：只要前文
            context_before = get_context_before_merged(merged_runs, i, 2)
            context_after = ""
        else:
            # 正常情况：前后文都要
            context_before = get_context_before_merged(merged_runs, i, 2)
            context_after = get_context_after_merged(merged_runs, i, 2)
        
        # 构建带上下文的翻译文本
        context_parts = []
        if context_before:
            context_parts.append(f"[前文: {context_before}]")
        context_parts.append(merged_item['text'])
        if context_after:
            context_parts.append(f"[后文: {context_after}]")
        
        context_text = " ".join(context_parts)
        
        texts.append({
            "text": merged_item['text'],           # 原始文本
            "context_text": context_text,  # 带上下文的文本
            "type": "merged_run",
            "merged_item": merged_item,  # 包含runs列表
            "complete": False,
            "context_type": context_type,  # 标记为正文
            "is_boundary": is_start or is_end
        })


def get_context_before(runs, current_index, window_size):
    """获取前文上下文"""
    start_index = max(0, current_index - window_size)
    context_runs = runs[start_index:current_index]
    
    # 收集文本
    context_texts = []
    for run in context_runs:
        if check_text(run.text):
            context_texts.append(run.text)
    
    return ''.join(context_texts)


def get_context_after(runs, current_index, window_size):
    """获取后文上下文"""
    end_index = min(len(runs), current_index + window_size + 1)
    context_runs = runs[current_index + 1:end_index]
    
    # 收集文本
    context_texts = []
    for run in context_runs:
        if check_text(run.text):
            context_texts.append(run.text)
    
    return ''.join(context_texts)


def get_context_before_merged(merged_runs, current_index, window_size):
    """获取合并run的前文上下文"""
    start_index = max(0, current_index - window_size)
    context_items = merged_runs[start_index:current_index]
    
    # 收集文本
    context_texts = []
    for item in context_items:
        if check_text(item['text']):
            context_texts.append(item['text'])
    
    return ''.join(context_texts)


def get_context_after_merged(merged_runs, current_index, window_size):
    """获取合并run的后文上下文"""
    end_index = min(len(merged_runs), current_index + window_size + 1)
    context_items = merged_runs[current_index + 1:end_index]
    
    # 收集文本
    context_texts = []
    for item in context_items:
        if check_text(item['text']):
            context_texts.append(item['text'])
    
    return ''.join(context_texts)


def extract_comments(file_path, texts):
    """提取文档中的批注"""
    try:
        with zipfile.ZipFile(file_path, 'r') as docx:
            if 'word/comments.xml' in docx.namelist():
                with docx.open('word/comments.xml') as f:
                    tree = ET.parse(f)
                    root = tree.getroot()

                    # 定义命名空间
                    namespaces = {
                        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
                    }

                    # 查找所有批注
                    for comment in root.findall('.//w:comment', namespaces) or root.findall(
                            './/{*}comment'):
                        # 尝试不同方式获取ID
                        comment_id = None
                        for attr_name in [
                            '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id',
                            'id']:
                            if attr_name in comment.attrib:
                                comment_id = comment.attrib[attr_name]
                                break

                        if not comment_id:
                            continue

                        # 收集批注中的所有文本
                        text_elements = comment.findall('.//w:t', namespaces) or comment.findall(
                            './/{*}t')
                        for t_elem in text_elements:
                            if t_elem.text and check_text(t_elem.text):
                                texts.append({
                                    "text": t_elem.text,
                                    "type": "comment",
                                    "comment_id": comment_id,
                                    "complete": False,
                                    "original_text": t_elem.text  # 保存原始文本用于匹配
                                })
    except Exception as e:
        print(f"提取批注时出错: {str(e)}")


def run_translation(trans, texts, max_threads):
    """执行多线程翻译"""
    if not texts:
        print("没有需要翻译的内容")
        return

    event = threading.Event()
    
    with print_lock:
        print(f"开始翻译 {len(texts)} 个文本片段")
        print(f"翻译服务: {trans.get('server', 'unknown')}")  # 确认使用的翻译服务

    # 使用线程池执行翻译任务
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        # 提交所有翻译任务
        futures = []
        for i in range(len(texts)):
            future = executor.submit(to_translate.get, trans, event, texts, i)
            futures.append(future)
            with print_lock:
                print(f"提交翻译任务 {i}")
        
        # 等待所有任务完成
        for future in as_completed(futures):
            try:
                future.result()  # 获取结果，如果有异常会抛出
            except Exception as e:
                with print_lock:
                    print(f"翻译任务执行异常: {str(e)}")
                if not event.is_set():
                    event.set()  # 设置事件，通知其他线程停止

    with print_lock:
        print("所有翻译任务已完成")


def calculate_adaptive_font_size(original_text, translated_text, original_font_size):
    """根据翻译后文本长度计算自适应字体大小"""
    try:
        if not original_font_size:
            return None
        
        # 计算文本长度比例
        original_length = len(original_text.strip())
        translated_length = len(translated_text.strip())
        
        if original_length == 0:
            return original_font_size
        
        # 计算长度比例
        length_ratio = translated_length / original_length
        
        # 如果翻译后文本变长，适当缩小字体
        if length_ratio > 1.2:  # 文本长度增加超过20%
            # 根据长度比例计算新的字体大小，但不要小于原始大小的70%
            new_size = max(original_font_size * 0.7, original_font_size / length_ratio)
            return int(new_size)
        elif length_ratio < 0.8:  # 文本长度减少超过20%
            # 如果文本变短，可以适当增大字体，但不要超过原始大小的120%
            new_size = min(original_font_size * 1.2, original_font_size / length_ratio)
            return int(new_size)
        else:
            # 长度变化不大，保持原始字体大小
            return original_font_size
            
    except Exception as e:
        print(f"计算自适应字体大小失败: {str(e)}")
        return original_font_size


def calculate_adaptive_line_spacing(original_text, translated_text, original_line_spacing):
    """根据翻译后文本长度计算自适应行间距"""
    try:
        # 计算文本行数变化
        original_lines = len(original_text.split('\n'))
        translated_lines = len(translated_text.split('\n'))
        
        if original_lines == 0:
            return original_line_spacing
        
        # 计算行数比例
        line_ratio = translated_lines / original_lines
        
        # 如果行数增加，适当增加行间距
        if line_ratio > 1.1:  # 行数增加超过10%
            # 增加行间距，但不要超过原始行间距的150%
            new_spacing = min(original_line_spacing * 1.5, original_line_spacing * line_ratio)
            return new_spacing
        elif line_ratio < 0.9:  # 行数减少超过10%
            # 如果行数减少，可以适当减少行间距，但不要少于原始行间距的80%
            new_spacing = max(original_line_spacing * 0.8, original_line_spacing * line_ratio)
            return new_spacing
        else:
            # 行数变化不大，保持原始行间距
            return original_line_spacing
            
    except Exception as e:
        print(f"计算自适应行间距失败: {str(e)}")
        return original_line_spacing


def apply_adaptive_styles(run, original_text, translated_text, context_type=None):
    """应用自适应样式到run"""
    try:
        # 获取原始字体大小
        original_font_size = None
        if run.font.size:
            try:
                original_font_size = run.font.size.pt
            except:
                original_font_size = None
        
        # 计算自适应字体大小
        if original_font_size:
            adaptive_font_size = calculate_adaptive_font_size(original_text, translated_text, original_font_size)
            if adaptive_font_size and adaptive_font_size != original_font_size:
                # 如果是文本框，进一步缩小20%
                if context_type == 'textbox':
                    adaptive_font_size = int(adaptive_font_size * 0.8)
                from docx.shared import Pt
                run.font.size = Pt(adaptive_font_size)
                print(f"字体大小自适应: {original_font_size}pt -> {adaptive_font_size}pt")
            elif context_type == 'textbox':
                # 对于文本框，即使长度没变，也缩小20%
                adaptive_font_size = int(original_font_size * 0.8)
                from docx.shared import Pt
                run.font.size = Pt(adaptive_font_size)
                print(f"文本框字体固定缩小: {original_font_size}pt -> {adaptive_font_size}pt")
        
        # 获取段落对象并应用行间距自适应
        try:
            paragraph = run._element.getparent()
            if hasattr(paragraph, 'paragraph_format') and paragraph.paragraph_format:
                # 获取原始行间距
                original_line_spacing = paragraph.paragraph_format.line_spacing
                if original_line_spacing:
                    adaptive_line_spacing = calculate_adaptive_line_spacing(original_text, translated_text, original_line_spacing)
                    if adaptive_line_spacing and adaptive_line_spacing != original_line_spacing:
                        paragraph.paragraph_format.line_spacing = adaptive_line_spacing
                        print(f"行间距自适应: {original_line_spacing} -> {adaptive_line_spacing}")
        except Exception as e:
            print(f"应用行间距自适应失败: {str(e)}")
                
    except Exception as e:
        print(f"应用自适应样式失败: {str(e)}")


def apply_translations_with_adaptive_styles(document, texts):
    """应用翻译结果到文档，同时应用自适应样式"""
    text_count = 0

    for item in texts:
        if not item.get('complete', False):
            continue

        if item['type'] == 'run':
            # 检查run是否包含图片，如果包含则跳过
            if check_if_image(item['run']):
                continue
            
            # 获取原始文本和翻译后文本
            original_text = item['run'].text
            translated_text = item.get('text', original_text)
            
            # 应用翻译结果
            item['run'].text = translated_text
            
            # 应用自适应样式
            apply_adaptive_styles(item['run'], original_text, translated_text)
            
            text_count += 1
        elif item['type'] == 'merged_run':
            # 处理合并的run，需要将翻译结果分配回原始run
            merged_item = item['merged_item']
            translated_text = item.get('text', merged_item['text'])
            original_text = merged_item['text']
            
            # 检查是否包含图片，如果包含则跳过
            has_image = False
            for run in merged_item['runs']:
                if check_if_image(run):
                    has_image = True
                    break
            
            if has_image:
                continue
            
            if merged_item['type'] == 'merged':
                # 合并的run组，需要智能分配翻译结果
                distribute_translation_to_runs_with_adaptive_styles(merged_item['runs'], translated_text, original_text)
            else:
                # 单个run，直接替换
                run = merged_item['runs'][0]
                run.text = translated_text
                apply_adaptive_styles(run, original_text, translated_text)
            
            text_count += 1

    return text_count


def distribute_translation_to_runs_with_adaptive_styles(runs, translated_text, original_text):
    """将翻译结果智能分配回原始run，同时应用自适应样式"""
    
    # 如果只有一个run，直接替换
    if len(runs) == 1:
        runs[0].text = translated_text
        apply_adaptive_styles(runs[0], original_text, translated_text)
        return
    
    # 计算原始文本的总长度
    original_total_length = sum(len(run.text) for run in runs)
    
    # 如果翻译后文本长度变化不大，按比例分配
    if abs(len(translated_text) - original_total_length) <= 2:
        # 按原始比例分配
        current_pos = 0
        for run in runs:
            original_ratio = len(run.text) / original_total_length
            target_length = int(len(translated_text) * original_ratio)
            
            if current_pos < len(translated_text):
                end_pos = min(current_pos + target_length, len(translated_text))
                allocated_text = translated_text[current_pos:end_pos]
                run.text = allocated_text
                
                # 应用自适应样式
                apply_adaptive_styles(run, run.text, allocated_text)
                
                current_pos = end_pos
            else:
                run.text = ""
    else:
        # 长度变化较大，尝试按空格和标点分割
        words = translated_text.split()
        if len(words) >= len(runs):
            # 按run数量分配单词
            for i, run in enumerate(runs):
                if i < len(words):
                    allocated_text = words[i]
                    run.text = allocated_text
                    apply_adaptive_styles(run, run.text, allocated_text)
                else:
                    run.text = ""
        else:
            # 单词数量少于run数量，平均分配
            chars_per_run = len(translated_text) // len(runs)
            for i, run in enumerate(runs):
                start_pos = i * chars_per_run
                end_pos = start_pos + chars_per_run if i < len(runs) - 1 else len(translated_text)
                allocated_text = translated_text[start_pos:end_pos]
                run.text = allocated_text
                apply_adaptive_styles(run, run.text, allocated_text)


def update_special_elements(docx_path, texts):
    """更新批注等特殊元素"""
    # 筛选出需要处理的批注
    comment_texts = [t for t in texts if t.get('type') == 'comment' and t.get('complete')]
    if not comment_texts:
        return  # 没有需要处理的批注

    temp_path = f"temp_{os.path.basename(docx_path)}"

    try:
        with zipfile.ZipFile(docx_path, 'r') as zin, \
                zipfile.ZipFile(temp_path, 'w') as zout:

            for item in zin.infolist():
                with zin.open(item) as file:
                    if item.filename == 'word/comments.xml':
                        try:
                            tree = ET.parse(file)
                            root = tree.getroot()

                            # 定义命名空间
                            namespaces = {
                                'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
                            }

                            # 查找所有批注
                            for comment in root.findall('.//w:comment', namespaces) or root.findall(
                                    './/{*}comment'):
                                # 尝试不同方式获取ID
                                comment_id = None
                                for attr_name in [
                                    '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}id',
                                    'id']:
                                    if attr_name in comment.attrib:
                                        comment_id = comment.attrib[attr_name]
                                        break

                                if not comment_id:
                                    continue

                                # 查找匹配的翻译结果
                                matching_texts = [t for t in comment_texts if
                                                  t.get('comment_id') == comment_id]
                                if not matching_texts:
                                    continue

                                # 更新批注文本
                                text_elements = comment.findall('.//w:t',
                                                                namespaces) or comment.findall(
                                    './/{*}t')
                                for i, t_elem in enumerate(text_elements):
                                    if i < len(matching_texts):
                                        # 找到匹配的原始文本
                                        for match in matching_texts:
                                            if match.get('original_text') == t_elem.text:
                                                t_elem.text = match.get('text', t_elem.text)
                                                break

                            # 写入修改后的XML
                            modified_xml = ET.tostring(root, encoding='utf-8', xml_declaration=True)
                            zout.writestr(item.filename, modified_xml)
                        except Exception as e:
                            print(f"处理批注时出错: {str(e)}")
                            # 如果解析失败，直接复制原文件
                            file.seek(0)
                            zout.writestr(item.filename, file.read())
                    else:
                        # 直接复制其他文件
                        file.seek(0)
                        zout.writestr(item.filename, file.read())

        # 替换原始文件
        os.replace(temp_path, docx_path)
    except Exception as e:
        print(f"更新批注时出错: {str(e)}")
        # 确保临时文件被删除
        if os.path.exists(temp_path):
            os.remove(temp_path)



def check_text(text):
    """检查文本是否有效（非空且非纯标点）- 优化版本"""
    if not text or len(text) == 0:
        return False
    
    # 快速检查：如果第一个字符是字母或数字，很可能需要翻译
    if text[0].isalnum():
        return True
    
    # 快速检查：如果全是空格，不需要翻译
    if text.isspace():
        return False
    
    # 快速检查：如果长度很短且全是标点，不需要翻译
    if len(text) <= 3 and all(not c.isalnum() for c in text):
        return False
    
    # 最后检查：使用正则表达式
    if SPECIAL_SYMBOLS_PATTERN.match(text):
        return False
    
    if NUMBERS_PATTERN.match(text):
        return False
    
    return not common.is_all_punc(text)


def apply_translations(document, texts):
    """应用翻译结果到文档，完全保留原始格式"""
    text_count = 0

    for item in texts:
        if not item.get('complete', False):
            continue

        if item['type'] == 'run':
            # 检查run是否包含图片，如果包含则跳过
            if check_if_image(item['run']):
                continue
            # 直接替换run文本，保留所有格式
            item['run'].text = item.get('text', item['run'].text)
            # 如果是文本框，应用自适应样式
            if item.get('context_type') == 'textbox':
                original_text = item['run'].text  # 注意：这里 original_text 应该是替换前的，但由于已替换，使用 item['text'] 作为 translated
                translated_text = item['run'].text
                apply_adaptive_styles(item['run'], original_text, translated_text, context_type='textbox')
            text_count += 1
        elif item['type'] == 'merged_run':
            # 处理合并的run，需要将翻译结果分配回原始run
            merged_item = item['merged_item']
            translated_text = item.get('text', merged_item['text'])
            
            # 如果是目录文本，附加原页码
            if item.get('is_toc_text'):
                translated_text += item['original_page_num']
            
            # 检查是否包含图片，如果包含则跳过
            has_image = False
            for run in merged_item['runs']:
                if check_if_image(run):
                    has_image = True
                    break
            
            if has_image:
                continue
            
            if merged_item['type'] == 'merged':
                # 合并的run组，需要智能分配翻译结果
                distribute_translation_to_runs(merged_item['runs'], translated_text)
            else:
                # 单个run，直接替换
                merged_item['runs'][0].text = translated_text
            
            # 如果是文本框，应用自适应样式到每个run
            if item.get('context_type') == 'textbox':
                original_text = merged_item['text']  # 原始合并文本
                # 对于每个run，应用自适应（简化：对第一个run应用整体调整）
                for run in merged_item['runs']:
                    apply_adaptive_styles(run, original_text, translated_text, context_type='textbox')
            
            text_count += 1

    return text_count


def distribute_translation_to_runs(runs, translated_text):
    """将翻译结果智能分配回原始run，保持格式"""
    
    # 如果只有一个run，直接替换
    if len(runs) == 1:
        runs[0].text = translated_text
        return
    
    # 计算原始文本的总长度
    original_total_length = sum(len(run.text) for run in runs)
    
    # 如果翻译后文本长度变化不大，按比例分配
    if abs(len(translated_text) - original_total_length) <= 2:
        # 按原始比例分配
        current_pos = 0
        for run in runs:
            original_ratio = len(run.text) / original_total_length
            target_length = int(len(translated_text) * original_ratio)
            
            if current_pos < len(translated_text):
                end_pos = min(current_pos + target_length, len(translated_text))
                run.text = translated_text[current_pos:end_pos]
                current_pos = end_pos
            else:
                run.text = ""
    else:
        # 长度变化较大，尝试按空格和标点分割
        words = translated_text.split()
        if len(words) >= len(runs):
            # 按run数量分配单词
            for i, run in enumerate(runs):
                if i < len(words):
                    run.text = words[i]
                else:
                    run.text = ""
        else:
            # 单词数量少于run数量，平均分配
            chars_per_run = len(translated_text) // len(runs)
            for i, run in enumerate(runs):
                start_pos = i * chars_per_run
                end_pos = start_pos + chars_per_run if i < len(runs) - 1 else len(translated_text)
                run.text = translated_text[start_pos:end_pos]
