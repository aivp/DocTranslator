import threading
import pptx
from . import to_translate
from . import common
import os
import sys
import time
import datetime

def start(trans):
    # 允许的最大线程
    threads=trans['threads']
    if threads is None or int(threads)<0:
        max_threads=10
    else:
        max_threads=int(threads)
    # 当前执行的索引位置
    run_index=0
    start_time = datetime.datetime.now()
    wb = pptx.Presentation(trans['file_path']) 
    print(trans['file_path'])
    slides = wb.slides
    texts=[]
    
    # 提取文本时保存样式信息
    for slide in slides:
        for shape in slide.shapes:
            if shape.has_table:
                table = shape.table
                print(table)
                rows = len(table.rows)
                cols = len(table.columns)
                for r in range(rows):
                    row_data = []
                    for c in range(cols):
                        cell_text = table.cell(r, c).text
                        if cell_text!=None and len(cell_text)>0 and not common.is_all_punc(cell_text):
                            # 保存表格单元格的样式信息
                            cell = table.cell(r, c)
                            style_info = extract_cell_style(cell)
                            texts.append({
                                "text": cell_text,
                                "row": r,
                                "column": c, 
                                "complete": False,
                                "type": "table_cell",
                                "style_info": style_info
                            })
            if not shape.has_text_frame:
                continue
            text_frame = shape.text_frame
            for paragraph in text_frame.paragraphs:
                text=paragraph.text
                if text!=None and len(text)>0 and not common.is_all_punc(text):
                    # 保存段落的样式信息
                    style_info = extract_paragraph_style(paragraph)
                    texts.append({
                        "text": text, 
                        "complete": False,
                        "type": "paragraph",
                        "style_info": style_info,
                        "paragraph": paragraph
                    })
    
    max_run=max_threads if len(texts)>max_threads else len(texts)
    before_active_count=threading.activeCount()
    event=threading.Event()
    while run_index<=len(texts)-1:
        if threading.activeCount()<max_run+before_active_count:
            if not event.is_set():
                thread = threading.Thread(target=to_translate.get,args=(trans,event,texts,run_index))
                thread.start()
                run_index+=1
            else:
                return False
    
    while True:
        complete=True
        for text in texts:
            if not text['complete']:
                complete=False
        if complete:
            break
        else:
            time.sleep(1)

    text_count=0
    for slide in slides:
        for shape in slide.shapes:
            if shape.has_table:
                table = shape.table
                rows = len(table.rows)
                cols = len(table.columns)
                for r in range(rows):
                    row_data = []
                    for c in range(cols):
                        cell_text = table.cell(r, c).text
                        if cell_text!=None and len(cell_text)>0 and not common.is_all_punc(cell_text):
                            item=texts.pop(0)
                            cell = table.cell(r, c)
                            # 检查是否启用自适应样式
                            use_adaptive_styles = trans.get('adaptive_styles', False)  # 默认不启用
                            if use_adaptive_styles:
                                # 应用翻译结果并恢复样式，同时应用自适应样式
                                apply_translation_to_cell_with_adaptive_styles(cell, item['text'], item.get('style_info', {}))
                            else:
                                # 应用翻译结果并恢复样式（原始版本）
                                apply_translation_to_cell(cell, item['text'], item.get('style_info', {}))
                            text_count+=item.get('count', 1)
                          
            if not shape.has_text_frame:
                continue
            text_frame = shape.text_frame
            for paragraph in text_frame.paragraphs:
                text=paragraph.text
                if text!=None and len(text)>0 and not common.is_all_punc(text) and len(texts)>0:
                    item=texts.pop(0)
                    # 检查是否启用自适应样式
                    use_adaptive_styles = trans.get('adaptive_styles', False)  # 默认不启用
                    if use_adaptive_styles:
                        # 应用翻译结果并恢复样式，同时应用自适应样式
                        apply_translation_to_paragraph_with_adaptive_styles(paragraph, item['text'], item.get('style_info', {}))
                    else:
                        # 应用翻译结果并恢复样式（原始版本）
                        apply_translation_to_paragraph(paragraph, item['text'], item.get('style_info', {}))
                    text_count+=item.get('count', 1)

    wb.save(trans['target_file'])
    end_time = datetime.datetime.now()
    spend_time=common.display_spend(start_time, end_time)
    to_translate.complete(trans,text_count,spend_time)
    return True

def extract_paragraph_style(paragraph):
    """提取段落的样式信息"""
    style_info = {
        'paragraph_level': {},
        'runs': []
    }
    
    try:
        # 段落级别的样式
        if paragraph.alignment:
            style_info['paragraph_level']['alignment'] = paragraph.alignment
        if paragraph.level:
            style_info['paragraph_level']['level'] = paragraph.level
        
        # 每个run的样式
        for run in paragraph.runs:
            run_style = {}
            
            try:
                # 字体样式
                if run.font.name:
                    run_style['font_name'] = run.font.name
                if run.font.size:
                    run_style['font_size'] = run.font.size
                if run.font.bold is not None:
                    run_style['bold'] = run.font.bold
                if run.font.italic is not None:
                    run_style['italic'] = run.font.italic
                if run.font.underline is not None:
                    run_style['underline'] = run.font.underline
                
                # 颜色处理 - 简化版本，只保存颜色对象
                if run.font.color:
                    # 直接保存颜色对象，避免类型检查错误
                    run_style['color_object'] = run.font.color
                        
            except Exception as e:
                # 如果获取样式失败，继续处理下一个run
                print(f"提取run样式失败: {str(e)}")
                continue
            
            style_info['runs'].append({
                'text': run.text,
                'style': run_style
            })
    except Exception as e:
        # 如果提取段落样式失败，返回空的样式信息
        print(f"提取段落样式失败: {str(e)}")
    
    return style_info

def extract_cell_style(cell):
    """提取表格单元格的样式信息"""
    style_info = {
        'paragraphs': []
    }
    
    for paragraph in cell.text_frame.paragraphs:
        para_style = extract_paragraph_style(paragraph)
        style_info['paragraphs'].append(para_style)
    
    return style_info

def apply_translation_to_paragraph(paragraph, translated_text, style_info):
    """应用翻译结果到段落并恢复样式（原始版本）"""
    # 清空段落内容
    paragraph.clear()
    
    # 如果有样式信息，按run恢复样式
    if style_info and 'runs' in style_info and style_info['runs']:
        # 按原始run的样式分配翻译文本
        distribute_text_to_runs(paragraph, translated_text, style_info['runs'])
    else:
        # 没有样式信息，直接添加文本
        paragraph.text = translated_text
    
    # 恢复段落级别的样式
    if style_info and 'paragraph_level' in style_info:
        para_level = style_info['paragraph_level']
        if 'alignment' in para_level:
            paragraph.alignment = para_level['alignment']
        if 'level' in para_level:
            paragraph.level = para_level['level']


def apply_translation_to_cell(cell, translated_text, style_info):
    """应用翻译结果到表格单元格并恢复样式（原始版本）"""
    # 清空单元格内容
    cell.text = ""
    
    # 如果有样式信息，按段落恢复样式
    if style_info and 'paragraphs' in style_info and style_info['paragraphs']:
        # 按原始段落的样式分配翻译文本
        distribute_text_to_paragraphs(cell.text_frame, translated_text, style_info['paragraphs'])
    else:
        # 没有样式信息，直接添加文本
        cell.text = translated_text


def apply_translation_to_paragraph_with_adaptive_styles(paragraph, translated_text, style_info):
    """应用翻译结果到段落并恢复样式，同时应用自适应样式"""
    # 保存原始文本用于自适应计算
    original_text = paragraph.text
    
    # 清空段落内容
    paragraph.clear()
    
    # 如果有样式信息，按run恢复样式
    if style_info and 'runs' in style_info and style_info['runs']:
        # 按原始run的样式分配翻译文本
        distribute_text_to_runs_with_adaptive_styles(paragraph, translated_text, style_info['runs'], original_text)
    else:
        # 没有样式信息，直接添加文本
        paragraph.text = translated_text
        # 应用自适应样式到整个段落
        if paragraph.runs:
            apply_adaptive_styles_ppt(paragraph.runs[0], original_text, translated_text)
    
    # 恢复段落级别的样式
    if style_info and 'paragraph_level' in style_info:
        para_level = style_info['paragraph_level']
        if 'alignment' in para_level:
            paragraph.alignment = para_level['alignment']
        if 'level' in para_level:
            paragraph.level = para_level['level']


def apply_translation_to_cell_with_adaptive_styles(cell, translated_text, style_info):
    """应用翻译结果到表格单元格并恢复样式，同时应用自适应样式"""
    # 保存原始文本用于自适应计算
    original_text = cell.text
    
    # 清空单元格内容
    cell.text = ""
    
    # 如果有样式信息，按段落恢复样式
    if style_info and 'paragraphs' in style_info and style_info['paragraphs']:
        # 按原始段落的样式分配翻译文本
        distribute_text_to_paragraphs_with_adaptive_styles(cell.text_frame, translated_text, style_info['paragraphs'], original_text)
    else:
        # 没有样式信息，直接添加文本
        cell.text = translated_text
        # 应用自适应样式到单元格中的段落
        if cell.text_frame.paragraphs:
            for paragraph in cell.text_frame.paragraphs:
                if paragraph.runs:
                    apply_adaptive_styles_ppt(paragraph.runs[0], original_text, translated_text)


def distribute_text_to_runs_with_adaptive_styles(paragraph, translated_text, run_styles, original_text):
    """将翻译文本按原始run的样式分配到新的run中，同时应用自适应样式"""
    if not run_styles:
        paragraph.text = translated_text
        # 应用自适应样式
        if paragraph.runs:
            apply_adaptive_styles_ppt(paragraph.runs[0], original_text, translated_text)
        return
    
    # 计算每个run应该分配的文本长度
    total_original_length = sum(len(run['text']) for run in run_styles)
    if total_original_length == 0:
        paragraph.text = translated_text
        # 应用自适应样式
        if paragraph.runs:
            apply_adaptive_styles_ppt(paragraph.runs[0], original_text, translated_text)
        return
    
    # 按比例分配翻译文本
    current_pos = 0
    for i, run_style in enumerate(run_styles):
        original_length = len(run_style['text'])
        if original_length == 0:
            continue
        
        # 计算这个run应该分配的文本长度
        if i == len(run_styles) - 1:
            # 最后一个run，分配剩余的所有文本
            allocated_text = translated_text[current_pos:]
        else:
            # 按比例分配
            ratio = original_length / total_original_length
            allocated_length = max(1, int(len(translated_text) * ratio))
            # 确保不超过剩余文本长度
            remaining_length = len(translated_text) - current_pos
            allocated_length = min(allocated_length, remaining_length)
            allocated_text = translated_text[current_pos:current_pos + allocated_length]
            current_pos += allocated_length
        
        if allocated_text:
            # 创建新的run并应用样式
            run = paragraph.add_run()
            run.text = allocated_text
            apply_run_style(run, run_style['style'])
            # 应用自适应样式
            apply_adaptive_styles_ppt(run, run_style['text'], allocated_text)


def distribute_text_to_paragraphs_with_adaptive_styles(text_frame, translated_text, paragraph_styles, original_text):
    """将翻译文本按原始段落的样式分配到新的段落中，同时应用自适应样式"""
    if not paragraph_styles:
        text_frame.text = translated_text
        # 应用自适应样式
        if text_frame.paragraphs:
            for paragraph in text_frame.paragraphs:
                if paragraph.runs:
                    apply_adaptive_styles_ppt(paragraph.runs[0], original_text, translated_text)
        return
    
    # 清空文本框架
    text_frame.clear()
    
    # 按段落分配文本
    total_original_length = sum(len(run['text']) for para in paragraph_styles for run in para['runs'])
    if total_original_length == 0:
        text_frame.text = translated_text
        # 应用自适应样式
        if text_frame.paragraphs:
            for paragraph in text_frame.paragraphs:
                if paragraph.runs:
                    apply_adaptive_styles_ppt(paragraph.runs[0], original_text, translated_text)
        return
    
    current_pos = 0
    for i, para_style in enumerate(paragraph_styles):
        if i > 0:
            # 添加段落分隔符
            text_frame.add_paragraph()
        
        paragraph = text_frame.paragraphs[-1] if text_frame.paragraphs else text_frame.add_paragraph()
        
        # 计算这个段落应该分配的文本长度
        para_original_length = sum(len(run['text']) for run in para_style['runs'])
        if para_original_length == 0:
            continue
        
        if i == len(paragraph_styles) - 1:
            # 最后一个段落，分配剩余的所有文本
            allocated_text = translated_text[current_pos:]
        else:
            # 按比例分配
            ratio = para_original_length / total_original_length
            allocated_length = max(1, int(len(translated_text) * ratio))
            # 确保不超过剩余文本长度
            remaining_length = len(translated_text) - current_pos
            allocated_length = min(allocated_length, remaining_length)
            allocated_text = translated_text[current_pos:current_pos + allocated_length]
            current_pos += allocated_length
        
        if allocated_text:
            # 按run分配文本并应用样式
            if para_style['runs']:
                distribute_text_to_runs_with_adaptive_styles(paragraph, allocated_text, para_style['runs'], allocated_text)
            else:
                paragraph.text = allocated_text
                # 应用自适应样式
                if paragraph.runs:
                    apply_adaptive_styles_ppt(paragraph.runs[0], allocated_text, allocated_text)

def apply_run_style(run, style):
    """应用run的样式"""
    if not style:
        return
    
    try:
        # 字体名称
        if 'font_name' in style:
            run.font.name = style['font_name']
        
        # 字体大小
        if 'font_size' in style:
            run.font.size = style['font_size']
        
        # 粗体
        if 'bold' in style:
            run.font.bold = style['bold']
        
        # 斜体
        if 'italic' in style:
            run.font.italic = style['italic']
        
        # 下划线
        if 'underline' in style:
            run.font.underline = style['underline']
        
        # 颜色处理 - 简化版本
        if 'color_object' in style:
            try:
                color_object = style['color_object']
                # 尝试复制颜色属性
                if hasattr(color_object, 'rgb') and color_object.rgb:
                    run.font.color.rgb = color_object.rgb
                elif hasattr(color_object, 'theme_color') and color_object.theme_color:
                    run.font.color.theme_color = color_object.theme_color
                elif hasattr(color_object, 'color_index') and color_object.color_index:
                    run.font.color.color_index = color_object.color_index
                elif hasattr(color_object, 'srgbClr') and color_object.srgbClr:
                    run.font.color.srgbClr = color_object.srgbClr
                # 其他颜色类型暂时跳过，避免错误
            except Exception as e:
                print(f"应用颜色样式失败: {str(e)}")
                pass  # 如果颜色设置失败，跳过颜色设置
    except Exception as e:
        # 如果应用样式失败，记录错误但继续处理
        print(f"应用run样式失败: {str(e)}")


def calculate_adaptive_font_size_ppt(original_text, translated_text, original_font_size):
    """根据翻译后文本长度计算PPT自适应字体大小"""
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
        if length_ratio > 1.3:  # 文本长度增加超过30%
            # 根据长度比例计算新的字体大小，但不要小于原始大小的60%
            new_size = max(original_font_size * 0.6, original_font_size / length_ratio)
            return int(new_size)
        elif length_ratio < 0.7:  # 文本长度减少超过30%
            # 如果文本变短，可以适当增大字体，但不要超过原始大小的130%
            new_size = min(original_font_size * 1.3, original_font_size / length_ratio)
            return int(new_size)
        else:
            # 长度变化不大，保持原始字体大小
            return original_font_size
            
    except Exception as e:
        print(f"计算PPT自适应字体大小失败: {str(e)}")
        return original_font_size


def apply_adaptive_styles_ppt(run, original_text, translated_text):
    """应用自适应样式到PPT run"""
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
            adaptive_font_size = calculate_adaptive_font_size_ppt(original_text, translated_text, original_font_size)
            if adaptive_font_size and adaptive_font_size != original_font_size:
                from pptx.util import Pt
                run.font.size = Pt(adaptive_font_size)
                print(f"PPT字体大小自适应: {original_font_size}pt -> {adaptive_font_size}pt")
                    
    except Exception as e:
        print(f"应用PPT自适应样式失败: {str(e)}")


def distribute_text_to_runs(paragraph, translated_text, run_styles):
    """将翻译文本按原始run的样式分配到新的run中（原始版本）"""
    if not run_styles:
        paragraph.text = translated_text
        return
    
    # 计算每个run应该分配的文本长度
    total_original_length = sum(len(run['text']) for run in run_styles)
    if total_original_length == 0:
        paragraph.text = translated_text
        return
    
    # 按比例分配翻译文本
    current_pos = 0
    for i, run_style in enumerate(run_styles):
        original_length = len(run_style['text'])
        if original_length == 0:
            continue
        
        # 计算这个run应该分配的文本长度
        if i == len(run_styles) - 1:
            # 最后一个run，分配剩余的所有文本
            allocated_text = translated_text[current_pos:]
        else:
            # 按比例分配
            ratio = original_length / total_original_length
            allocated_length = max(1, int(len(translated_text) * ratio))
            # 确保不超过剩余文本长度
            remaining_length = len(translated_text) - current_pos
            allocated_length = min(allocated_length, remaining_length)
            allocated_text = translated_text[current_pos:current_pos + allocated_length]
            current_pos += allocated_length
        
        if allocated_text:
            # 创建新的run并应用样式
            run = paragraph.add_run()
            run.text = allocated_text
            apply_run_style(run, run_style['style'])


def distribute_text_to_paragraphs(text_frame, translated_text, paragraph_styles):
    """将翻译文本按原始段落的样式分配到新的段落中（原始版本）"""
    if not paragraph_styles:
        text_frame.text = translated_text
        return
    
    # 清空文本框架
    text_frame.clear()
    
    # 按段落分配文本
    total_original_length = sum(len(run['text']) for para in paragraph_styles for run in para['runs'])
    if total_original_length == 0:
        text_frame.text = translated_text
        return
    
    current_pos = 0
    for i, para_style in enumerate(paragraph_styles):
        if i > 0:
            # 添加段落分隔符
            text_frame.add_paragraph()
        
        paragraph = text_frame.paragraphs[-1] if text_frame.paragraphs else text_frame.add_paragraph()
        
        # 计算这个段落应该分配的文本长度
        para_original_length = sum(len(run['text']) for run in para_style['runs'])
        if para_original_length == 0:
            continue
        
        if i == len(paragraph_styles) - 1:
            # 最后一个段落，分配剩余的所有文本
            allocated_text = translated_text[current_pos:]
        else:
            # 按比例分配
            ratio = para_original_length / total_original_length
            allocated_length = max(1, int(len(translated_text) * ratio))
            # 确保不超过剩余文本长度
            remaining_length = len(translated_text) - current_pos
            allocated_length = min(allocated_length, remaining_length)
            allocated_text = translated_text[current_pos:current_pos + allocated_length]
            current_pos += allocated_length
        
        if allocated_text:
            # 按run分配文本
            distribute_text_to_runs(paragraph, allocated_text, para_style['runs'])
            
            # 恢复段落级别的样式
            if 'paragraph_level' in para_style:
                para_level = para_style['paragraph_level']
                if 'alignment' in para_level:
                    paragraph.alignment = para_level['alignment']
                if 'level' in para_level:
                    paragraph.level = para_level['level']


