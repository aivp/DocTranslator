import threading
import openai
import os
import sys
import time
import getopt
from . import to_translate
from . import word
from . import excel
from . import powerpoint
from . import pdf

from . import txt
from . import csv_handle
from . import md
import pymysql
from . import db
from . import common
import traceback
from . import rediscon
import logging

# 当前正在执行的线程
run_threads=0

def main():
    global run_threads
    # 允许的最大线程
    max_threads=10
    # 当前执行的索引位置
    run_index=0
    # 是否保留原文
    keep_original=False
    # 要翻译的文件路径
    file_path=''
    # 翻译后的目标文件路径
    target_file=''
    uuid=sys.argv[1]
    storage_path=sys.argv[2]
    trans=db.get("select * from translate where uuid=%s", uuid)
    translate_id=trans['id']
    origin_filename=trans['origin_filename']
    origin_filepath=trans['origin_filepath']
    target_filepath=trans['target_filepath']
    api_key=trans['api_key']
    api_url=trans['api_url']
    comparison=get_comparison(trans['comparison_id'])
    prompt=get_prompt(trans['prompt_id'], comparison)
    if comparison:
        prompt = (
            "术语对照表:\n"
            f"{comparison}\n"
            "请按照以下规则进行翻译：\n"
            "1. 遇到术语时，请使用术语对照表中的对应翻译，无论翻译成什么语言。\n"
            "2. 未在术语对照表中的文本，请遵循翻译说明进行翻译。\n"
            "3. 确保翻译结果不包含原文或任何解释。\n"
            "翻译说明:\n"
            f"{prompt}"
        )
    trans['prompt']=prompt
    
    file_path=storage_path+origin_filepath
    target_file=storage_path+target_filepath

    origin_path_dir=os.path.dirname(file_path)
    target_path_dir=os.path.dirname(target_file)
    
    if not os.path.exists(origin_path_dir):
        os.makedirs(origin_path_dir, mode=0o777, exist_ok=True)

    if not os.path.exists(target_path_dir):
        os.makedirs(target_path_dir, mode=0o777, exist_ok=True)

    trans['file_path']=file_path
    trans['target_file']=target_file
    trans['storage_path']=storage_path
    trans['target_path_dir']=target_path_dir
    extension = origin_filename[origin_filename.rfind('.'):]
    trans['extension']=extension
    trans['run_complete']=True
    item_count=0
    spend_time=''
    try:
        status=True
        # 设置OpenAI API
        to_translate.init_openai(api_url, api_key)
        if extension=='.docx' or extension == '.doc':
            status=word.start(trans)
        elif extension=='.xls' or extension == '.xlsx':
            status=excel.start(trans)
        elif extension=='.ppt' or extension == '.pptx':
            status=powerpoint.start(trans)
        elif extension == '.pdf':
            # if pdf.is_scanned_pdf(trans['file_path']):
            #     status=gptpdf.start(trans)
            # else:
            status=pdf.start(trans)
        elif extension == '.txt':
            status=txt.start(trans)
        elif extension == '.csv':
            status=csv_handle.start(trans)
        elif extension == '.md':
            status=md.start(trans)
        if status:
            print("success")
            #before_active_count=threading.activeCount()
            #mredis.decr(api_url,threading_num-before_active_count)
            # print(item_count + ";" + spend_time)
        else:
            #before_active_count=threading.active_count()
            #mredis.decr(api_url,threading_num-before_active_count)
            logging.error("翻译出错了")
    except Exception as e:
        #before_active_count=threading.active_count()
        #mredis.decr(api_url,threading_num-before_active_count)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        line_number = exc_traceback.tb_lineno  # 异常抛出的具体行号
        logging.error(f"Error occurred on line: {line_number}")
        logging.error(f"Error details: {e}")

def get_prompt(prompt_id, comparison):
    # 确保prompt_id不为None，如果是None则设为0
    if prompt_id is None:
        prompt_id = 0
    else:
        prompt_id = int(prompt_id)
    
    if prompt_id > 0:
        prompt=db.get("select content from prompt where id=%s and deleted_flag='N'", prompt_id)
        if prompt and len(prompt['content'])>0:
            return prompt['content']

    prompt=db.get("select value from setting where `group`='other_setting' and alias='prompt'")
    return prompt['value']

def get_comparison(comparison_id):
    # 确保comparison_id不为None，如果是None则设为空字符串
    if comparison_id is None:
        comparison_id = ''
    else:
        comparison_id = str(comparison_id)
    
    if comparison_id and comparison_id.strip():
        # 支持多个术语库ID，逗号分隔
        comparison_ids = [int(id.strip()) for id in comparison_id.split(',') if id.strip().isdigit()]
        if comparison_ids:
            all_terms = {}  # 用于去重的字典
            
            for comp_id in comparison_ids:
                try:
                    # 从 comparison_sub 表获取术语数据 - 使用正确的查询方法
                    terms = db.get_all("select original, comparison_text from comparison_sub where comparison_sub_id=%s", comp_id)
                    
                    # 检查terms是否为有效结果
                    if terms and isinstance(terms, list) and len(terms) > 0:
                        logging.info(f"术语库 {comp_id} 找到 {len(terms)} 条术语")
                        
                        for term in terms:
                            if term and isinstance(term, dict) and term.get('original') and term.get('comparison_text'):
                                # 去重：如果原文已存在，跳过（以第一个为准）
                                if term['original'] not in all_terms:
                                    all_terms[term['original']] = term['comparison_text']
                                    logging.info(f"添加术语: {term['original']} -> {term['comparison_text']}")
                    else:
                        logging.warning(f"术语库 {comp_id} 未找到术语数据或查询结果为空")
                        
                except Exception as e:
                    logging.error(f"查询术语库 {comp_id} 时发生异常: {str(e)}")
                    continue
            
            # 拼接所有术语
            if all_terms:
                combined_terms = []
                for source, target in all_terms.items():
                    combined_terms.append(f"{source}: {target}")
                result = '\n'.join(combined_terms)
                # 添加日志，显示最终传入模型的术语表
                logging.info(f"任务使用术语表ID: {comparison_id}")
                logging.info(f"术语表内容: {list(all_terms.items())}")
                logging.info(f"总共合并了 {len(all_terms)} 条术语")
                return result
            else:
                logging.warning(f"任务术语表ID {comparison_id} 未找到内容")
                return None
        else:
            logging.warning(f"任务术语表ID格式无效: {comparison_id}")
            return None
    else:
        logging.info("任务未使用术语库")
        return None

if __name__ == '__main__':
    main()


