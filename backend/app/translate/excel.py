import threading
import openpyxl
from . import to_translate
from . import common
import os
import sys
import time
import datetime
import logging

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
    start_time = datetime.datetime.now()
    wb = None
    try:
        wb = openpyxl.load_workbook(trans['file_path']) 
        sheets = wb.get_sheet_names()
        texts=[]
        for sheet in sheets:
            ws = wb.get_sheet_by_name(sheet)
            read_row(ws.rows, texts)
        
        # print(texts)
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
                print(f"翻译进度: {completed_count}/{total_count} ({progress_percentage:.1f}%)")
                
                # 更新数据库进度
                try:
                    from .to_translate import db
                    db.execute("update translate set process=%s where id=%s", 
                             str(format(progress_percentage, '.1f')), 
                             trans['id'])
                    
                    # 如果进度达到100%，立即更新状态为已完成
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
        
        while run_index<=len(texts)-1:
            if threading.activeCount()<max_run+before_active_count:
                if not event.is_set():
                    thread = threading.Thread(target=to_translate.get, args=(trans, event, texts, run_index))
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
                print(f"翻译进度: {completed_count}/{total_count} ({progress_percentage:.1f}%)")
                
                # 更新数据库进度
                try:
                    from .to_translate import db
                    db.execute("update translate set process=%s where id=%s", 
                             str(format(progress_percentage, '.1f')), 
                             trans['id'])
                    
                except Exception as e:
                    print(f"更新进度失败: {str(e)}")
                
                last_completed_count = current_completed
            
            if complete:
                break
            else:
                time.sleep(1)

        text_count=0
        # print(texts)
        for sheet in sheets:
            ws = wb.get_sheet_by_name(sheet)
            text_count+=write_row(ws.rows, texts)

        wb.save(trans['target_file'])
        
        end_time = datetime.datetime.now()
        spend_time=common.display_spend(start_time, end_time)
        to_translate.complete(trans,text_count,spend_time)
        return True
    finally:
        # 确保Workbook被关闭以释放内存
        if wb is not None:
            try:
                wb.close()
                logger.info("Excel工作簿已关闭")
            except Exception as e:
                logger.warning(f"关闭Excel工作簿失败: {e}")


def read_row(rows,texts):
    for row in rows:
        text=""
        for cell in row:
            value=cell.value
            if value!=None and not common.is_all_punc(value):
                texts.append({"text":value, "complete":False})
        #         if text=="":
        #             text=value
        #         else:
        #             text=text+"\n"+value
        # if text!=None and not common.is_all_punc(text):
        #     texts.append({"text":text, "complete":False})

def write_row(rows, texts):
    text_count=0
    for row in rows:
        text=""
        for cell in row:
            value=cell.value
            if value!=None and not common.is_all_punc(value) and len(texts)>0:
                item=texts.pop(0)
                text_count+=item['count']
                cell.value=item['text']
        #         if text=="":
        #             text=value
        #         else:
        #             text=text+"\n"+value
        # if text!=None and not common.is_all_punc(text):
        #     item=texts.pop(0)
        #     values=item['text'].split("\n")
        #     text_count+=item['count']
        #     for cell in row:
        #         value=cell.value
        #         if value!=None and not common.is_all_punc(value):
        #             if len(values)>0:
        #                 cell.value=values.pop(0)
    return text_count



