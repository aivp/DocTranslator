# -*- coding: utf-8 -*-
"""
任务管理器 - 用于追踪和取消正在运行的翻译任务
"""
import threading
from typing import Dict, Optional
from threading import Event

# 全局任务字典：{task_id: {'cancel_event': Event, 'pause_event': Event}}
_task_events: Dict[int, Dict[str, Event]] = {}
_task_lock = threading.Lock()


def register_task(task_id: int, cancel_event: Event) -> None:
    """
    注册翻译任务
    
    Args:
        task_id: 任务ID
        cancel_event: 用于控制任务取消的Event对象
    """
    with _task_lock:
        pause_event = Event()  # 创建暂停事件
        _task_events[task_id] = {
            'cancel_event': cancel_event,
            'pause_event': pause_event
        }


def unregister_task(task_id: int) -> None:
    """
    注销翻译任务并释放资源
    
    Args:
        task_id: 任务ID
    """
    with _task_lock:
        if task_id in _task_events:
            task_events = _task_events[task_id]
            # 清理事件对象
            if task_events:
                task_events['cancel_event'].clear()  # 清除取消事件状态
                task_events['pause_event'].clear()   # 清除暂停事件状态
            del _task_events[task_id]


def cancel_task(task_id: int) -> bool:
    """
    取消正在运行的翻译任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        bool: 是否成功取消任务
    """
    with _task_lock:
        if task_id in _task_events:
            task_events = _task_events[task_id]
            task_events['cancel_event'].set()  # 设置取消事件
            return True
        return False


def pause_task(task_id: int) -> bool:
    """
    暂停正在运行的翻译任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        bool: 是否成功暂停任务
    """
    with _task_lock:
        if task_id in _task_events:
            task_events = _task_events[task_id]
            task_events['pause_event'].set()  # 设置暂停事件
            return True
        return False


def resume_task(task_id: int) -> bool:
    """
    恢复暂停的翻译任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        bool: 是否成功恢复任务
    """
    with _task_lock:
        if task_id in _task_events:
            task_events = _task_events[task_id]
            task_events['pause_event'].clear()  # 清除暂停事件
            return True
        return False


def is_task_running(task_id: int) -> bool:
    """
    检查任务是否正在运行
    
    Args:
        task_id: 任务ID
        
    Returns:
        bool: 任务是否正在运行
    """
    with _task_lock:
        return task_id in _task_events


def get_task_event(task_id: int) -> Optional[Event]:
    """
    获取任务的取消Event对象
    
    Args:
        task_id: 任务ID
        
    Returns:
        Event: 任务的取消Event对象，如果任务不存在则返回None
    """
    with _task_lock:
        if task_id in _task_events:
            return _task_events[task_id]['cancel_event']
        return None


def get_task_pause_event(task_id: int) -> Optional[Event]:
    """
    获取任务的暂停Event对象
    
    Args:
        task_id: 任务ID
        
    Returns:
        Event: 任务的暂停Event对象，如果任务不存在则返回None
    """
    with _task_lock:
        if task_id in _task_events:
            return _task_events[task_id]['pause_event']
        return None


def get_running_tasks() -> list:
    """
    获取所有正在运行的任务信息列表
    
    Returns:
        list: 正在运行的任务信息列表，每个元素包含 {'task_id': int}
    """
    with _task_lock:
        return [{'task_id': task_id} for task_id in _task_events.keys()]

def is_any_task_running() -> bool:
    """
    检查是否有任何任务正在运行
    
    Returns:
        bool: 是否有任务正在运行
    """
    with _task_lock:
        return len(_task_events) > 0

