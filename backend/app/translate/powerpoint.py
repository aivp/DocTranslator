import threading
import pptx
from . import to_translate
from . import common
import os
import sys
import time
import logging
from datetime import datetime

# 配置日志
logger = logging.getLogger(__name__)

def start(trans):
    # 允许的最大线程
    threads=trans['threads']
    if threads is None or int(threads)<0:
        max_threads=10
    else:
        max_threads=int(threads)
    # 当前执行的索引位置
    run_index=0
    start_time = datetime.now()
    wb = pptx.Presentation(trans['file_path']) 
    logger.info(f"处理文件: {trans['file_path']}")
    slides = wb.slides
    texts=[]
    
    # 提取文本时保存样式信息
    slide_count = 0
    for slide in slides:
        slide_count += 1
        slide_text_count = 0
        logger.info(f"正在处理第 {slide_count} 页幻灯片...")
        
        # 第三页特殊调试
        if slide_count == 3:
            # logger.info("🔍 第三页特殊调试模式启动")
            # logger.info(f"第三页形状总数: {len(slide.shapes)}")
            pass
        
        for shape in slide.shapes:
            # 第三页特殊调试
            if slide_count == 3:
                # logger.info(f"🔍 第三页形状详情:")
                # logger.info(f"  形状类型: {type(shape).__name__}")
                # logger.info(f"  形状名称: {getattr(shape, 'name', 'N/A')}")
                # logger.info(f"  是否有表格: {shape.has_table}")
                # logger.info(f"  是否有文本框架: {shape.has_text_frame}")
                # logger.info(f"  是否有文本属性: {hasattr(shape, 'text')}")
                # if hasattr(shape, 'text'):
                #     logger.info(f"  文本内容: '{getattr(shape, 'text', '')[:50]}...'")
                # if hasattr(shape, 'text_frame') and shape.text_frame:
                #     logger.info(f"  文本框架段落数: {len(shape.text_frame.paragraphs)}")
                #     for i, para in enumerate(shape.text_frame.paragraphs):
                #         logger.info(f"    段落{i+1}: '{para.text[:50]}...'")
                pass
            
            # 处理表格
            if shape.has_table:
                table = shape.table
                logger.info(f"发现表格: {table}")
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
                            slide_text_count += 1
            
            # 处理所有有文本框架的形状（包括文本框、标题、占位符等）
            if shape.has_text_frame:
                text_frame = shape.text_frame
                # logger.info(f"发现文本框架，段落数: {len(text_frame.paragraphs)}")
                for paragraph in text_frame.paragraphs:
                    text=paragraph.text
                    # logger.info(f"段落文本: '{text[:50]}...' (长度: {len(text)})")
                    if text!=None and len(text)>0 and not common.is_all_punc(text):
                        # 保存段落的样式信息
                        style_info = extract_paragraph_style(paragraph)
                        # logger.info(f"提取段落样式: runs数={len(style_info.get('runs', []))}")
                        texts.append({
                            "text": text, 
                            "complete": False,
                            "type": "paragraph",
                            "style_info": style_info,
                            "paragraph": paragraph
                        })
                        slide_text_count += 1
                        # logger.info(f"已添加段落文本: '{text[:30]}...'")
                    else:
                        # logger.info(f"跳过段落文本: '{text[:30]}...' (原因: 空文本或纯标点)")
                        pass
                
                # 额外检查：处理可能遗漏的文本框架内容
                if text_frame.text and text_frame.text.strip():
                    # 检查是否有文本但没有被段落处理
                    frame_text = text_frame.text.strip()
                    # 更严格的重复检查：检查是否与任何已提取的文本重复
                    is_duplicate = False
                    for item in texts:
                        if item['text'].strip() == frame_text:
                            is_duplicate = True
                            # logger.info(f"跳过重复的文本框架内容: {frame_text[:50]}...")
                            break
                    
                    if not is_duplicate:
                        # logger.info(f"发现遗漏的文本框架内容: {frame_text[:50]}...")
                        texts.append({
                            "text": frame_text,
                            "complete": False,
                            "type": "text_frame",
                            "text_frame": text_frame
                        })
                        slide_text_count += 1
            
            # 处理其他可能有文本的形状（如形状内的文本）
            elif hasattr(shape, 'text') and shape.text:
                text = shape.text
                if text!=None and len(text)>0 and not common.is_all_punc(text):
                    texts.append({
                        "text": text, 
                        "complete": False,
                        "type": "shape_text",
                        "shape": shape
                    })
                    slide_text_count += 1
            
            # 处理可能遗漏的文本类型
            elif hasattr(shape, 'text_frame') and shape.text_frame:
                # 检查是否有文本框架但没有被has_text_frame识别
                text_frame = shape.text_frame
                if text_frame.text and text_frame.text.strip():
                    # logger.info(f"处理遗漏的文本框架: {text_frame.text[:50]}...")
                    for paragraph in text_frame.paragraphs:
                        text = paragraph.text
                        if text and len(text.strip()) > 0 and not common.is_all_punc(text):
                            style_info = extract_paragraph_style(paragraph)
                            texts.append({
                                "text": text,
                                "complete": False,
                                "type": "paragraph",
                                "style_info": style_info,
                                "paragraph": paragraph
                            })
                            slide_text_count += 1
            
            # 处理其他可能的文本类型
            elif hasattr(shape, 'name') and shape.name:
                # 检查形状名称是否包含文本
                shape_name = shape.name
                if shape_name and len(shape_name.strip()) > 0:
                    # logger.info(f"发现形状名称文本: {shape_name}")
                    texts.append({
                        "text": shape_name,
                        "complete": False,
                        "type": "shape_name",
                        "shape": shape
                    })
                    slide_text_count += 1
            
            # 额外检查：处理可能遗漏的占位符文本
            try:
                if hasattr(shape, 'placeholder_format') and shape.placeholder_format:
                    placeholder_type = shape.placeholder_format.type
                    # logger.info(f"发现占位符类型: {placeholder_type}")
                    # 检查占位符是否有文本内容
                    if hasattr(shape, 'text_frame') and shape.text_frame:
                        placeholder_text = shape.text_frame.text.strip()
                        if placeholder_text and not any(item['text'] == placeholder_text for item in texts[-slide_text_count:]):
                            # logger.info(f"发现占位符文本: {placeholder_text[:50]}...")
                            texts.append({
                                "text": placeholder_text,
                                "complete": False,
                                "type": "placeholder",
                                "shape": shape
                            })
                            slide_text_count += 1
            except ValueError as e:
                # 忽略"shape is not a placeholder"错误
                pass
            except Exception as e:
                logger.warning(f"处理占位符时出错: {str(e)}")
        
        # 记录提取的文本数量
        # logger.info(f"第 {slide_count} 页幻灯片提取了 {slide_text_count} 个文本元素")
        
        # 记录总文本数量
        # logger.info(f"总共提取了 {len(texts)} 个文本元素")
    
    # 额外检查：确保没有遗漏任何文本
    # logger.info(f"总共提取了 {len(texts)} 个文本元素")
    
    # 调试：打印所有提取的文本类型
    # logger.info(f"提取的文本类型分布: {text_types}")
    max_run=max_threads if len(texts)>max_threads else len(texts)
    before_active_count=threading.activeCount()
    event=threading.Event()
    
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
            logger.info(f"翻译进度: {completed_count}/{total_count} ({progress_percentage:.1f}%)")
            
            # 更新数据库进度
            try:
                from .to_translate import db
                db.execute("update translate set process=%s where id=%s", 
                         str(format(progress_percentage, '.1f')), 
                         trans['id'])
                
                # 如果进度达到100%，立即更新状态为已完成
                if progress_percentage >= 100.0:
                    import pytz
                    end_time = datetime.now(pytz.timezone('Asia/Shanghai'))
                    db.execute(
                        "update translate set status='done',end_at=%s,process=100 where id=%s",
                        end_time, trans['id']
                    )
                    print("✅ 翻译完成，状态已更新为已完成")
                    
            except Exception as e:
                print(f"更新进度失败: {str(e)}")
    
    while run_index<=len(texts)-1:
        if threading.activeCount()<max_run+before_active_count:
            if not event.is_set():
                thread = threading.Thread(target=to_translate.get,args=(trans,event,texts,run_index))
                thread.start()
                run_index+=1
            else:
                return False
    
    # 等待翻译完成，并监控进度
    last_completed_count = 0
    while True:
        complete=True
        current_completed = 0
        for text in texts:
            if not text['complete']:
                complete=False
            else:
                current_completed += 1
        
        # 检查是否有新的文本完成
        if current_completed > last_completed_count:
            completed_count = current_completed
            progress_percentage = min((completed_count / total_count) * 100, 100.0)
            logger.info(f"翻译进度: {completed_count}/{total_count} ({progress_percentage:.1f}%)")
            
            # 更新数据库进度
            try:
                from .to_translate import db
                db.execute("update translate set process=%s where id=%s", 
                         str(format(progress_percentage, '.1f')), 
                         trans['id'])
                
                # 如果进度达到100%，立即更新状态为已完成
                if progress_percentage >= 100.0:
                    import pytz
                    end_time = datetime.now(pytz.timezone('Asia/Shanghai'))
                    db.execute(
                        "update translate set status='done',end_at=%s,process=100 where id=%s",
                        end_time, trans['id']
                    )
                    print("✅ 翻译完成，状态已更新为已完成")
                    
            except Exception as e:
                print(f"更新进度失败: {str(e)}")
            
            last_completed_count = current_completed
        
        if complete:
            break
        else:
            time.sleep(1)

    text_count=0
    slide_count = 0
    for slide in slides:
        slide_count += 1
        slide_processed_count = 0
        # 应用翻译结果到幻灯片
        # logger.info(f"正在应用翻译结果到第 {slide_count} 页幻灯片...")
        
        # 第三页特殊调试
        if slide_count == 3:
            # logger.info("🔍 第三页翻译应用调试模式启动")
            # logger.info(f"第三页待处理文本数: {len(texts)}")
            pass
        
        for shape in slide.shapes:
            # 添加详细的形状信息日志
            # logger.info(f"=== 处理第 {slide_count} 页形状 ===")
            # logger.info(f"形状类型: {type(shape).__name__}")
            # logger.info(f"形状名称: {getattr(shape, 'name', 'N/A')}")
            # logger.info(f"是否有表格: {shape.has_table}")
            # logger.info(f"是否有文本框架: {shape.has_text_frame}")
            # logger.info(f"是否有文本属性: {hasattr(shape, 'text')}")
            try:
                # logger.info(f"是否有占位符格式: {hasattr(shape, 'placeholder_format')}")
                pass
            except ValueError:
                # logger.info(f"是否有占位符格式: False (非占位符形状)")
                pass
            
            # 处理表格
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
                            # 默认启用自适应样式
                            apply_translation_to_cell_with_adaptive_styles(cell, item['text'], item.get('style_info', {}))
                            text_count+=item.get('count', 1)
                            slide_processed_count += 1
                          
            # 处理所有有文本框架的形状（包括文本框、标题、占位符等）
            elif shape.has_text_frame:
                text_frame = shape.text_frame
                # logger.info(f"处理文本框架形状，段落数: {len(text_frame.paragraphs)}")
                for paragraph in text_frame.paragraphs:
                    text=paragraph.text
                    if text!=None and len(text)>0 and not common.is_all_punc(text) and len(texts)>0:
                        item=texts.pop(0)
                        # 默认启用自适应样式
                        # logger.info(f"应用翻译到段落: 原文='{paragraph.text[:30]}...' -> 译文='{item['text'][:30]}...'")
                        apply_translation_to_paragraph_with_adaptive_styles(paragraph, item['text'], item.get('style_info', {}))
                        text_count+=item.get('count', 1)
                        slide_processed_count += 1
                        # logger.info(f"段落翻译完成，当前runs数: {len(paragraph.runs)}")
                    elif len(texts) == 0:
                        logger.warning(f"文本列表已为空，无法处理段落: '{text[:30]}...'")
                
                # 处理遗漏的文本框架内容
                if text_frame.text and text_frame.text.strip() and len(texts)>0:
                    # 检查是否有对应的文本框架项目
                    for i, item in enumerate(texts):
                        if item.get('type') == 'text_frame' and item.get('text_frame') == text_frame:
                            item = texts.pop(i)
                            logger.info(f"处理文本框架内容: 原文='{text_frame.text[:30]}...' -> 译文='{item['text'][:30]}...'")
                            # 直接设置文本框架的文本
                            original_text = text_frame.text
                            text_frame.text = item['text']
                            # 应用自适应样式到所有段落
                            if text_frame.paragraphs:
                                for paragraph in text_frame.paragraphs:
                                    if paragraph.runs:
                                        for run in paragraph.runs:
                                            apply_adaptive_styles_ppt(run, original_text, item['text'])
                            text_count += item.get('count', 1)
                            slide_processed_count += 1
                            logger.info(f"文本框架内容处理完成，当前段落数: {len(text_frame.paragraphs)}")
                            break
            
            # 处理其他可能有文本的形状（如形状内的文本）
            elif hasattr(shape, 'text') and shape.text:
                text = shape.text
                if text!=None and len(text)>0 and not common.is_all_punc(text) and len(texts)>0:
                    item=texts.pop(0)
                    # 处理形状文本
                    original_text = shape.text
                    shape.text = item['text']
                    # 应用自适应样式到形状文本
                    apply_adaptive_styles_to_shape(shape, original_text, item['text'])
                    text_count+=item.get('count', 1)
                    slide_processed_count += 1
                elif len(texts) == 0:
                    logger.warning(f"文本列表已为空，无法处理形状文本: '{text[:30]}...'")
            
            # 处理遗漏的文本框架
            elif hasattr(shape, 'text_frame') and shape.text_frame:
                text_frame = shape.text_frame
                if text_frame.text and text_frame.text.strip():
                    for paragraph in text_frame.paragraphs:
                        text = paragraph.text
                        if text and len(text.strip()) > 0 and not common.is_all_punc(text) and len(texts)>0:
                            item=texts.pop(0)
                            # 默认启用自适应样式
                            apply_translation_to_paragraph_with_adaptive_styles(paragraph, item['text'], item.get('style_info', {}))
                            text_count+=item.get('count', 1)
                            slide_processed_count += 1
                        elif len(texts) == 0:
                            logger.warning(f"文本列表已为空，无法处理遗漏的文本框架段落: '{text[:30]}...'")
            
            # 处理形状名称文本
            elif hasattr(shape, 'name') and shape.name:
                shape_name = shape.name
                if shape_name and len(shape_name.strip()) > 0 and len(texts)>0:
                    item=texts.pop(0)
                    # 处理形状名称文本
                    original_name = shape.name
                    shape.name = item['text']
                    # 应用自适应样式到形状名称
                    apply_adaptive_styles_to_shape(shape, original_name, item['text'])
                    text_count+=item.get('count', 1)
                    slide_processed_count += 1
                elif len(texts) == 0:
                    logger.warning(f"文本列表已为空，无法处理形状名称: '{shape_name[:30]}...'")
            
            # 处理占位符文本
            try:
                if hasattr(shape, 'placeholder_format') and shape.placeholder_format and len(texts)>0:
                    # 检查是否有对应的占位符项目
                    for i, item in enumerate(texts):
                        if item.get('type') == 'placeholder' and item.get('shape') == shape:
                            item = texts.pop(i)
                            # 处理占位符文本
                            if hasattr(shape, 'text_frame') and shape.text_frame:
                                original_text = shape.text_frame.text
                                shape.text_frame.text = item['text']
                                # 应用自适应样式到所有段落
                                if shape.text_frame.paragraphs:
                                    for paragraph in shape.text_frame.paragraphs:
                                        if paragraph.runs:
                                            for run in paragraph.runs:
                                                apply_adaptive_styles_ppt(run, original_text, item['text'])
                            text_count += item.get('count', 1)
                            slide_processed_count += 1
                            break
            except ValueError as e:
                # 忽略"shape is not a placeholder"错误
                pass
            except Exception as e:
                logger.warning(f"应用占位符翻译时出错: {str(e)}")
        
        logger.info(f"第 {slide_count} 页幻灯片处理了 {slide_processed_count} 个文本元素")
    
    # 检查是否还有未处理的文本
    if texts:
        logger.warning(f"还有 {len(texts)} 个文本元素未处理:")
        for i, item in enumerate(texts[:5]):  # 只显示前5个
            logger.warning(f"  未处理文本 {i+1}: {item.get('text', '')[:50]}... (类型: {item.get('type', 'unknown')})")
        if len(texts) > 5:
            logger.warning(f"  ... 还有 {len(texts) - 5} 个未处理")
    
    # 添加详细的处理统计
    logger.info(f"=== PowerPoint处理统计 ===")
    logger.info(f"总文本元素数: {len(texts) + text_count}")
    logger.info(f"已处理文本数: {text_count}")
    logger.info(f"未处理文本数: {len(texts)}")
    logger.info(f"处理成功率: {text_count / (len(texts) + text_count) * 100:.1f}%" if (len(texts) + text_count) > 0 else "0%")

    logger.info(f"总共处理了 {text_count} 个文本元素")
    wb.save(trans['target_file'])
    end_time = datetime.now()
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
                logger.warning(f"提取run样式失败: {str(e)}")
                continue
            
            style_info['runs'].append({
                'text': run.text,
                'style': run_style
            })
    except Exception as e:
        # 如果提取段落样式失败，返回空的样式信息
        logger.warning(f"提取段落样式失败: {str(e)}")
    
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
    # 保存原始文本用于自适应计算
    original_text = paragraph.text
    
    # 清空段落内容
    paragraph.clear()
    
    # 如果有样式信息，按run恢复样式
    if style_info and 'runs' in style_info and style_info['runs']:
        # 按原始run的样式分配翻译文本（应用自适应样式）
        distribute_text_to_runs_with_adaptive_styles(paragraph, translated_text, style_info['runs'], original_text)
    else:
        # 没有样式信息，直接添加文本
        original_text = paragraph.text
        paragraph.text = translated_text
        # 应用自适应样式到所有runs
        if paragraph.runs:
            for run in paragraph.runs:
                apply_adaptive_styles_ppt(run, original_text, translated_text)
    
    # 恢复段落级别的样式
    if style_info and 'paragraph_level' in style_info:
        para_level = style_info['paragraph_level']
        if 'alignment' in para_level:
            paragraph.alignment = para_level['alignment']
        if 'level' in para_level:
            paragraph.level = para_level['level']


def apply_translation_to_cell(cell, translated_text, style_info):
    """应用翻译结果到表格单元格并恢复样式（原始版本）"""
    # 保存原始文本用于自适应计算
    original_text = cell.text
    
    # 清空单元格内容
    cell.text = ""
    
    # 如果有样式信息，按段落恢复样式
    if style_info and 'paragraphs' in style_info and style_info['paragraphs']:
        # 按原始段落的样式分配翻译文本（应用自适应样式）
        distribute_text_to_paragraphs_with_adaptive_styles(cell.text_frame, translated_text, style_info['paragraphs'], original_text)
    else:
        # 没有样式信息，直接添加文本
        original_text = cell.text
        cell.text = translated_text
        # 应用自适应样式到单元格中的所有段落的所有runs
        if cell.text_frame.paragraphs:
            for paragraph in cell.text_frame.paragraphs:
                if paragraph.runs:
                    for run in paragraph.runs:
                        apply_adaptive_styles_ppt(run, original_text, translated_text)


def apply_translation_to_paragraph_with_adaptive_styles(paragraph, translated_text, style_info):
    """应用翻译结果到段落并恢复样式，同时应用自适应样式"""
    try:
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
            # 应用自适应样式到所有runs
            if paragraph.runs:
                for run in paragraph.runs:
                    apply_adaptive_styles_ppt(run, original_text, translated_text)
        
        # 恢复段落级别的样式
        if style_info and 'paragraph_level' in style_info:
            para_level = style_info['paragraph_level']
            if 'alignment' in para_level:
                paragraph.alignment = para_level['alignment']
            if 'level' in para_level:
                paragraph.level = para_level['level']

    except Exception as e:
        logger.error(f"应用段落自适应样式失败: {str(e)}")
        # 回退到普通方法
        apply_translation_to_paragraph(paragraph, translated_text, style_info)


def apply_translation_to_cell_with_adaptive_styles(cell, translated_text, style_info):
    """应用翻译到单元格，使用自适应样式"""
    try:
        # 保存原始文本用于自适应计算
        original_text = cell.text
        
        # 清空单元格内容
        cell.text = ""
        
        # 使用自适应样式分发文本
        distribute_text_to_paragraphs_with_adaptive_styles(cell.text_frame.paragraphs[0], translated_text, style_info, original_text)
        
        # logger.info(f"单元格自适应样式应用完成，当前runs数: {len(cell.text_frame.paragraphs[0].runs)}")
        
    except Exception as e:
        logger.error(f"应用单元格自适应样式失败: {str(e)}")
        # 回退到普通方法
        apply_translation_to_cell(cell, translated_text, style_info)


def distribute_text_to_runs_with_adaptive_styles(paragraph, translated_text, run_styles, original_text):
    """将翻译文本按原始run的样式分配到新的run中，同时应用自适应样式"""
    if not run_styles:
        paragraph.text = translated_text
        # 应用自适应样式到所有runs
        if paragraph.runs:
            for run in paragraph.runs:
                apply_adaptive_styles_ppt(run, original_text, translated_text)
        return
    
    # 计算每个run应该分配的文本长度
    total_original_length = sum(len(run['text']) for run in run_styles)
    if total_original_length == 0:
        paragraph.text = translated_text
        # 应用自适应样式到所有runs
        if paragraph.runs:
            for run in paragraph.runs:
                apply_adaptive_styles_ppt(run, original_text, translated_text)
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
            # 应用自适应样式 - 使用整个段落的原始文本和翻译文本
            apply_adaptive_styles_ppt(run, original_text, translated_text)


def distribute_text_to_paragraphs_with_adaptive_styles(text_frame, translated_text, paragraph_styles, original_text):
    """将翻译文本按原始段落的样式分配到新的段落中，同时应用自适应样式"""
    if not paragraph_styles:
        text_frame.text = translated_text
        # 应用自适应样式到所有段落的所有runs
        if text_frame.paragraphs:
            for paragraph in text_frame.paragraphs:
                if paragraph.runs:
                    for run in paragraph.runs:
                        apply_adaptive_styles_ppt(run, original_text, translated_text)
        return
    
    # 清空文本框架
    text_frame.clear()
    
    # 按段落分配文本
    total_original_length = sum(len(run['text']) for para in paragraph_styles for run in para['runs'])
    if total_original_length == 0:
        text_frame.text = translated_text
        # 应用自适应样式到所有段落的所有runs
        if text_frame.paragraphs:
            for paragraph in text_frame.paragraphs:
                if paragraph.runs:
                    for run in paragraph.runs:
                        apply_adaptive_styles_ppt(run, original_text, translated_text)
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
            distribute_text_to_runs_with_adaptive_styles(paragraph, allocated_text, para_style['runs'], original_text)
            
            # 恢复段落级别的样式
            if 'paragraph_level' in para_style:
                para_level = para_style['paragraph_level']
                if 'alignment' in para_level:
                    paragraph.alignment = para_level['alignment']
                if 'level' in para_level:
                    paragraph.level = para_level['level']


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
                logger.warning(f"应用颜色样式失败: {str(e)}")
                pass  # 如果颜色设置失败，跳过颜色设置
    except Exception as e:
        # 如果应用样式失败，记录错误但继续处理
        logger.warning(f"应用run样式失败: {str(e)}")


def calculate_adaptive_font_size_ppt(original_text, translated_text, original_font_size):
    """根据翻译后文本长度计算PPT自适应字体大小"""
    try:
        if not original_font_size:
            return None
        
        original_length = len(original_text.strip())
        translated_length = len(translated_text.strip())
        
        if original_length == 0:
            return original_font_size
        
        length_ratio = translated_length / original_length
        
        # logger.info(f"PPT字体自适应调试: 原文长度={original_length}, 译文长度={translated_length}, 比例={length_ratio:.2f}")
        
        if length_ratio > 2.0:  # 文本长度增加超过100%
            new_size = max(original_font_size * 0.5, original_font_size / length_ratio)
            # logger.info(f"PPT字体自适应: 文本特别长，缩小到50% -> {new_size}pt")
            return int(new_size)
        elif length_ratio > 1.3:  # 文本长度增加超过30%
            new_size = max(original_font_size * 0.5, original_font_size / length_ratio)
            # logger.info(f"PPT字体自适应: 文本较长，缩小到50% -> {new_size}pt")
            return int(new_size)
        elif length_ratio < 0.7:  # 文本长度减少超过30%
            new_size = min(original_font_size * 1.3, original_font_size / length_ratio)
            return int(new_size)
        else:
            return original_font_size
            
    except Exception as e:
        logger.error(f"计算PPT自适应字体大小失败: {str(e)}")
        return original_font_size


def apply_adaptive_styles_ppt(run, original_text, translated_text):
    try:
        # 获取原始字体大小
        original_font_size = None
        
        # 方法1：直接从run获取
        if hasattr(run, 'font') and run.font and hasattr(run.font, 'size'):
            original_font_size = run.font.size
            # logger.info(f"从run.font.size获取字体大小: {original_font_size}pt")
        
        # 方法2：从段落默认属性获取
        if not original_font_size and hasattr(run, '_element') and run._element.getparent() is not None:
            parent = run._element.getparent()
            if hasattr(parent, 'pPr') and parent.pPr is not None:
                if hasattr(parent.pPr, 'defRPr') and parent.pPr.defRPr is not None:
                    if hasattr(parent.pPr.defRPr, 'sz') and parent.pPr.defRPr.sz is not None:
                        original_font_size = parent.pPr.defRPr.sz.val
                        # logger.info(f"从段落默认属性获取字体大小: {original_font_size}pt")
        
        # 方法3：使用默认值
        if not original_font_size:
            original_font_size = 14  # 默认14pt
            # logger.info(f"使用默认字体大小: {original_font_size}pt")
        
        # 计算新的字体大小
        new_font_size = calculate_adaptive_font_size_ppt(original_text, translated_text, original_font_size)
        
        if new_font_size and new_font_size != original_font_size:
            # 应用新的字体大小
            if hasattr(run, 'font') and run.font:
                run.font.size = Pt(new_font_size)
                # logger.info(f"应用自适应字体大小: {original_font_size}pt -> {new_font_size}pt")
            else:
                # 如果没有font属性，尝试创建
                run.font.size = Pt(new_font_size)
                # logger.info(f"创建并应用自适应字体大小: {original_font_size}pt -> {new_font_size}pt")
        else:
            # logger.info(f"字体大小无需调整: {original_font_size}pt")
            pass
            
    except Exception as e:
        logger.error(f"应用PPT自适应样式失败: {str(e)}")
        # 出错时保持原始字体大小
        pass


def apply_adaptive_styles_to_shape(shape, original_text, translated_text):
    """应用自适应样式到形状文本"""
    try:
        # 获取原始字体大小
        original_font_size = None
        
        # 方法1：从文本框架获取字体大小
        if hasattr(shape, 'text_frame') and shape.text_frame:
            if shape.text_frame.paragraphs:
                paragraph = shape.text_frame.paragraphs[0]
                if paragraph.runs:
                    run = paragraph.runs[0]
                    if run.font.size:
                        try:
                            original_font_size = run.font.size.pt
                        except:
                            original_font_size = None
        
        # 方法2：从形状属性获取字体大小（如果有的话）
        if not original_font_size and hasattr(shape, 'text') and shape.text:
            # 对于简单的形状文本，尝试获取默认字体大小
            try:
                # 使用一个合理的默认字体大小
                original_font_size = 18  # 默认18pt
                # logger.info(f"PPT形状自适应: 使用默认字体大小 {original_font_size}pt")
            except:
                original_font_size = None
        
        # 方法3：从形状名称获取字体大小（如果有的话）
        if not original_font_size and hasattr(shape, 'name') and shape.name:
            # 对于形状名称，使用较小的默认字体大小
            original_font_size = 12  # 默认12pt
            # logger.info(f"PPT形状名称自适应: 使用默认字体大小 {original_font_size}pt")
        
        # 计算自适应字体大小
        if original_font_size:
            adaptive_font_size = calculate_adaptive_font_size_ppt(original_text, translated_text, original_font_size)
            if adaptive_font_size and adaptive_font_size != original_font_size:
                from pptx.util import Pt
                # 应用到形状的文本框架
                if hasattr(shape, 'text_frame') and shape.text_frame and shape.text_frame.paragraphs:
                    for paragraph in shape.text_frame.paragraphs:
                        for run in paragraph.runs:
                            run.font.size = Pt(adaptive_font_size)
                # logger.info(f"PPT形状字体大小自适应: {original_font_size}pt -> {adaptive_font_size}pt")
            else:
                # logger.info(f"PPT形状自适应: 字体大小未改变 (原始={original_font_size}pt, 计算={adaptive_font_size}pt)")
                pass
        else:
            logger.warning(f"PPT形状自适应: 无法获取原始字体大小")
                    
    except Exception as e:
        logger.error(f"应用PPT形状自适应样式失败: {str(e)}")


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
            # 按run分配文本并应用样式
            distribute_text_to_runs(paragraph, allocated_text, para_style['runs'])
            
            # 恢复段落级别的样式
            if 'paragraph_level' in para_style:
                para_level = para_style['paragraph_level']
                if 'alignment' in para_level:
                    paragraph.alignment = para_level['alignment']
                if 'level' in para_level:
                    paragraph.level = para_level['level']


