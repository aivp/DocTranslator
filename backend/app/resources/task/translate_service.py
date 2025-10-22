import os
from datetime import datetime
from threading import Thread, Event
from flask import current_app
from app.extensions import db
from app.models.translate import Translate
from app.models.comparison import Comparison, ComparisonSub
from app.models.prompt import Prompt
from app.utils.task_manager import register_task, unregister_task
from .main import main_wrapper
import pytz

# 时间修复
class TranslateEngine:
    def __init__(self, task_id):
        self.task_id = task_id
        self.app = current_app._get_current_object()  # 获取真实app对象

    def execute(self):
        """启动翻译任务入口"""
        try:
            # 在主线程上下文中准备任务
            with self.app.app_context():
                task = self._prepare_task()

            # 检查任务是否已经在运行（防止重复启动）
            from app.utils.task_manager import is_task_running
            if is_task_running(self.task_id):
                self.app.logger.warning(f"任务 {self.task_id} 已经在运行，跳过重复启动")
                return False

            # 创建用于控制任务取消的Event
            cancel_event = Event()
            
            # 注册任务到任务管理器
            register_task(self.task_id, cancel_event)
            self.app.logger.info(f"任务 {self.task_id} 已注册到任务管理器")

            # 启动线程时传递真实app对象、任务ID和取消事件
            thr = Thread(
                target=self._async_wrapper,
                args=(self.app, self.task_id, cancel_event),
                daemon=True  # 设置为守护线程，主进程退出时自动退出
            )
            thr.start()
            return True
        except Exception as e:
            self.app.logger.error(f"任务初始化失败: {str(e)}", exc_info=True)
            # 如果启动失败，确保任务状态更新为失败
            try:
                task = Translate.query.get(self.task_id)
                if task:
                    task.status = 'failed'
                    task.failed_reason = f'任务启动失败: {str(e)}'
                    db.session.commit()
            except:
                pass
            return False

    def _async_wrapper(self, app, task_id, cancel_event):
        """异步执行包装器"""
        with app.app_context():
            from app.extensions import db  # 确保在每个线程中导入
            try:
                # 使用新会话获取任务对象
                task = db.session.query(Translate).get(task_id)
                if not task:
                    app.logger.error(f"任务 {task_id} 不存在")
                    return

                # 执行核心逻辑，传递取消事件
                success = self._execute_core(task, cancel_event)
                # 只在任务真正完成时更新状态
                if success is not None:
                    self._complete_task(success)
            except Exception as e:
                app.logger.error(f"任务执行异常: {str(e)}", exc_info=True)
                # 异常时也更新状态为失败
                self._complete_task(False)
            finally:
                # 注销任务并释放资源
                unregister_task(task_id)
                app.logger.info(f"任务 {task_id} 已从任务管理器注销")
                
                # 释放内存
                import gc
                gc.collect()
                
                # 强制释放内存到操作系统
                try:
                    import ctypes
                    libc = ctypes.CDLL("libc.so.6")
                    libc.malloc_trim(0)
                    app.logger.info(f"🧹 任务 {task_id} 已调用malloc_trim释放内存")
                except Exception as e:
                    app.logger.debug(f"malloc_trim不可用: {e}")
                
                app.logger.debug(f"任务 {task_id} 内存已释放")
                
                db.session.remove()  # 清理线程局部session
    
    def _complete_task(self, success):
        """更新任务状态（只在任务真正完成或失败时调用）"""
        try:
            task = db.session.query(Translate).get(self.task_id)
            if task:
                # 检查当前状态，如果已经是 done 或 failed，不重复更新
                if task.status in ['done', 'failed']:
                    self.app.logger.info(f"任务 {self.task_id} 状态已经是 {task.status}，跳过更新")
                    return
                
                task.status = 'done' if success else 'failed'
                task.end_at = datetime.now(pytz.timezone(self.app.config['TIMEZONE']))  # 使用配置的东八区时区
                task.process = 100.00 if success else task.process  # 失败时保持当前进度
                db.session.commit()
                self.app.logger.info(f"任务 {self.task_id} 状态已更新为 {task.status}")
        except Exception as e:
            db.session.rollback()
            self.app.logger.error(f"状态更新失败: {str(e)}", exc_info=True)

    def _execute_core(self, task, cancel_event):
        """执行核心翻译逻辑"""
        try:
            # 初始化翻译配置
            self._init_translate_config(task)

            # 构建符合要求的 trans 字典
            trans_config = self._build_trans_config(task)
            
            # 将取消事件添加到配置中
            trans_config['cancel_event'] = cancel_event

            # 调用 main_wrapper 执行翻译
            return main_wrapper(task_id=task.id, config=trans_config,origin_path=task.origin_filepath)
        except Exception as e:
            current_app.logger.error(f"翻译执行失败: {str(e)}", exc_info=True)
            return False

    def _prepare_task(self):
        """准备翻译任务"""
        task = Translate.query.get(self.task_id)
        if not task:
            raise ValueError(f"任务 {self.task_id} 不存在")

        # 验证文件存在性和路径安全性
        if not os.path.exists(task.origin_filepath):
            raise FileNotFoundError(f"原始文件不存在: {task.origin_filepath}")
        
        # 防止路径遍历攻击 - 允许 /app/ 和 /workspace/ 路径
        abs_path = os.path.abspath(task.origin_filepath)
        if not (abs_path.startswith('/app/') or abs_path.startswith('/workspace/')):
            raise ValueError(f"文件路径不安全: {task.origin_filepath}")

        # 更新任务状态
        # PDF文件不在这里设置状态，由PDF翻译函数自己管理
        # 其他文件使用process状态
        if not task.origin_filepath.lower().endswith('.pdf'):
            task.status = 'process'    # 非PDF文件：进行中
        
        # 只有在start_at为空时才设置开始时间（避免覆盖队列设置的开始时间）
        if not task.start_at:
            task.start_at = datetime.now(pytz.timezone(self.app.config['TIMEZONE']))  # 使用配置的东八区时区
            self.app.logger.info(f"任务 {self.task_id} 开始时间已设置")
        
        # 提交状态更新
        db.session.commit()
        self.app.logger.info(f"任务 {self.task_id} 状态已更新为 {task.status}")
        
        return task

    def _build_trans_config(self, task):
        """构建符合文件处理器要求的 trans 字典"""
        # 添加调试日志，查看task.prompt_id的值
        current_app.logger.info(f"🔍 TranslateEngine 调试信息:")
        current_app.logger.info(f"  task.id: {task.id}")
        current_app.logger.info(f"  task.prompt_id类型: {type(task.prompt_id)}")
        current_app.logger.info(f"  task.prompt_id值: {repr(task.prompt_id)}")
        current_app.logger.info(f"  task.prompt_id是否为空: {not task.prompt_id}")
        
        config = {
            'id': task.id,  # 任务ID
            'target_lang': task.lang,
            'source_lang': task.origin_lang or 'zh',  # 源语言，默认为中文
            'uuid': task.uuid,
            'target_path_dir': os.path.dirname(task.target_filepath),
            'threads': task.threads,
            'file_path': task.origin_filepath,  # 原始文件绝对路径
            'target_file': task.target_filepath,  # 目标文件绝对路径
            'api_url': task.api_url,
            'api_key': task.api_key,  # 新增API密钥字段
            # 机器翻译相关
            'app_id':task.app_id,
            'app_key': task.app_key,
            'type': task.type,
            'lang': task.lang,
            'server': task.server,
            'run_complete': True,  # 默认设为True
            'prompt': task.prompt,
            'model': task.model,
            'backup_model': task.backup_model,
            'comparison_id': task.comparison_id,
            'prompt_id': task.prompt_id,
            'doc2x_api_key':task.doc2x_secret_key,
            'extension': os.path.splitext(task.origin_filepath)[1],  # 动态获取文件扩展名
            'pdf_translate_method': getattr(task, 'pdf_translate_method', None),  # PDF翻译方法
            'user_id': task.customer_id,  # 添加用户ID，用于文件隔离
            # 流式翻译配置
            'use_streaming': getattr(task, 'use_streaming', False),  # 是否启用流式翻译
            'streaming_chunk_size': getattr(task, 'streaming_chunk_size', 10)  # 流式翻译块大小
        }

        # 加载术语对照表（支持多个术语库，逗号分隔）
        if task.comparison_id and task.comparison_id != '':
            try:
                # 解析多个术语库ID
                comparison_ids = [int(id.strip()) for id in str(task.comparison_id).split(',') if id.strip().isdigit()]
                
                if comparison_ids:
                    # 获取所有术语库内容并拼接
                    combined_comparison = self.get_multiple_comparisons(comparison_ids)
                    if combined_comparison:
                        config['prompt'] = f"""
                            术语对照表如下:
                            {combined_comparison}
                            ---------------------
                            {config['prompt']}
                            """
                        # 添加日志，显示最终传入模型的术语表
                        self.app.logger.info(f"任务 {task.id} 使用术语表: {task.comparison_id}")
                    else:
                        self.app.logger.warning(f"任务 {task.id} 术语表ID {task.comparison_id} 未找到内容，跳过术语库")
                else:
                    self.app.logger.warning(f"任务 {task.id} 术语表ID格式无效: {task.comparison_id}，跳过术语库")
                
            except Exception as e:
                self.app.logger.error(f"任务 {task.id} 术语库处理异常: {str(e)}，跳过术语库")
                self.app.logger.info(f"任务 {task.id} 未使用术语表（异常跳过）")
        else:
            self.app.logger.info(f"任务 {task.id} 未使用术语表")


        return config

    def _init_translate_config(self, task):
        """初始化翻译配置"""
        if task.api_url and task.api_key:
            import openai
            openai.api_base = task.api_url
            openai.api_key = task.api_key

    def get_comparison(self, comparison_id):
        """
        加载术语对照表（单个ID，保持向后兼容）
        :param comparison_id: 术语对照表ID
        :return: 术语对照表内容
        """
        comparison = db.session.query(Comparison).filter_by(id=comparison_id).first()
        if comparison and comparison.content:
            return comparison.content.replace(',', ':').replace(';', '\n')
        return

    def get_multiple_comparisons(self, comparison_ids):
        """
        加载多个术语对照表并拼接（去重，以第一个为准）
        确保返回格式与 Qwen 模型的 tm_list 格式一致
        :param comparison_ids: 术语对照表ID列表
        :return: 拼接后的术语对照表内容
        """
        if not comparison_ids:
            return None
            
        all_terms = {}  # 用于去重的字典，key为原文，value为译文
        
        for comparison_id in comparison_ids:
            try:
                # 从 comparison_sub 表获取术语数据
                terms = db.session.query(ComparisonSub).filter_by(
                    comparison_sub_id=comparison_id
                ).order_by(ComparisonSub.id.desc()).all()
                
                if terms:
                    for term in terms:
                        if term.original and term.comparison_text:
                            # 去重：如果原文已存在，跳过（以第一个为准）
                            if term.original not in all_terms:
                                all_terms[term.original] = term.comparison_text
                else:
                    self.app.logger.warning(f"术语库 {comparison_id} 未找到术语数据")
                    
            except Exception as e:
                self.app.logger.error(f"查询术语库 {comparison_id} 时发生异常: {str(e)}")
                continue
        
        # 拼接所有术语 - 确保格式与 Qwen 模型的 tm_list 期望格式一致
        if all_terms:
            # Qwen 模型期望的格式是: "源术语:目标术语\n源术语2:目标术语2"
            # 这与单个术语库的 get_comparison 函数返回格式一致
            combined_terms = []
            for source, target in all_terms.items():
                # 使用与单个术语库完全相同的格式：source: target
                combined_terms.append(f"{source}: {target}")
            
            # 使用换行符连接，与单个术语库格式一致
            result = '\n'.join(combined_terms)
            
            return result
        
        return None


    def get_prompt(self,prompt_id):
        """
        加载提示词模板
        :param prompt_id: 提示词模板ID
        :return: 提示词内容
        """
        prompt = db.session.query(Prompt).filter_by(id=prompt_id).first()
        if prompt and prompt.content:
            return prompt.content
        return

