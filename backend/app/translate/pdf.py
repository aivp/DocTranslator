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
    try:
        # 开始时间
        start_time = datetime.datetime.now()
        print(f"开始PDF翻译任务: {trans['id']}")

        # 检查文件是否存在
        original_path = Path(trans['file_path'])
        if not original_path.exists():
            to_translate.error(trans['id'], f"文件不存在: {trans['file_path']}")
            return False

        # 确保目标目录存在
        target_dir = os.path.dirname(trans['target_file'])
        os.makedirs(target_dir, exist_ok=True)

        # 获取doc2x保存目录
        doc2x_save_dir = get_doc2x_save_dir()

        # 设置转换后的Word文件路径（保存在doc2x_results目录下）
        docx_filename = f"{original_path.stem}_doc2x.docx"
        docx_path = os.path.join(doc2x_save_dir, docx_filename)

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
        if not api_key:
            to_translate.error(trans['id'], "缺少Doc2X API密钥")
            return False

        # 1. 启动转换任务
        try:
            uid = Doc2XService.start_task(api_key, str(original_path))
            print(f"Doc2X任务启动成功，UID: {uid}")
        except Exception as e:
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
        for i, item in enumerate(texts):
            if should_translate(item['text']):
                filtered_texts.append(item)
            else:
                # 对于不需要翻译的内容，标记为已完成
                item['complete'] = True
                print(f"跳过翻译: {item['text'][:30]}..." if len(
                    item['text']) > 30 else f"跳过翻译: {item['text']}")

        print(f"过滤后需要翻译的文本片段: {len(filtered_texts)}")

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
        traceback.print_exc()
        # 确保错误状态被正确记录
        to_translate.error(trans['id'], f"PDF翻译过程出错: {str(e)}")
        return False


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

    # 过滤过短的文本（如单个字符）
    if len(text.strip()) <= 1:
        return False

    return True


def extract_content_for_translation(document, file_path, texts):
    """提取需要翻译的内容，完全保留原始位置信息"""
    # 正文段落
    for paragraph in document.paragraphs:
        for run in paragraph.runs:
            if check_text(run.text):
                texts.append({
                    "text": run.text,
                    "type": "run",
                    "run": run,  # 直接保留run引用
                    "complete": False
                })
        # 处理超链接
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
                    for run in paragraph.runs:
                        if check_text(run.text):
                            texts.append({
                                "text": run.text,
                                "type": "run",
                                "run": run,
                                "complete": False
                            })
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
            for run in paragraph.runs:
                if check_text(run.text):
                    texts.append({
                        "text": run.text,
                        "type": "run",
                        "run": run,
                        "complete": False
                    })
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
            for run in paragraph.runs:
                if check_text(run.text):
                    texts.append({
                        "text": run.text,
                        "type": "run",
                        "run": run,
                        "complete": False
                    })
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

    return text_count


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
