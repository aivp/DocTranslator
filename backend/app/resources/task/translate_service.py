import os
from datetime import datetime
from threading import Thread
from flask import current_app
from app.extensions import db
from app.models.translate import Translate
from app.models.comparison import Comparison, ComparisonSub
from app.models.prompt import Prompt
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

            # 启动线程时传递真实app对象和任务ID
            thr = Thread(
                target=self._async_wrapper,
                args=(self.app, self.task_id)
            )
            thr.start()
            return True
        except Exception as e:
            self.app.logger.error(f"任务初始化失败: {str(e)}", exc_info=True)
            return False

    def _async_wrapper(self, app, task_id):
        """异步执行包装器"""
        with app.app_context():
            from app.extensions import db  # 确保在每个线程中导入
            try:
                # 使用新会话获取任务对象
                task = db.session.query(Translate).get(task_id)
                if not task:
                    app.logger.error(f"任务 {task_id} 不存在")
                    return

                # 执行核心逻辑
                success = self._execute_core(task)
                self._complete_task(success)
            except Exception as e:
                app.logger.error(f"任务执行异常: {str(e)}", exc_info=True)
                self._complete_task(False)
            finally:
                db.session.remove()  # 清理线程局部session

    def _execute_core(self, task):
        """执行核心翻译逻辑"""
        try:
            # 初始化翻译配置
            self._init_translate_config(task)

            # 构建符合要求的 trans 字典
            trans_config = self._build_trans_config(task)

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

        # 验证文件存在性
        if not os.path.exists(task.origin_filepath):
            raise FileNotFoundError(f"原始文件不存在: {task.origin_filepath}")

        # 更新任务状态
        task.status = 'process'
        task.start_at = datetime.now(pytz.timezone(self.app.config['TIMEZONE']))  # 使用配置的东八区时区
        db.session.commit()
        return task

    def _build_trans_config(self, task):
        """构建符合文件处理器要求的 trans 字典"""
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
            'extension': os.path.splitext(task.origin_filepath)[1]  # 动态获取文件扩展名
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

    def _complete_task(self, success):
        """更新任务状态"""
        try:
            task = db.session.query(Translate).get(self.task_id)
            if task:
                task.status = 'done' if success else 'failed'
                task.end_at = datetime.now(pytz.timezone(self.app.config['TIMEZONE']))  # 使用配置的东八区时区
                task.process = 100.00 if success else 0.00
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            self.app.logger.error(f"状态更新失败: {str(e)}", exc_info=True)


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

