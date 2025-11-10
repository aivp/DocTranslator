import os
import uuid
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from flask import request, current_app
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.customer import Customer
from app.models.video_translate import VideoTranslate
from app.utils.response import APIResponse
from app.utils.token_checker import require_valid_token
from app.utils.akool_video import AkoolVideoService
from app.utils.tenant_helper import get_current_tenant_id
from app.utils.tenant_path import get_tenant_video_dir


class VideoUploadResource(Resource):
    """视频上传接口"""
    
    @require_valid_token
    @jwt_required()
    def post(self):
        """上传视频文件"""
        # 验证文件存在
        if 'file' not in request.files:
            return APIResponse.error('未选择文件', 400)
        
        file = request.files['file']
        
        # 验证文件名有效性
        if file.filename == '':
            return APIResponse.error('无效文件名', 400)
        
        # 验证文件类型
        if not self._allowed_file(file.filename):
            return APIResponse.error(
                f"仅支持以下视频格式：{', '.join(self._get_allowed_extensions())}", 400)
        
        # 验证文件大小
        file_size = request.content_length
        if file_size > self._get_max_file_size():
            return APIResponse.error(
                f"文件大小超过{self._get_max_file_size() // (1024 * 1024)}MB", 400)
        
        # 获取用户信息
        user_id = get_jwt_identity()
        customer = Customer.query.get(user_id)
        
        # 验证存储空间
        if customer.storage + file_size > customer.total_storage:
            return APIResponse.error('用户存储空间不足', 403)
        
        try:
            # 生成存储路径
            save_dir = self._get_upload_dir(user_id)
            original_filename = secure_filename(file.filename)
            
            # 生成唯一文件名：yyyyMMddhhmmss + 毫秒 + 扩展名
            ext = os.path.splitext(original_filename)[1]
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]  # 毫秒级时间戳
            unique_filename = f"{timestamp}{ext}"
            save_path = os.path.join(save_dir, unique_filename)
            
            # 检查路径是否安全
            if not self._is_safe_path(save_dir, save_path):
                return APIResponse.error('文件名包含非法字符', 400)
            
            # 保存文件
            file.save(save_path)
            
            # 计算文件MD5
            file_md5 = self._calculate_md5(save_path)
            
            # 生成视频访问URL
            video_url = self._generate_video_url(unique_filename, user_id)
            
            # 创建视频翻译记录
            tenant_id = get_current_tenant_id(user_id)
            
            video_record = VideoTranslate(
                customer_id=user_id,
                filename=unique_filename,
                original_filename=original_filename,
                filepath=os.path.abspath(save_path),
                video_url=video_url,
                file_size=file_size,
                created_at=datetime.utcnow()
            )
            
            # 设置租户ID
            if tenant_id:
                video_record.tenant_id = tenant_id
            
            db.session.add(video_record)
            
            # 更新用户存储空间
            customer.storage += file_size
            
            db.session.commit()
            
            return APIResponse.success({
                'id': video_record.id,
                'filename': unique_filename,
                'original_filename': original_filename,
                'file_size': file_size,
                'video_url': video_url,
                'message': '视频上传成功'
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"视频上传失败：{str(e)}")
            return APIResponse.error('视频上传失败', 500)
    
    @staticmethod
    def _allowed_file(filename):
        """验证文件类型是否允许"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in VideoUploadResource._get_allowed_extensions()
    
    @staticmethod
    def _get_allowed_extensions():
        """获取允许的视频格式"""
        return {'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm'}
    
    @staticmethod
    def _get_max_file_size():
        """获取最大文件大小"""
        return int(os.getenv('MAX_VIDEO_SIZE', 300)) * 1024 * 1024  # 300MB
    
    @staticmethod
    def _get_upload_dir(user_id):
        """获取视频上传目录（包含租户ID）"""
        # 使用租户路径工具
        return get_tenant_video_dir(user_id)
    
    @staticmethod
    def _calculate_md5(file_path):
        """计算文件MD5"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    @staticmethod
    def _is_safe_path(base_dir, file_path):
        """检查文件路径是否安全"""
        base_dir = Path(base_dir).resolve()
        file_path = Path(file_path).resolve()
        return file_path.is_relative_to(base_dir)
    
    @staticmethod
    def _generate_video_url(filename, user_id):
        """生成视频访问URL（包含租户ID）"""
        base_url = os.getenv('VIDEO_BASE_URL', 'https://yourdomain.com')
        # 获取租户ID
        tenant_id = get_current_tenant_id(user_id)
        if tenant_id is None:
            tenant_id = 1  # 默认租户
        
        # 生成包含租户ID、日期和用户ID目录的完整URL路径
        date_dir = datetime.now().strftime('%Y-%m-%d')
        return f"{base_url}/video/tenant_{tenant_id}/user_{user_id}/{date_dir}/{filename}"


class VideoTranslateResource(Resource):
    """视频翻译接口"""
    
    @require_valid_token
    @jwt_required()
    def post(self):
        """启动视频翻译（支持多语言和语音选择）"""
        # 支持JSON和表单数据
        if request.is_json:
            data = request.get_json()
        else:
            # 处理表单数据，包括数组格式
            form_data = request.form.to_dict()
            data = {}
            
            # 处理普通字段
            for key, value in form_data.items():
                if key == 'video_id':
                    data[key] = int(value)
                elif key == 'speaker_num':
                    data[key] = int(value)
                elif key == 'lipsync_enabled':
                    data[key] = value.lower() in ('true', '1', 'yes')
                elif key == 'lip_sync_type':
                    data[key] = int(value)
                elif key == 'dynamic_duration':
                    data[key] = value.lower() in ('true', '1', 'yes')
                elif not ('[' in key and ']' in key):  # 不是数组格式的字段
                    data[key] = value
            
            # 处理数组格式的字段
            target_languages = []
            voices_map = {}
            terminology_ids = []
            
            for key, value in form_data.items():
                if key.startswith('target_languages[') and key.endswith(']'):
                    target_languages.append(value)
                elif key.startswith('voices_map[') and key.endswith(']'):
                    # 提取语言代码
                    lang_code = key[11:-1]  # 去掉 'voices_map[' 和 ']'
                    voices_map[lang_code] = value
                elif key.startswith('terminology_ids[') and key.endswith(']'):
                    terminology_ids.append(value)
            
            # 设置处理后的数据
            if target_languages:
                data['target_languages'] = target_languages
            if voices_map:
                data['voices_map'] = voices_map
            if terminology_ids:
                data['terminology_ids'] = terminology_ids
        
        required_fields = ['video_id', 'source_language', 'target_languages']
        if not all(field in data for field in required_fields):
            current_app.logger.error(f"缺少必要参数，请求数据: {data}")
            return APIResponse.error('缺少必要参数', 400)
        
        # 处理目标语言（支持多语言）
        target_languages = data['target_languages']
        if isinstance(target_languages, str):
            target_languages = [target_languages]
        elif not isinstance(target_languages, list):
            return APIResponse.error('target_languages必须是字符串或数组', 400)
        
        # 处理术语库ID（支持多选）
        terminology_ids = data.get('terminology_ids', [])
        if isinstance(terminology_ids, str):
            terminology_ids = [terminology_ids] if terminology_ids else []
        elif not isinstance(terminology_ids, list):
            terminology_ids = []
        
        try:
            current_app.logger.info("开始处理翻译请求")
            current_app.logger.info("原始表单数据: {}".format(request.form.to_dict()))
            current_app.logger.info("解析后的数据: {}".format(data))
            current_app.logger.info("目标语言: {}".format(target_languages))
            current_app.logger.info("语音映射: {}".format(data.get('voices_map', {})))
            
            # 验证必要参数
            if not data.get('video_id'):
                current_app.logger.error("video_id参数为空")
                return APIResponse.error('video_id参数不能为空', 400)
            
            if not data.get('source_language'):
                current_app.logger.error("source_language参数为空")
                return APIResponse.error('source_language参数不能为空', 400)
            
            if not target_languages or len(target_languages) == 0:
                current_app.logger.error("target_languages参数为空")
                return APIResponse.error('target_languages参数不能为空', 400)
            
            # 查询视频记录
            user_id = get_jwt_identity()
            tenant_id = get_current_tenant_id(user_id)
            
            query = VideoTranslate.query.filter_by(
                id=data['video_id'],
                customer_id=user_id,
                deleted_flag='N'
            )
            if tenant_id:
                query = query.filter_by(tenant_id=tenant_id)
            
            video = query.first()
            
            if not video:
                current_app.logger.error(f"视频记录不存在，video_id: {data['video_id']}, customer_id: {user_id}")
                return APIResponse.error('视频记录不存在', 404)
            
            current_app.logger.info(f"找到视频记录: {video.id}, 状态: {video.status}")
            
            if video.status != 'uploaded':
                return APIResponse.error('视频状态不允许翻译', 400)
            
            # 检查是否已经存在相同的翻译任务
            query2 = VideoTranslate.query.filter_by(
                customer_id=user_id,
                video_url=video.video_url,
                source_language=data['source_language'],
                deleted_flag='N'
            )
            if tenant_id:
                query2 = query2.filter_by(tenant_id=tenant_id)
            
            existing_translations = query2.filter(
                VideoTranslate.target_language.in_(target_languages)
            ).all()
            
            if existing_translations:
                existing_langs = [t.target_language for t in existing_translations]
                current_app.logger.warning(f"已存在相同翻译任务: {existing_langs}")
                return APIResponse.error(f'已存在相同翻译任务: {", ".join(existing_langs)}', 400)
            
            # 检查队列状态
            from app.utils.video_queue_manager import video_queue_manager
            queue_status = video_queue_manager.get_queue_status()
            
            # 生成翻译组ID
            import uuid
            translation_group_id = str(uuid.uuid4())
            
            # 生成Webhook URL
            webhook_url = self._generate_webhook_url(video.id)
            
            # 准备语音映射
            voices_map = data.get('voices_map', {})
            
            # 计算可用槽位
            current_processing = queue_status['current_processing']
            slots_available = max(0, queue_status['max_concurrent'] - current_processing)
            languages_to_start = len(target_languages)
            
            # 初始化Akool服务（使用租户配置）
            current_app.logger.info(f"初始化Akool服务，租户ID: {tenant_id}")
            akool_service = AkoolVideoService(tenant_id=tenant_id)
            
            # 检查是否需要立即调用Akool API
            # 只有当有可用槽位时才调用API，否则直接创建queued记录
            if slots_available > 0:
                # 有可用槽位，调用Akool API创建任务
                current_app.logger.info("调用Akool API创建翻译任务")
                current_app.logger.info("视频URL: {}".format(video.video_url))
                current_app.logger.info("源语言: {}".format(data['source_language']))
                current_app.logger.info("目标语言: {}".format(target_languages))
                current_app.logger.info("语音映射: {}".format(voices_map))
                
                result = akool_service.create_translation(
                    video_url=video.video_url,
                    source_language=data['source_language'],
                    target_languages=target_languages,
                    lipsync=data.get('lipsync_enabled', False),
                    webhook_url=webhook_url,
                    speaker_num=data.get('speaker_num', 0),
                    voice_id=data.get('voice_id'),
                    voices_map=voices_map,
                    terminology_ids=terminology_ids,
                    style=data.get('style', 'professional'),
                    caption_type=data.get('caption_type', 0),
                    dynamic_duration=data.get('dynamic_duration', False)
                )
                
                # 处理Akool返回的结果
                akool_results = result.get('all_results', [])
                if not akool_results:
                    akool_data = result.get('data', {})
                    if akool_data:
                        akool_results = [{'code': 1000, 'data': akool_data}]
                    else:
                        akool_results = []
            else:
                # 没有可用槽位，不调用API，设置为queued状态
                current_app.logger.info(f"队列已满（{current_processing}/{queue_status['max_concurrent']}），任务将进入队列")
                akool_results = []
            
            created_videos = []
            started_count = 0
            
            # 为每个目标语言创建视频记录
            for i, target_lang in enumerate(target_languages):
                # 判断是否应该立即启动还是进入队列
                # 如果当前已处理的视频数+已启动的<最大并发数，则立即启动
                if (current_processing + started_count) < queue_status['max_concurrent']:
                    status = 'processing'
                    started_count += 1
                    # 只有processing状态的任务才有akool_task_id
                    akool_result = akool_results[i] if i < len(akool_results) else {}
                    akool_data = akool_result.get('data', {})
                    akool_task_id = akool_data.get('_id')
                else:
                    status = 'queued'
                    akool_task_id = None  # queued任务暂时没有akool_task_id
                
                new_video = VideoTranslate(
                    customer_id=video.customer_id,
                    filename=video.filename,
                    original_filename=video.original_filename,
                    filepath=video.filepath,
                    video_url=video.video_url,
                    source_language=data['source_language'],
                    target_language=target_lang,
                    akool_task_id=akool_task_id,
                    status=status,
                    lipsync_enabled=data.get('lipsync_enabled', False),
                    webhook_url=webhook_url,
                    file_size=video.file_size,
                    duration=video.duration,
                    voice_id=voices_map.get(target_lang) if voices_map else None,
                    voice_name=data.get('voice_name'),
                    voice_gender=data.get('voice_gender'),
                    voice_language=data.get('voice_language'),
                    voice_preview_url=data.get('voice_preview_url'),
                    lip_sync_type=data.get('lip_sync_type', 0),
                    parent_video_id=video.id,
                    translation_group_id=translation_group_id,
                    terminology_ids=json.dumps(terminology_ids) if terminology_ids else None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                # 设置租户ID（从原视频继承）
                if hasattr(video, 'tenant_id') and video.tenant_id:
                    new_video.tenant_id = video.tenant_id
                
                db.session.add(new_video)
                created_videos.append(new_video)
            
            # 更新原始视频记录状态
            # 如果有任何一个任务在处理，就标记为processing，否则标记为queued
            video.status = 'processing' if started_count > 0 else 'queued'
            video.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # 生成返回消息
            if started_count == languages_to_start:
                message = '已启动{}个语言的翻译任务'.format(languages_to_start)
                final_status = 'processing'
            elif started_count > 0:
                message = f'已启动{started_count}个语言，{languages_to_start - started_count}个已加入队列'
                final_status = 'partially_queued'
            else:
                message = f'当前系统资源紧张（{current_processing}/{queue_status["max_concurrent"]}），您的{languages_to_start}个任务已加入队列，将在资源释放后自动开始'
                final_status = 'queued'
            
            return APIResponse.success({
                'translation_group_id': translation_group_id,
                'created_videos': [v.id for v in created_videos],
                'target_languages': target_languages,
                'status': final_status,
                'message': message,
                'started_count': started_count,
                'queued_count': languages_to_start - started_count
            })
            
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            current_app.logger.error("启动视频翻译失败：{}".format(error_msg))
            
            # 检查是否是语音必选错误
            if 'voice_id is required' in error_msg or 'voices_map' in error_msg or 'This language' in error_msg:
                return APIResponse.error('某些语言必须选择AI语音，请为所有目标语言选择对应的AI语音', 400)
            
            # 检查是否是Akool认证问题
            if 'Akool认证信息未配置' in error_msg:
                return APIResponse.error('Akool认证信息未配置，请联系管理员', 500)
            
            # 检查是否是Akool API错误
            if 'Akool API错误' in error_msg or 'Akool' in error_msg:
                return APIResponse.error(f'Akool API错误: {error_msg}', 500)
            
            # 返回详细错误信息
            return APIResponse.error(f'启动翻译失败: {error_msg}', 500)
    
    @staticmethod
    def _generate_webhook_url(video_id):
        """生成Webhook URL"""
        base_url = os.getenv('WEBHOOK_BASE_URL', 'https://yourdomain.com')
        return f"{base_url}/api/video/webhook/{video_id}"


class VideoStatusResource(Resource):
    """视频状态查询接口"""
    
    @require_valid_token
    @jwt_required()
    def get(self, video_id):
        """查询视频翻译状态"""
        try:
            user_id = get_jwt_identity()
            tenant_id = get_current_tenant_id(user_id)
            
            query = VideoTranslate.query.filter_by(
                id=video_id,
                customer_id=user_id,
                deleted_flag='N'
            )
            if tenant_id:
                query = query.filter_by(tenant_id=tenant_id)
            
            video = query.first_or_404()
            
            # 如果正在处理中，查询Akool状态
            if video.status == 'processing' and video.akool_task_id:
                try:
                    # 使用租户配置初始化Akool服务
                    akool_service = AkoolVideoService(tenant_id=tenant_id)
                    akool_status = akool_service.get_task_status(video.akool_task_id)
                    
                    if akool_status:
                        video_status = akool_status.get('video_status')
                        if video_status == 3:  # completed
                            video.status = 'completed'
                            video.translated_video_url = akool_status.get('video', '')
                            video.expires_at = datetime.utcnow() + timedelta(days=7)
                        elif video_status == 4:  # failed
                            video.status = 'failed'
                            video.error_message = akool_status.get('error_message', '翻译失败')
                        
                        db.session.commit()
                except Exception as e:
                    current_app.logger.error(f"查询Akool状态失败：{str(e)}")
            
            status_info = video.get_status_info()
            
            return APIResponse.success({
                'video_id': video.id,
                'status': video.status,
                'status_info': status_info,
                'translated_video_url': video.translated_video_url,
                'expires_at': video.expires_at.isoformat() if video.expires_at else None
            })
            
        except Exception as e:
            current_app.logger.error(f"查询视频状态失败：{str(e)}")
            return APIResponse.error('查询状态失败', 500)


class VideoListResource(Resource):
    """视频列表接口"""
    
    @require_valid_token
    @jwt_required()
    def get(self):
        """获取用户视频列表"""
        try:
            user_id = get_jwt_identity()
            tenant_id = get_current_tenant_id(user_id)
            
            current_app.logger.info("获取视频列表请求，用户ID: {}".format(user_id))
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            status = request.args.get('status')
            current_app.logger.info("查询参数: page={}, per_page={}, status={}".format(page, per_page, status))
            
            query = VideoTranslate.query.filter_by(
                customer_id=user_id,
                deleted_flag='N'
            )
            if tenant_id:
                query = query.filter_by(tenant_id=tenant_id)
            
            query = query.filter(
                VideoTranslate.target_language.isnot(None)  # 只显示有目标语言的记录（翻译任务）
            )
            
            if status:
                query = query.filter_by(status=status)
            
            current_app.logger.info("执行查询: {}".format(query))
            videos = query.order_by(VideoTranslate.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            current_app.logger.info("查询结果: 总数={}, 当前页={}, 每页={}".format(videos.total, videos.page, videos.per_page))
            
            video_list = []
            for video in videos.items:
                try:
                    video_data = video.to_dict()
                    video_data['status_info'] = video.get_status_info()
                    video_list.append(video_data)
                    current_app.logger.info("处理视频记录: ID={}, 文件名={}".format(video.id, video.filename))
                except Exception as e:
                    current_app.logger.error("处理视频记录失败: ID={}, 错误={}".format(video.id, str(e)))
                    continue
            
            return APIResponse.success({
                'videos': video_list,
                'total': videos.total,
                'page': page,
                'per_page': per_page,
                'pages': videos.pages
            })
            
        except Exception as e:
            current_app.logger.error(f"获取视频列表失败：{str(e)}")
            return APIResponse.error('获取视频列表失败', 500)


class VideoDeleteResource(Resource):
    """视频删除接口"""
    
    @require_valid_token
    @jwt_required()
    def delete(self, video_id):
        """软删除视频"""
        try:
            user_id = get_jwt_identity()
            tenant_id = get_current_tenant_id(user_id)
            
            query = VideoTranslate.query.filter_by(
                id=video_id,
                customer_id=user_id,
                deleted_flag='N'
            )
            if tenant_id:
                query = query.filter_by(tenant_id=tenant_id)
            
            video = query.first_or_404()
            
            customer = Customer.query.get(user_id)
            
            # 记录删除前的存储空间
            old_storage = customer.storage
            file_size = video.file_size or 0
            
            # 软删除
            video.deleted_flag = 'Y'
            video.deleted_at = datetime.utcnow()
            
            # 更新用户存储空间
            customer.storage = max(0, customer.storage - file_size)
            
            db.session.commit()
            
            return APIResponse.success({
                'message': '删除成功',
                'storage_freed': file_size
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"删除视频失败：{str(e)}")
            return APIResponse.error('删除失败', 500)


class VideoDownloadResource(Resource):
    """视频下载代理接口"""
    
    @require_valid_token
    @jwt_required()
    def get(self, video_id):
        """代理下载视频文件"""
        try:
            user_id = get_jwt_identity()
            tenant_id = get_current_tenant_id(user_id)
            
            query = VideoTranslate.query.filter_by(
                id=video_id,
                customer_id=user_id,
                deleted_flag='N'
            )
            if tenant_id:
                query = query.filter_by(tenant_id=tenant_id)
            
            video = query.first_or_404()
            
            if not video.translated_video_url:
                return APIResponse.error('翻译视频不存在', 404)
            
            # 使用requests获取视频数据
            import requests
            response = requests.get(video.translated_video_url, stream=True)
            response.raise_for_status()
            
            # 设置响应头
            from flask import Response
            filename = video.original_filename or video.filename or 'translated_video.mp4'
            if not filename.endswith('.mp4'):
                filename += '.mp4'
            
            def generate():
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        yield chunk
            
            return Response(
                generate(),
                mimetype='video/mp4',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': 'video/mp4',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET',
                    'Access-Control-Allow-Headers': 'Authorization'
                }
            )
            
        except Exception as e:
            current_app.logger.error(f"下载视频失败：{str(e)}")
            return APIResponse.error('下载视频失败', 500)


class VideoLanguagesResource(Resource):
    """支持语言列表接口"""
    
    def get(self):
        """获取Akool支持的语言列表"""
        try:
            # 从JWT获取用户ID和租户ID（可选）
            tenant_id = None
            try:
                user_id = get_jwt_identity()
                current_app.logger.info(f"🔍 VideoLanguagesResource: user_id={user_id}")
                tenant_id = get_current_tenant_id(user_id)
                current_app.logger.info(f"🔍 VideoLanguagesResource: tenant_id={tenant_id}")
            except Exception as e:
                # 如果没有登录，使用默认租户
                current_app.logger.warning(f"⚠️ VideoLanguagesResource: 无法获取租户ID: {e}")
            
            if not tenant_id:
                current_app.logger.warning(f"⚠️ tenant_id为None，尝试使用租户ID=1")
                tenant_id = 1
            
            current_app.logger.info(f"🔍 VideoLanguagesResource: 最终使用 tenant_id={tenant_id}")
            
            # 使用租户配置初始化Akool服务
            akool_service = AkoolVideoService(tenant_id=tenant_id)
            languages = akool_service.get_languages()
            
            if not languages:
                current_app.logger.error("Akool API返回空的语言列表")
                return APIResponse.error('无法获取语言列表', 500)
            
            return APIResponse.success({
                'languages': languages
            })
            
        except Exception as e:
            current_app.logger.error(f"获取语言列表失败：{str(e)}")
            return APIResponse.error(f'获取语言列表失败: {str(e)}', 500)


class VideoVoicesResource(Resource):
    """AI语音列表接口"""
    
    def get(self):
        """获取AI语音列表"""
        try:
            # 获取查询参数
            language_code = request.args.get('language_code')
            page = request.args.get('page', 1, type=int)
            size = request.args.get('size', 100, type=int)
            
            # 从JWT获取用户ID和租户ID（可选）
            tenant_id = None
            try:
                user_id = get_jwt_identity()
                current_app.logger.info(f"🔍 VideoVoicesResource: user_id={user_id}")
                tenant_id = get_current_tenant_id(user_id)
                current_app.logger.info(f"🔍 VideoVoicesResource: tenant_id={tenant_id}")
            except Exception as e:
                # 如果没有登录，使用默认租户
                current_app.logger.warning(f"⚠️ VideoVoicesResource: 无法获取租户ID: {e}")
            
            if not tenant_id:
                current_app.logger.warning(f"⚠️ tenant_id为None，尝试使用租户ID=1")
                tenant_id = 1
            
            current_app.logger.info(f"🔍 VideoVoicesResource: 最终使用 tenant_id={tenant_id}")
            
            # 使用租户配置初始化Akool服务
            akool_service = AkoolVideoService(tenant_id=tenant_id)
            voices_data = akool_service.get_ai_voices(language_code, page, size)
            
            if voices_data:
                return APIResponse.success(voices_data)
            else:
                # 返回空结果而不是错误
                return APIResponse.success({
                    'page': page,
                    'size': size,
                    'count': 0,
                    'result': []
                })
            
        except Exception as e:
            current_app.logger.error(f"获取AI语音列表失败：{str(e)}")
            return APIResponse.error('获取AI语音列表失败', 500)


class VideoTokenInfoResource(Resource):
    """Token缓存信息接口"""
    
    def get(self):
        """获取当前token缓存状态"""
        try:
            token_info = AkoolVideoService.get_token_info()
            return APIResponse.success(token_info)
        except Exception as e:
            current_app.logger.error(f"获取token信息失败：{str(e)}")
            return APIResponse.error('获取token信息失败', 500)
    
    def delete(self):
        """清除token缓存"""
        try:
            AkoolVideoService.clear_token_cache()
            return APIResponse.success({'message': 'Token缓存已清除'})
        except Exception as e:
            current_app.logger.error(f"清除token缓存失败：{str(e)}")
            return APIResponse.error('清除token缓存失败', 500)


class VideoWebhookResource(Resource):
    """Webhook回调接口"""
    
    def post(self, video_id):
        """处理Akool回调"""
        try:
            data = request.get_json()
            current_app.logger.info(f"Webhook回调数据: {data}")
            
            if not data:
                return APIResponse.error('无效的请求数据', 400)
            
            # 检查是否是加密数据格式
            if 'dataEncrypt' in data:
                current_app.logger.info("检测到加密数据格式，尝试解密...")
                # TODO: 实现Akool数据解密逻辑
                # 目前先返回成功，避免重复回调
                return APIResponse.success({'message': 'Webhook received'})
            
            task_id = data.get('_id') or data.get('task_id')
            video_status = data.get('video_status')
            video_url = data.get('video') or data.get('translated_video_url')
            
            if not task_id:
                return APIResponse.error('缺少任务ID', 400)
            
            # 查找对应的视频记录
            video = VideoTranslate.query.filter_by(
                id=video_id,
                akool_task_id=task_id
            ).first()
            
            if not video:
                current_app.logger.warning(f"未找到视频ID {video_id} 和任务ID {task_id} 对应的视频记录")
                return APIResponse.error('视频记录不存在', 404)
            
            # 更新视频状态
            if video_status == 3:  # completed
                video.status = 'completed'
                video.translated_video_url = video_url
                video.expires_at = datetime.utcnow() + timedelta(days=7)
            elif video_status == 4:  # failed
                video.status = 'failed'
                video.error_message = data.get('error_message', '翻译失败')
            
            video.updated_at = datetime.utcnow()
            db.session.commit()
            
            current_app.logger.info(f"视频翻译任务 {task_id} 状态更新为 {video.status}")
            
            return APIResponse.success({'message': 'OK'})
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Webhook处理失败：{str(e)}")
            return APIResponse.error('处理失败', 500)
