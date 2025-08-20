# import tiktoken
import datetime
import hashlib
import logging
import os
import sys
import re
import openai
from . import common
from . import db
import time

from .baidu.main import baidu_translate

# 导入Qwen翻译模块
try:
    from .qwen_translate import qwen_translate, check_qwen_availability
except ImportError:
    # 如果Qwen模块不存在，使用默认函数
    def qwen_translate(text, target_language, source_lang="auto", tm_list=None, terms=None, domains=None):
        return text
    def check_qwen_availability():
        return False, "Qwen模块未找到"


def get(trans, event, texts, index):
    if event.is_set():
        exit(0)
    threads = trans['threads']
    if threads is None or threads == "" or int(threads) < 0:
        max_threads = 10
    else:
        max_threads = int(threads)
    translate_id = trans['id']
    target_lang = trans['lang']
    
    # ============== 模型配置 ==============
    model = trans['model']
    backup_model = trans['backup_model']
    
    # 打印当前配置（仅第一次）
    if index == 0:
        try:
            # 检查Qwen服务可用性
            if model == 'qwen-mt-plus':
                qwen_available, qwen_message = check_qwen_availability()
                logging.info(f"Qwen服务检查: {qwen_message}")
                if not qwen_available:
                    logging.warning("警告: Qwen服务不可用，将使用备用方案")
                else:
                    logging.info("Qwen翻译服务已启用")
        except:
            pass
    # ==========================================
    
    prompt = trans['prompt']
    extension = trans['extension'].lower()
    text = texts[index]
    api_key = trans['api_key']
    api_url = trans['api_url']
    app_id = trans['app_id']
    app_key = trans['app_key']
    comparison_id = trans.get('comparison_id', 0)
    # 确保comparison_id不为None，如果是None则设为0
    if comparison_id is None:
        comparison_id = 0
    # 不要强制转换为int，保持原始字符串格式以支持多个ID
    server = trans.get('server', 'openai')
    old_text = text['text']
    md5_key = md5_encryption(
        str(api_key) + str(api_url) + str(old_text) + str(prompt) + str(backup_model) + str(
            model) + str(target_lang))

    # ============== 百度翻译处理 ==============
    if server == 'baidu':
        try:
            oldtrans = db.get("select * from translate_logs where md5_key=%s", md5_key)
            if not text['complete']:
                content = oldtrans['content'] if oldtrans else baidu_translate(
                    text=old_text,
                    appid=app_id,
                    app_key=app_key,
                    from_lang='auto',
                    to_lang=target_lang,
                    use_term_base=comparison_id == 1  # 使用术语库
                )
                text['count'] = count_text(text['text'])
                if check_translated(content):
                    text['text'] = content  # 百度翻译无需过滤<think>标签
                    if not oldtrans:
                        db.execute("INSERT INTO translate_logs set api_url=%s,api_key=%s,"
                                   + "backup_model=%s ,created_at=%s ,prompt=%s,  "
                                   + "model=%s,target_lang=%s,source=%s,content=%s,md5_key=%s",
                                   str(api_url), str(api_key),
                                   str(backup_model),
                                   datetime.datetime.now(), str(prompt), str(model),
                                   str(target_lang),
                                   str(old_text),
                                   str(content), str(md5_key))
                text['complete'] = True
        except Exception as e:
            logging.error(f"百度翻译错误: {str(e)}")
            if "retry" not in text:
                text["retry"] = 0
            text["retry"] += 1
            if text["retry"] <= 3:
                time.sleep(5)
                logging.info('百度翻译出错，正在重试！')
                return get(trans, event, texts, index)  # 重新尝试
            text['complete'] = True

    # ============== AI翻译处理 ==============
    elif server == 'openai' or server == 'doc2x' or server == 'qwen':
        try:
            oldtrans = db.get("select * from translate_logs where md5_key=%s", md5_key)
            # mredis.set("threading_count",threading_num+1)
            # 目标语言映射处理
            LANGUAGE_MAPPING = {
                '中文': 'Chinese',
                '英语': 'English',
                '英文': 'English',  # 兼容旧版本
                '阿拉伯语': 'Arabic',
                '法语': 'French',
                '德文': 'German',  # 兼容旧版本
                '德语': 'German',
                '西班牙语': 'Spanish',
                '西班牙文': 'Spanish',  # 兼容旧版本
                '俄语': 'Russian',
                '俄文': 'Russian',  # 兼容旧版本
                '意大利语': 'Italian',
                '意大利文': 'Italian',  # 兼容旧版本
                '泰语': 'Thai',
                '越南语': 'Vietnamese',
                '印尼语/马来语': 'Indonesian',
                '印尼语': 'Indonesian',
                '马来语': 'Malay',
                '菲律宾语（他加禄语）': 'Filipino',
                '菲律宾语': 'Filipino',
                '他加禄语': 'Filipino',
                '缅甸语': 'Burmese',
                '柬埔寨语（高棉语）': 'Khmer',
                '柬埔寨语': 'Khmer',
                '高棉语': 'Khmer',
                '老挝语': 'Lao',
                '柬语': 'Khmer',
                '葡萄牙语': 'Portuguese'
            }
            
            # 使用映射字典处理目标语言
            target_lang = LANGUAGE_MAPPING.get(target_lang, target_lang)

            # 获取术语库内容并转换为tm_list格式（仅当使用千问模型且有术语库时）
            tm_list = None
            if model == 'qwen-mt-plus' and comparison_id:
                # 支持多个术语库ID，逗号分隔
                comparison_ids = [int(id.strip()) for id in str(comparison_id).split(',') if id.strip().isdigit()]
                
                if comparison_ids:
                    all_terms = {}  # 用于去重的字典
                    
                    for comp_id in comparison_ids:
                        try:
                            # 从 comparison_sub 表获取术语数据，使用get_all而不是execute
                            terms = db.get_all("select original, comparison_text from comparison_sub where comparison_sub_id=%s", comp_id)
                            
                            if terms and isinstance(terms, list) and len(terms) > 0:
                                # 解析术语库内容
                                for term in terms:
                                    if term and isinstance(term, dict) and term.get('original') and term.get('comparison_text'):
                                        source = term['original'].strip()
                                        target = term['comparison_text'].strip()
                                        # 去重：如果原文已存在，跳过（以第一个为准）
                                        if source not in all_terms:
                                            all_terms[source] = target
                            else:
                                logging.warning(f"术语库 {comp_id} 未找到术语数据")
                                
                        except Exception as e:
                            logging.error(f"查询术语库 {comp_id} 时发生异常: {str(e)}")
                            continue
                    
                    # 转换为tm_list格式
                    if all_terms:
                        tm_list = []
                        for source, target in all_terms.items():
                            tm_list.append({
                                "source": source,
                                "target": target
                            })
                
                    logging.info("千问的术语库")
                    # 只打印前10条，避免日志过长
                    if tm_list and len(tm_list) > 10:
                        logging.info(f"tm_list(前10条): {tm_list[:10]} ... 共{len(tm_list)}条")
                    else:
                        logging.info(f"tm_list: {tm_list}")
                    # 添加日志，显示最终传入模型的术语表
                    if all_terms:
                        logging.info(f"任务使用术语表ID: {comparison_id}")
                    else:
                        logging.warning(f"任务 {translate_id} 术语表ID {comparison_id} 未找到内容")
                else:
                    logging.warning(f"任务 {translate_id} 术语表ID格式无效: {comparison_id}")
            else:
                logging.info(f"任务 {translate_id} 未使用术语库，model: {model}, comparison_id: {comparison_id}")

            if text['complete'] == False:
                content = ''
                if oldtrans:
                    content = oldtrans['content']
                    # 特别处理PDF类型

                # elif extension == ".pdf":
                #     return handle_pdf(trans, event, texts, index)
                # elif extension == ".pdf":
                #     if text['type'] == "text":
                #         content = translate_html(text['text'], target_lang, model, prompt)
                #         time.sleep(0.1)
                #     else:
                #         content = get_content_by_image(text['text'], target_lang)
                #         time.sleep(0.1)
                # ---------------这里实现不同模型格式的请求--------------

                elif extension == ".md":
                    if model == 'qwen-mt-plus':
                        content = qwen_translate(text['text'], target_lang, tm_list=tm_list)
                    else:
                        content = req(text['text'], target_lang, model, prompt, True)
                else:
                    # 根据是否有上下文选择翻译方式
                    if 'context_text' in text and text.get('context_type') == 'body':
                        # 正文段落：使用带上下文的文本
                        if model == 'qwen-mt-plus':
                            content = qwen_translate(text['text'], target_lang, tm_list=tm_list)
                        else:
                            content = req(text['context_text'], target_lang, model, prompt, False)
                    else:
                        # 其他内容：使用原始文本
                        if model == 'qwen-mt-plus':
                            content = qwen_translate(text['text'], target_lang, tm_list=tm_list)
                        else:
                            content = req(text['text'], target_lang, model, prompt, False)
                    # print("content", text['content'])
                text['count'] = count_text(text['text'])
                
                # 检查是否是data_inspection_failed导致的空字符串
                if content == "" and model == 'qwen-mt-plus':
                    # data_inspection_failed错误，直接设置为完成状态，不进行重试
                    logging.warning(f"内容检查失败，跳过此内容: {text['text'][:50]}...")
                    text['text'] = ""  # 设置为空字符串
                    text['complete'] = True
                elif check_translated(content):
                    # 过滤deepseek思考过程
                    cleaned_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                    # 清理上下文标记
                    # cleaned_content = clean_translation_result(cleaned_content)
                    text['text'] = cleaned_content
                    if oldtrans is None:
                        db.execute("INSERT INTO translate_logs set api_url=%s,api_key=%s,"
                                   + "backup_model=%s ,created_at=%s ,prompt=%s,  "
                                   + "model=%s,target_lang=%s,source=%s,content=%s,md5_key=%s",
                                   str(api_url), str(api_key),
                                   str(backup_model),
                                   datetime.datetime.now(), str(prompt), str(model),
                                   str(target_lang),
                                   str(old_text),
                                   str(content), str(md5_key))
                    text['complete'] = True
                else:
                    # 翻译失败，记录警告但继续处理
                    logging.warning(f"翻译失败，保留原文: {text['text'][:50]}...")
                    text['complete'] = True
        except openai.AuthenticationError as e:
            # set_threading_num(mredis)
            return use_backup_model(trans, event, texts, index, "openai密钥或令牌无效")
        except openai.APIConnectionError as e:
            # set_threading_num(mredis)
            return use_backup_model(trans, event, texts, index,
                                    "请求无法与openai服务器或建立安全连接")
        except openai.PermissionDeniedError as e:
            # set_threading_num(mredis)
            texts[index] = text
            # return use_backup_model(trans, event, texts, index, "令牌额度不足")
        except openai.RateLimitError as e:
            # set_threading_num(mredis)
            if "retry" not in text:
                trans['model'] = backup_model
                trans['backup_model'] = model
                time.sleep(1)
                logging.warning("访问速率达到限制,交换备用模型与模型重新重试")
                get(trans, event, texts, index)
            else:
                return use_backup_model(trans, event, texts, index,
                                        "访问速率达到限制,10分钟后再试" + str(text['text']))
        except openai.InternalServerError as e:
            # set_threading_num(mredis)
            if "retry" not in text:
                trans['model'] = backup_model
                trans['backup_model'] = model
                time.sleep(1)
                logging.warning("当前分组上游负载已饱和，交换备用模型与模型重新重试")
                get(trans, event, texts, index)
            else:
                return use_backup_model(trans, event, texts, index,
                                        "当前分组上游负载已饱和，请稍后再试" + str(text['text']))
        except openai.APIStatusError as e:
            # set_threading_num(mredis)
            return use_backup_model(trans, event, texts, index, e.response)
        except Exception as e:
            # set_threading_num(mredis)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            line_number = exc_traceback.tb_lineno  # 异常抛出的具体行号
            logging.error(f"Error occurred on line: {line_number}")
            logging.error(f"Error details: {e}")
            if "retry" not in text:
                text["retry"] = 0
            text["retry"] += 1
            if text["retry"] <= 3:
                trans['model'] = backup_model
                trans['backup_model'] = model
                logging.warning("当前模型执行异常，交换备用模型与模型重新重试")
                time.sleep(1)
                get(trans, event, texts, index)
                return
            else:
                text['complete'] = True
            # traceback.print_exc()
            # print("translate error")
    
    texts[index] = text
    # print(text)
    if not event.is_set():
        process(texts, translate_id)
    # set_threading_num(mredis)
    return True  # 返回结果而不是exit(0)


def get11(trans, event, texts, index):
    if event.is_set():
        exit(0)
    threads = trans['threads']
    if threads is None or threads == "" or int(threads) < 0:
        max_threads = 10
    else:
        max_threads = int(threads)
    # mredis=rediscon.get_conn()
    # threading_num=get_threading_num(mredis)
    # while threading_num>=max_threads:
    #    time.sleep(1)
    # print('trans配置项', trans)
    translate_id = trans['id']
    target_lang = trans['lang']
    model = trans['model']
    backup_model = trans['backup_model']
    prompt = trans['prompt']
    extension = trans['extension'].lower()
    text = texts[index]
    api_key = trans['api_key']
    api_url = trans['api_url']
    old_text = text['text']
    md5_key = md5_encryption(
        str(api_key) + str(api_url) + str(old_text) + str(prompt) + str(backup_model) + str(
            model) + str(target_lang))
    try:
        oldtrans = db.get("select * from translate_logs where md5_key=%s", md5_key)
        # mredis.set("threading_count",threading_num+1)
        if text['complete'] == False:
            content = ''
            if oldtrans:
                content = oldtrans['content']
                # 特别处理PDF类型

            # elif extension == ".pdf":
            #     return handle_pdf(trans, event, texts, index)
            # elif extension == ".pdf":
            #     if text['type'] == "text":
            #         content = translate_html(text['text'], target_lang, model, prompt)
            #         time.sleep(0.1)
            #     else:
            #         content = get_content_by_image(text['text'], target_lang)
            #         time.sleep(0.1)
            # ---------------这里实现不同模型格式的请求--------------
            elif extension == ".md":
                content = req(text['text'], target_lang, model, prompt, True)
            else:
                content = req(text['text'], target_lang, model, prompt, False)
                # print("content", text['content'])
            text['count'] = count_text(text['text'])
            if check_translated(content):
                # 过滤deepseek思考过程
                text['text'] = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                if oldtrans is None:
                    db.execute("INSERT INTO translate_logs set api_url=%s,api_key=%s,"
                               + "backup_model=%s ,created_at=%s ,prompt=%s,  "
                               + "model=%s,target_lang=%s,source=%s,content=%s,md5_key=%s",
                               str(api_url), str(api_key),
                               str(backup_model),
                               datetime.datetime.now(), str(prompt), str(model), str(target_lang),
                               str(old_text),
                               str(content), str(md5_key))
            text['complete'] = True
    except openai.AuthenticationError as e:
        # set_threading_num(mredis)
        return use_backup_model(trans, event, texts, index, "openai密钥或令牌无效")
    except openai.APIConnectionError as e:
        # set_threading_num(mredis)
        return use_backup_model(trans, event, texts, index, "请求无法与openai服务器或建立安全连接")
    except openai.PermissionDeniedError as e:
        # set_threading_num(mredis)
        texts[index] = text
        # return use_backup_model(trans, event, texts, index, "令牌额度不足")
    except openai.RateLimitError as e:
        # set_threading_num(mredis)
        if "retry" not in text:
            trans['model'] = backup_model
            trans['backup_model'] = model
            time.sleep(1)
            logging.warning("访问速率达到限制,交换备用模型与模型重新重试")
            get(trans, event, texts, index)
        else:
            return use_backup_model(trans, event, texts, index,
                                    "访问速率达到限制,10分钟后再试" + str(text['text']))
    except openai.InternalServerError as e:
        # set_threading_num(mredis)
        if "retry" not in text:
            trans['model'] = backup_model
            trans['backup_model'] = model
            time.sleep(1)
            logging.warning("当前分组上游负载已饱和，交换备用模型与模型重新重试")
            get(trans, event, texts, index)
        else:
            return use_backup_model(trans, event, texts, index,
                                    "当前分组上游负载已饱和，请稍后再试" + str(text['text']))
    except openai.APIStatusError as e:
        # set_threading_num(mredis)
        return use_backup_model(trans, event, texts, index, e.response)
    except Exception as e:
        # set_threading_num(mredis)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        line_number = exc_traceback.tb_lineno  # 异常抛出的具体行号
        logging.error(f"Error occurred on line: {line_number}")
        logging.error(f"Error details: {e}")
        if "retry" not in text:
            text["retry"] = 0
        text["retry"] += 1
        if text["retry"] <= 3:
            trans['model'] = backup_model
            trans['backup_model'] = model
            logging.warning("当前模型执行异常，交换备用模型与模型重新重试")
            time.sleep(1)
            get(trans, event, texts, index)
            return
        else:
            text['complete'] = True
        # traceback.print_exc()
        # print("translate error")
    texts[index] = text
    # print(text)
    if not event.is_set():
        process(texts, translate_id)
    # set_threading_num(mredis)
    exit(0)


def handle_pdf(trans, event, texts, index):
    try:
        from . import pdf_parser
        success = pdf_parser.start(trans)
        if success:
            texts[index]['complete'] = True
        else:
            return use_backup_model(trans, event, texts, index, "PDF解析失败")
    except Exception as e:
        return use_backup_model(trans, event, texts, index, str(e))



# def get_threading_num(mredis):
#    threading_count=mredis.get("threading_count")
#    if threading_count is None or threading_count=="" or int(threading_count)<0:
#        threading_num=0
#    else:
#        threading_num=int(threading_count)
#    return threading_num
# def set_threading_num(mredis):
#    threading_count=mredis.get("threading_count")
#    if threading_count is None or threading_count=="" or int(threading_count)<1:
#        mredis.set("threading_count",0)
#    else:
#        threading_num=int(threading_count)
#        mredis.set("threading_count",threading_num-1)

def md5_encryption(data):
    md5 = hashlib.md5(data.encode('utf-8'))  # 创建一个md5对象
    return md5.hexdigest()  # 返回加密后的十六进制字符串


def req(text, target_lang, model, prompt, ext):
    # 判断是否是md格式
    if ext == True:
        # 如果是 md 格式，追加提示文本
        prompt += "。 请帮助我翻译以下 Markdown 文件中的内容。请注意，您只需翻译文本部分，而不应更改任何 Markdown 标签或格式。保持原有的标题、列表、代码块、链接和其他 Markdown 标签的完整性。"
    
    # 检查是否包含上下文标记
    if '[前文:' in text or '[后文:' in text:
        # 有上下文的情况：增强提示词
        enhanced_prompt = f"""
        {prompt}
        
        严格指令：
        1. 只翻译方括号外的文本，不要翻译方括号内的任何内容
        2. 纯大写英文的为专有名词，不要翻译
        3. 请结合上下文的语义语境进行翻译
        4. 不要输出任何方括号标记
        5. 不要添加任何解释、说明或思考过程
        6. 只返回纯翻译结果
        7. 目标语言为{target_lang}
        
        示例：
        输入："[前文: Hello] World [后文: Program]"
        输出："世界"
        
        输入："[前文: 你好] 世界 [后文: 程序]"
        输出："world"
        
        记住：方括号内的内容是上下文参考用于翻译前后的语义语境，不需要翻译和输出！
        """
    else:
        # 没有上下文的情况：使用原始提示词
        enhanced_prompt = prompt
    
    # 构建 message
    message = [
        {"role": "system", "content": enhanced_prompt.replace("{target_lang}", target_lang)},
        {"role": "user", "content": text}
    ]
    # print(openai.base_url)
    logging.info(message)
    # 禁用 OpenAI 的日志输出
    logging.getLogger("openai").setLevel(logging.WARNING)
    # 禁用 httpx 的日志输出
    logging.getLogger("httpx").setLevel(logging.WARNING)
    response = openai.chat.completions.create(
        model=model,  # 使用GPT-3.5版本
        messages=message,
        temperature=0.8
    )
    # for choices in response.choices:
    #     print(choices.message.content)
    content = response.choices[0].message.content
    # print(content)
    return content


def translate_html(html, target_lang, model, prompt):
    message = [
        {"role": "system",
         "content": "把下面的html翻译成{},只返回翻译后的内容".format(target_lang)},
        {"role": "user", "content": html}
    ]
    # print(openai.base_url)
    response = openai.chat.completions.create(
        model=model,
        messages=message
    )
    # for choices in response.choices:
    #     print(choices.message.content)
    content = response.choices[0].message.content
    return content


def get_content_by_image(base64_image, target_lang):
    # print(image_path)
    # file_object = openai.files.create(file=Path(image_path), purpose="这是一张图片")
    # print(file_object)
    message = [
        {"role": "system", "content": "你是一个图片ORC识别专家"},
        {"role": "user", "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": base64_image
                }
            },
            {
                "type": "text",
                # "text": "读取图片链接并提取其中的文本数据,只返回识别后的数据，将文本翻译成英文,并按照图片中的文字布局返回html。只包含body(不包含body本身)部分",
                # "text": f"提取图片中的所有文字数据，将提取的文本翻译成{target_lang},只返回原始文本和翻译结果",
                "text": f"提取图片中的所有文字数据,将提取的文本翻译成{target_lang},只返回翻译结果",
            }
        ]}
    ]
    # print(message)
    # print(openai.base_url)
    response = openai.chat.completions.create(
        model="gpt-4o",  # 使用GPT-3.5版本
        messages=message
    )
    # for choices in response.choices:
    #     print(choices.message.content)
    content = response.choices[0].message.content
    # return content
    # print(''.join(map(lambda x: f'<p>{x}</p>',content.split("\n"))))
    return ''.join(map(lambda x: f'<p>{x}</p>', content.split("\n")))


def check(model):
    try:
        message = [
            {"role": "system", "content": "你通晓世界所有语言,可以用来从一种语言翻译成另一种语言"},
            {"role": "user", "content": "你现在能翻译吗？"}
        ]
        response = openai.chat.completions.create(
            model=model,
            messages=message
        )
        return "OK"
    except openai.AuthenticationError as e:
        return "openai密钥或令牌无效"
    except openai.APIConnectionError as e:
        return "请求无法与openai服务器或建立安全连接"
    except openai.PermissionDeniedError as e:
        return "令牌额度不足"
    except openai.RateLimitError as e:
        return "访问速率达到限制,10分钟后再试"
    except openai.InternalServerError as e:
        return "当前分组上游负载已饱和，请稍后再试"
    except openai.APIStatusError as e:
        return e.response
    except Exception as e:
        return "当前无法完成翻译"


def process(texts, translate_id):
    total = 0
    complete = 0
    for text in texts:
        total += 1
        if text['complete']:
            complete += 1
    if total != complete:
        if (total != 0):
            process = format((complete / total) * 100, '.1f')
            db.execute("update translate set process=%s where id=%s", str(process), translate_id)


def complete(trans, text_count, spend_time):
    target_filesize = 1 #os.stat(trans['target_file']).st_size
    # 使用Python时区时间，与start_at保持一致
    from datetime import datetime
    import pytz
    end_time = datetime.now(pytz.timezone('Asia/Shanghai'))  # 使用东八区时区，与translate_service.py保持一致
    
    db.execute(
        "update translate set status='done',end_at=%s,process=100,target_filesize=%s,word_count=%s where id=%s",
        end_time, target_filesize, text_count, trans['id'])


def error(translate_id, message):
    # 使用Python时区时间，与start_at保持一致
    from datetime import datetime
    import pytz
    end_time = datetime.now(pytz.timezone('Asia/Shanghai'))  # 使用东八区时区，与translate_service.py保持一致
    
    db.execute(
        "update translate set failed_count=failed_count+1,status='failed',end_at=%s,failed_reason=%s where id=%s",
        end_time, message, translate_id)


def count_text(text):
    count = 0
    for char in text:
        if common.is_chinese(char):
            count += 1;
        elif char is None or char == " ":
            continue
        else:
            count += 0.5
    return count


def init_openai(url, key):
    openai.api_key = key
    if "v1" not in url:
        if url[-1] == "/":
            url += "v1/"
        else:
            url += "/v1/"
    openai.base_url = url


def check_translated(content):
    if content.startswith("Sorry, I cannot") or content.startswith(
            "I am sorry,") or content.startswith(
            "I'm sorry,") or content.startswith("Sorry, I can't") or content.startswith(
        "Sorry, I need more") or content.startswith("抱歉，无法") or content.startswith(
        "错误：提供的文本") or content.startswith("无法翻译") or content.startswith(
        "抱歉，我无法") or content.startswith(
        "对不起，我无法") or content.startswith("ご指示の内容は") or content.startswith(
        "申し訳ございません") or content.startswith("Простите，") or content.startswith(
        "Извините,") or content.startswith("Lo siento,"):
        return False
    else:
        return True


# def get_model_tokens(model,content):
#     encoding=tiktoken.encoding_for_model(model)
#     return en(encoding.encode(content))

def use_backup_model(trans, event, texts, index, message):
    if trans['backup_model'] != None and trans['backup_model'] != "":
        trans['model'] = trans['backup_model']
        trans['backup_model'] = ""
        get(trans, event, texts, index)
    else:
        if not event.is_set():
            error(trans['id'], message)
            print(message)
        event.set()


def clean_translation_result(text):
    """清理翻译结果，移除上下文标记"""
    import re
    
    # 移除上下文标记
    text = re.sub(r'\[前文:.*?\]', '', text)
    text = re.sub(r'\[后文:.*?\]', '', text)
    
    # 移除可能的解释性内容
    text = re.sub(r'翻译.*?[:：]\s*', '', text)
    text = re.sub(r'根据上下文.*?[:：]\s*', '', text)
    text = re.sub(r'答案是.*?[:：]\s*', '', text)
    text = re.sub(r'结果.*?[:：]\s*', '', text)
    text = re.sub(r'应该是.*?[:：]\s*', '', text)
    text = re.sub(r'输出.*?[:：]\s*', '', text)
    text = re.sub(r'输入.*?[:：]\s*', '', text)
    
    # 移除可能的思考过程
    text = re.sub(r'让我分析.*?[:：]\s*', '', text)
    text = re.sub(r'根据.*?[:：]\s*', '', text)
    text = re.sub(r'记住.*?[:：]\s*', '', text)
    
    # 清理多余的空格
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()