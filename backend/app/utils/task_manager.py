# -*- coding: utf-8 -*-
"""
任务管理器 - 用于追踪和取消正在运行的翻译任务
"""
import threading
from typing import Dict, Optional
from threading import Event

# 全局任务字典：{task_id: event}
_task_events: Dict[int, Event] = {}
_task_lock = threading.Lock()


def register_task(task_id: int, event: Event) -> None:
    """
    注册翻译任务
    
    Args:
        task_id: 任务ID
        event: 用于控制任务取消的Event对象
    """
    with _task_lock:
        _task_events[task_id] = event


def unregister_task(task_id: int) -> None:
    """
    注销翻译任务并释放资源
    
    Args:
        task_id: 任务ID
    """
    with _task_lock:
        if task_id in _task_events:
            event = _task_events[task_id]
            # 清理事件对象
            if event:
                event.clear()  # 清除事件状态
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
            event = _task_events[task_id]
            event.set()  # 设置事件，通知所有线程停止
            # 注意：这里不删除事件，让任务完成时自己清理
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
    获取任务的Event对象
    
    Args:
        task_id: 任务ID
        
    Returns:
        Event: 任务的Event对象，如果任务不存在则返回None
    """
    with _task_lock:
        return _task_events.get(task_id)


def get_running_tasks() -> list:
    """
    获取所有正在运行的任务ID列表
    
    Returns:
        list: 正在运行的任务ID列表
    """
    with _task_lock:
        return list(_task_events.keys())

