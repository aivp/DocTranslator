import os
import time
import datetime
import traceback
from pathlib import Path
import threading
from docx import Document
from docx.oxml.ns import qn
from . import to_translate
from . import common
import zipfile
import xml.etree.ElementTree as ET
from threading import Lock
import re
import shutil

from ..utils.doc2x import Doc2XService

# 线程安全打印锁
print_lock = Lock()

# 特殊符号和数学符号的正则表达式
SPECIAL_SYMBOLS_PATTERN = re.compile(
    r'^[★☆♥♦♣♠♀♂☼☾☽♪♫♬☑☒✓✔✕✖✗✘⊕⊗∞∑∏πΠ±×÷√∛∜∫∮∇∂∆∏∑√∝∞∟∠∡∢∣∤∥∦∧∨∩∪∫∬∭∮∯∰∱∲∳∴∵∶∷∸∹∺∻∼∽∾∿≀≁≂≃≄≅≆≇≈≉≊≋≌≍≎≏≐≑≒≓≔≕≖≗≘≙≚≛≜≝≞≟≠≡≢≣≤≥≦≧≨≩≪≫≬≭≮≯≰≱≲≳≴≵≶≷≸≹≺≻≼≽≾≿⊀⊁⊂⊃⊄⊅⊆⊇⊈⊉⊊⊋⊌⊍⊎⊏⊐⊑⊒⊓⊔⊕⊖⊗⊘⊙⊚⊛⊜⊝⊞⊟⊠⊡⊢⊣⊤⊥⊦⊧⊨⊩⊪⊫⊬⊭⊮⊯⊰⊱⊲⊳⊴⊵⊶⊷⊸⊹⊺⊻⊼⊽⊾⊿⋀⋁⋂⋃⋄⋅⋆⋇⋈⋉⋊⋋⋌⋍⋎⋏⋐⋑⋒⋓⋔⋕⋖⋗⋘⋙⋚⋛⋜⋝⋞⋟⋠⋡⋢⋣⋤⋥⋦⋧⋨⋩⋪⋫⋬⋭⋮⋯⋰⋱⋲⋳⋴⋵⋶⋷⋸⋹⋺⋻⋼⋽⋾⋿]+$')

# 纯数字和简单标点的正则表达式
NUMBERS_PATTERN = re.compile(r'^[\d\s\.,\-\+\*\/\(\)\[\]\{\}]+$')


def check_docx_quality(docx_path):
    """检查转换后的DOCX文件质量，分析编码和文本内容"""
    try:
        print(f"\n=== 开始DOCX文件质量检查 ===")
        print(f"文件路径: {docx_path}")
        
        # 检查文件基本信息
        file_size = os.path.getsize(docx_path)
        print(f"文件大小: {file_size} 字节")
        
        if file_size < 1000:  # 小于1KB可能有问题
            print("⚠️  警告: 文件大小异常，可能转换失败")
            return False
        
        # 尝试加载文档
        try:
            document = Document(docx_path)
            print(f"✅ 文档加载成功")
        except Exception as e:
            print(f"❌ 文档加载失败: {str(e)}")
            return False
        
        # 分析文档结构
        paragraph_count = len(document.paragraphs)
        table_count = len(document.tables)
        section_count = len(document.sections)
        
        print(f"文档结构: {paragraph_count} 个段落, {table_count} 个表格, {section_count} 个节")
        
        # 分析前几个段落的文本内容
        print(f"\n--- 前5个段落内容分析 ---")
        chinese_chars = 0
        total_chars = 0
        sample_texts = []
        
        for i, para in enumerate(document.paragraphs[:5]):
            if para.text.strip():
                text = para.text.strip()
                sample_texts.append(text)
                
                # 统计字符
                para_chinese = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
                para_total = len(text)
                chinese_chars += para_chinese
                total_chars += para_total
                
                # 显示段落内容（限制长度避免日志过长）
                display_text = text[:100] + "..." if len(text) > 100 else text
                print(f"段落{i+1}: '{display_text}'")
                print(f"  长度: {para_total}, 中文字符: {para_chinese}")
                
                # 显示编码信息
                try:
                    encoded = text.encode('utf-8')
                    print(f"  UTF-8编码: {encoded}")
                except Exception as e:
                    print(f"  编码检查失败: {str(e)}")
        
        # 分析表格内容
        if table_count > 0:
            print(f"\n--- 表格内容分析 ---")
            table_chinese = 0
            table_total = 0
            
            for i, table in enumerate(document.tables[:2]):  # 只分析前2个表格
                print(f"表格{i+1}:")
                for row_idx, row in enumerate(table.rows[:3]):  # 只分析前3行
                    for col_idx, cell in enumerate(row.cells[:3]):  # 只分析前3列
                        if cell.text.strip():
                            text = cell.text.strip()
                            cell_chinese = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
                            cell_total = len(text)
                            table_chinese += cell_chinese
                            table_total += cell_total
                            
                            if cell_total > 0:
                                display_text = text[:50] + "..." if len(text) > 50 else text
                                print(f"  单元格[{row_idx+1},{col_idx+1}]: '{display_text}' (中文字符: {cell_chinese})")
            
            chinese_chars += table_chinese
            total_chars += table_total
            print(f"表格总计: {table_chinese} 个中文字符, {table_total} 个总字符")
        
        # 统计结果
        print(f"\n--- 质量检查结果 ---")
        if total_chars > 0:
            chinese_ratio = (chinese_chars / total_chars) * 100
            print(f"中文字符比例: {chinese_chars}/{total_chars} ({chinese_ratio:.1f}%)")
            
            if chinese_ratio < 10:
                print("⚠️  警告: 中文字符比例过低，可能存在编码问题")
            elif chinese_ratio > 80:
                print("✅ 中文字符比例正常")
            else:
                print("ℹ️  中文字符比例中等")
        else:
            print("⚠️  警告: 未发现任何文本内容")
        
        # 检查是否有明显的问题
        if paragraph_count == 0 and table_count == 0:
            print("❌ 严重问题: 文档没有任何内容")
            return False
        
        if chinese_chars == 0 and total_chars > 0:
            print("⚠️  警告: 有文本内容但没有中文字符，可能存在编码问题")
        
        print(f"=== DOCX质量检查完成 ===\n")
        return True
        
    except Exception as e:
        print(f"❌ DOCX质量检查失败: {str(e)}")
        traceback.print_exc()
        return False


def get_doc2x_save_dir():
    # 获取基础存储目录
    base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).parent.absolute()

    # 创建日期子目录（YYYY-MM-DD）
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    save_dir = base_dir / "storage" / "doc2x_results" / date_str

    save_dir.mkdir(parents=True, exist_ok=True)

    return str(save_dir)


def start(trans):
    """PDF翻译入口"""
    print("🚨 DEBUG: PDF翻译函数被调用！")
    print("🚨 DEBUG: 这是强制输出测试")
    
    try:
        # 开始时间
        start_time = datetime.datetime.now()
        print(f"=== 开始PDF翻译任务 ===")
        print(f"任务ID: {trans['id']}")
        print(f"源文件: {trans['file_path']}")
        print(f"目标文件: {trans['target_file']}")
        print(f"开始时间: {start_time}")
        print("=" * 50)

        # 检查文件是否存在
        original_path = Path(trans['file_path'])
        print(f"检查源文件是否存在: {original_path}")
        if not original_path.exists():
            print(f"❌ 源文件不存在: {trans['file_path']}")
            to_translate.error(trans['id'], f"文件不存在: {trans['file_path']}")
            return False
        print(f"✅ 源文件存在，大小: {os.path.getsize(original_path)} 字节")

        # 确保目标目录存在
        target_dir = os.path.dirname(trans['target_file'])
        print(f"创建目标目录: {target_dir}")
        os.makedirs(target_dir, exist_ok=True)
        print(f"✅ 目标目录已准备")

        # 获取doc2x保存目录
        doc2x_save_dir = get_doc2x_save_dir()
        print(f"📁 doc2x保存目录: {doc2x_save_dir}")

        # 设置转换后的Word文件路径（保存在doc2x_results目录下）
        docx_filename = f"{original_path.stem}_doc2x.docx"
        docx_path = os.path.join(doc2x_save_dir, docx_filename)
        print(f"📄 转换后的DOCX文件路径: {docx_path}")

        # 如果文件已存在，先删除
        if os.path.exists(docx_path):
            try:
                os.remove(docx_path)
                print(f"已删除已存在的文件: {docx_path}")
            except Exception as e:
                print(f"删除已存在的文件失败: {str(e)}")
                # 使用时间戳创建唯一文件名
                docx_filename = f"{original_path.stem}_doc2x_{int(time.time())}.docx"
                docx_path = os.path.join(doc2x_save_dir, docx_filename)

        print(f"转换后的DOCX文件将保存在: {docx_path}")

        # 使用Doc2X服务将PDF转换为DOCX
        print(f"开始将PDF转换为DOCX: {original_path}")

        # 获取API密钥
        api_key = trans.get('doc2x_api_key', '')
        print(f"🔑 检查API密钥: {'已设置' if api_key else '未设置'}")
        if not api_key:
            print(f"❌ 缺少Doc2X API密钥")
            to_translate.error(trans['id'], "缺少Doc2X API密钥")
            return False
        print(f"✅ API密钥已设置")

        # 1. 启动转换任务
        print(f"🚀 开始启动Doc2X转换任务...")
        try:
            uid = Doc2XService.start_task(api_key, str(original_path))
            print(f"✅ Doc2X任务启动成功，UID: {uid}")
        except Exception as e:
            print(f"❌ 启动Doc2X任务失败: {str(e)}")
            to_translate.error(trans['id'], f"启动Doc2X任务失败: {str(e)}")
            return False

        # 2. 等待解析完成
        max_retries = 60  # 最多等待10分钟
        retry_count = 0
        while retry_count < max_retries:
            try:
                status_info = Doc2XService.check_parse_status(api_key, uid)
                if status_info['status'] == 'success':
                    print(f"PDF解析成功: {uid}")
                    break
                elif status_info['status'] == 'failed':
                    to_translate.error(trans['id'],
                                       f"PDF解析失败: {status_info.get('detail', '未知错误')}")
                    return False

                # 更新进度
                progress = int(status_info.get('progress', 0) * 50)  # 解析阶段占总进度的50%
                print(f"PDF解析进度: {progress}%")

                # 等待10秒后再次检查
                time.sleep(10)
                retry_count += 1
            except Exception as e:
                to_translate.error(trans['id'], f"检查解析状态失败: {str(e)}")
                return False

        if retry_count >= max_retries:
            to_translate.error(trans['id'], "PDF解析超时")
            return False

        # 3. 触发导出
        try:
            export_success = Doc2XService.trigger_export(api_key, uid, original_path.stem)
            if not export_success:
                to_translate.error(trans['id'], "触发导出失败")
                return False
            print(f"已触发导出: {uid}")
        except Exception as e:
            to_translate.error(trans['id'], f"触发导出失败: {str(e)}")
            return False

        # 4. 等待导出完成并下载
        try:
            download_url = Doc2XService.check_export_status(api_key, uid)
            print(f"获取到下载链接: {download_url}")

            # 下载文件
            download_success = Doc2XService.download_file(download_url, docx_path)
            if not download_success:
                to_translate.error(trans['id'], "下载转换后的DOCX文件失败")
                return False
            print(f"DOCX文件下载成功: {docx_path}")
        except Exception as e:
            to_translate.error(trans['id'], f"下载DOCX文件失败: {str(e)}")
            return False

        # 确认文件存在
        if not os.path.exists(docx_path):
            to_translate.error(trans['id'], "转换后的DOCX文件不存在")
            return False

        # 4.5. 检查转换后的DOCX文件质量
        print(f"开始检查转换后的DOCX文件质量...")
        if not check_docx_quality(docx_path):
            print("⚠️  DOCX文件质量检查发现问题，但继续处理...")
        else:
            print("✅ DOCX文件质量检查通过")

        # 5. 使用Word翻译逻辑处理DOCX文件
        # 创建一个新的trans对象，包含DOCX文件路径
        docx_trans = trans.copy()
        docx_trans['file_path'] = docx_path

        # 设置目标文件路径（如果是PDF，添加.docx扩展名）
        target_file = trans['target_file']
        if target_file.lower().endswith('.pdf'):
            target_file = target_file + '.docx'
        docx_trans['target_file'] = target_file

        # 加载Word文档
        try:
            document = Document(docx_path)
            print(f"成功加载DOCX文档: {docx_path}")
        except Exception as e:
            to_translate.error(trans['id'], f"文档加载失败: {str(e)}")
            return False

        # 提取需要翻译的文本
        texts = []
        extract_content_for_translation(document, docx_path, texts)
        print(f"从DOCX提取了 {len(texts)} 个文本片段")

        # 过滤掉特殊符号和纯数字
        filtered_texts = []
        skipped_count = 0
        for i, item in enumerate(texts):
            if should_translate(item['text']):
                filtered_texts.append(item)
            else:
                # 对于不需要翻译的内容，标记为已完成
                item['complete'] = True
                text = item['text']
                reason = get_skip_reason(text)
                skipped_count += 1
                
                # 限制日志长度，避免输出过多
                if skipped_count <= 50:  # 只显示前50个跳过的项目
                    display_text = text[:50] + "..." if len(text) > 50 else text
                    print(f"跳过翻译: '{display_text}' - 原因: {reason}")
                elif skipped_count == 51:
                    print(f"... 还有更多跳过的项目，不再显示详细原因 ...")

        print(f"过滤后需要翻译的文本片段: {len(filtered_texts)}")
        print(f"跳过的文本片段: {skipped_count}")

        # 多线程翻译
        run_translation(docx_trans, filtered_texts, max_threads=10)

        # 写入翻译结果（完全保留原始格式）
        text_count = apply_translations(document, texts)
        print(f"应用了 {text_count} 个翻译结果")

        # 保存文档
        try:
            document.save(target_file)
            print(f"翻译后的文档保存成功: {target_file}")
        except Exception as e:
            to_translate.error(trans['id'], f"保存文档失败: {str(e)}")
            return False

        # 处理批注等特殊元素
        update_special_elements(target_file, texts)

        # 7. 完成处理
        end_time = datetime.datetime.now()
        spend_time = common.display_spend(start_time, end_time)
        if trans['run_complete']:
            to_translate.complete(trans, text_count, spend_time)
        print(f"PDF翻译任务完成: {trans['id']}")
        return True

    except Exception as e:
        # 打印详细错误信息
        print(f"❌ PDF翻译过程出错: {str(e)}")
        print("详细错误信息:")
        traceback.print_exc()
        # 确保错误状态被正确记录
        to_translate.error(trans['id'], f"PDF翻译过程出错: {str(e)}")
        return False


def check_image(run):
    """检查run是否包含图片"""
    try:
        # 检查run中是否有图片元素
        for element in run._element:
            if element.tag.endswith('drawing') or element.tag.endswith('picture'):
                return True
        return False
    except:
        return False


def are_runs_compatible(run1, run2):
    """检查两个run是否兼容（最严格的兼容性检查）"""
    try:
        # 1. 字体名称必须完全相同
        if run1.font.name != run2.font.name:
            return False
        
        # 2. 字体大小必须完全相同
        if run1.font.size != run2.font.size:
            return False
        
        # 3. 粗体状态必须完全相同
        if run1.font.bold != run2.font.bold:
            return False
        
        # 4. 斜体状态必须完全相同
        if run1.font.italic != run2.font.italic:
            return False
        
        # 5. 下划线状态必须完全相同
        if run1.font.underline != run2.font.underline:
            return False
        
        # 6. 删除线状态必须完全相同
        if run1.font.strike != run2.font.strike:
            return False
        
        # 7. 字体颜色必须完全相同
        if run1.font.color.rgb != run2.font.color.rgb:
            return False
        
        # 8. 背景色必须完全相同
        if run1.font.highlight_color != run2.font.highlight_color:
            return False
        
        # 9. 上标/下标状态必须完全相同
        if run1.font.superscript != run2.font.superscript:
            return False
        
        # 10. 小型大写字母状态必须完全相同
        if run1.font.small_caps != run2.font.small_caps:
            return False
        
        return True
    except:
        # 如果任何检查失败，默认不兼容
        return False


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
            if check_image(run):
                has_image = True
                break
        
        if has_image:
            continue
        
        texts.append({
            "text": merged_item['text'],
            "type": "merged_run",
            "merged_item": merged_item,
            "complete": False,
            "context_type": context_type  # 标记类型
        })


def conservative_run_merge(paragraph_runs, max_merge_length=500):
    """最严格的run合并策略"""
    
    merged = []
    current_group = []
    current_length = 0
    original_count = len([r for r in paragraph_runs if check_text(r.text)])
    merged_count = 0
    
    for run in paragraph_runs:
        # 跳过包含图片的run
        if check_image(run):
            # 保存当前组
            if current_group:
                merged.append(merge_compatible_runs(current_group))
                if len(current_group) > 1:
                    merged_count += 1
                current_group = []
                current_length = 0
            
            # 图片run单独处理，但不添加到翻译列表
            continue
        
        if not check_text(run.text):
            continue
        
        # 最严格条件：只合并极短的run（通常是空格、标点、单个字符）
        if len(run.text) <= 5 and current_length < max_merge_length:
            # 检查格式兼容性（最严格检查）
            if not current_group or are_runs_compatible(current_group[-1], run):
                # 额外检查：确保合并后的文本不会过长
                if current_length + len(run.text) <= 10:
                    current_group.append(run)
                    current_length += len(run.text)
                    continue
        
        # 保存当前组
        if current_group:
            merged.append(merge_compatible_runs(current_group))
            if len(current_group) > 1:
                merged_count += 1
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
            merged_count += 1
    
    # 打印合并统计信息
    if merged_count > 0:
        print(f"Run合并优化（最严格策略）: 原始{original_count}个run -> 合并后{len(merged)}个，减少了{merged_count}个API调用")
    else:
        print(f"Run合并（最严格策略）: 未找到可合并的run，保持原始{original_count}个run")
    
    return merged


def merge_compatible_runs(run_group):
    """合并兼容的run组（最严格策略）"""
    
    # 合并文本
    merged_text = "".join(run.text for run in run_group)
    
    # 额外安全检查：确保合并后的文本不会过长
    if len(merged_text) > 20:
        print(f"⚠️  警告: 合并后文本过长({len(merged_text)}字符)，取消合并")
        # 如果合并后过长，返回单个run
        return {
            'text': run_group[0].text,
            'runs': [run_group[0]],
            'type': 'single'
        }
    
    # 额外检查：确保所有run的格式完全一致
    first_run = run_group[0]
    for run in run_group[1:]:
        if not are_runs_compatible(first_run, run):
            print(f"⚠️  警告: 检测到格式不一致，取消合并")
            return {
                'text': run_group[0].text,
                'runs': [run_group[0]],
                'type': 'single'
            }
    
    return {
        'text': merged_text,
        'runs': run_group,
        'type': 'merged'
    }


def get_skip_reason(text):
    """获取文本被跳过的原因"""
    if not text or len(text) == 0:
        return "空文本"
    
    if len(text.strip()) <= 2:
        text_stripped = text.strip()
        
        # 检查中文字符
        if all('\u4e00' <= char <= '\u9fff' for char in text_stripped):
            return f"短中文字符'{text_stripped}'（已允许翻译）"
        
        # 检查数字
        if text_stripped.isdigit():
            return f"短数字'{text_stripped}'（已允许翻译）"
        
        # 检查单位符号
        if all(char in '•℃VAhH' for char in text_stripped):
            return f"常用单位符号'{text_stripped}'（已允许翻译）"
        
        # 检查中英文混合
        if len(text_stripped) == 2:
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text_stripped)
            if has_chinese:
                return f"中英文混合短文本'{text_stripped}'（已允许翻译）"
        
        return f"短文本'{text_stripped}'（无意义）"
    
    if SPECIAL_SYMBOLS_PATTERN.match(text):
        return "纯特殊符号"
    
    if NUMBERS_PATTERN.match(text):
        return "纯数字和简单标点"
    
    if common.is_all_punc(text):
        return "纯标点符号"
    
    return "其他原因"


def should_translate(text):
    """判断文本是否需要翻译（改进的过滤逻辑）"""
    if not text or len(text) == 0:
        return False

    # 对于短文本（≤2字符），进行特殊处理
    if len(text.strip()) <= 2:
        text_stripped = text.strip()
        
        # 允许短中文字符（通常是有意义的）
        if all('\u4e00' <= char <= '\u9fff' for char in text_stripped):
            return True
        
        # 允许短数字组合
        if text_stripped.isdigit():
            return True
        
        # 允许常用单位符号组合
        if all(char in '•℃VAhH' for char in text_stripped):
            return True
        
        # 允许中英文混合的短文本（如"图1"、"表2"）
        if len(text_stripped) == 2:
            # 检查是否包含中文字符
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text_stripped)
            if has_chinese:
                return True
        
        # 过滤其他短文本
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


def extract_content_for_translation(document, file_path, texts):
    """提取需要翻译的内容，使用run合并优化"""
    # 正文段落
    for paragraph in document.paragraphs:
        extract_paragraph_with_merge(paragraph, texts, "paragraph")
        
        # 处理超链接（单独处理，避免与普通run混合）
        for hyperlink in paragraph.hyperlinks:
            for run in hyperlink.runs:
                if check_text(run.text):
                    texts.append({
                        "text": run.text,
                        "type": "run",
                        "run": run,
                        "complete": False
                    })

    # 表格内容
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    extract_paragraph_with_merge(paragraph, texts, "table_cell")
                    
                    # 处理表格中的超链接
                    for hyperlink in paragraph.hyperlinks:
                        for run in hyperlink.runs:
                            if check_text(run.text):
                                texts.append({
                                    "text": run.text,
                                    "type": "run",
                                    "run": run,
                                    "complete": False
                                })

    # 页眉页脚
    for section in document.sections:
        # 处理页眉
        for paragraph in section.header.paragraphs:
            extract_paragraph_with_merge(paragraph, texts, "header")
            
            # 处理页眉中的超链接
            for hyperlink in paragraph.hyperlinks:
                for run in hyperlink.runs:
                    if check_text(run.text):
                        texts.append({
                            "text": run.text,
                            "type": "run",
                            "run": run,
                            "complete": False
                        })

        # 处理页脚
        for paragraph in section.footer.paragraphs:
            extract_paragraph_with_merge(paragraph, texts, "footer")
            
            # 处理页脚中的超链接
            for hyperlink in paragraph.hyperlinks:
                for run in hyperlink.runs:
                    if check_text(run.text):
                        texts.append({
                            "text": run.text,
                            "type": "run",
                            "run": run,
                            "complete": False
                        })

    # 批注内容
    extract_comments(file_path, texts)


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


def run_translation(trans, texts, max_threads=10):
    """执行多线程翻译"""
    if not texts:
        print("没有需要翻译的内容")
        return

    event = threading.Event()
    run_index = 0
    active_count = threading.activeCount()

    print(f"开始翻译 {len(texts)} 个文本片段")

    while run_index < len(texts):
        if threading.activeCount() < max_threads + active_count and not event.is_set():
            thread = threading.Thread(
                target=to_translate.get,
                args=(trans, event, texts, run_index)
            )
            thread.start()
            print(f"启动翻译线程 {run_index}")
            run_index += 1
        time.sleep(0.1)

    # 等待翻译完成
    while not all(t.get('complete') for t in texts) and not event.is_set():
        time.sleep(1)

    print("所有翻译任务已完成")


def apply_translations(document, texts):
    """应用翻译结果到文档，完全保留原始格式"""
    text_count = 0

    for item in texts:
        if not item.get('complete', False):
            continue

        if item['type'] == 'run':
            # 直接替换run文本，保留所有格式
            item['run'].text = item.get('text', item['run'].text)
            text_count += 1
        elif item['type'] == 'merged_run':
            # 处理合并的run，需要将翻译结果分配回原始run
            merged_item = item['merged_item']
            translated_text = item.get('text', merged_item['text'])
            
            if merged_item['type'] == 'merged':
                # 合并的run组，需要智能分配翻译结果
                distribute_translation_to_runs(merged_item['runs'], translated_text)
            else:
                # 单个run，直接替换
                merged_item['runs'][0].text = translated_text
            
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


def update_special_elements(docx_path, texts):
    """更新批注等特殊元素"""
    # 筛选出需要处理的批注
    comment_texts = [t for t in texts if t.get('type') == 'comment' and t.get('complete')]
    if not comment_texts:
        return  # 没有需要处理的批注

    temp_path = f"temp_{int(time.time())}_{os.path.basename(docx_path)}"

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
            try:
                os.remove(temp_path)
            except:
                pass


def check_text(text):
    """检查文本是否有效（非空且非纯标点）"""
    return text and len(text) > 0 and not common.is_all_punc(text)
