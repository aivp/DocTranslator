import os
import uuid
import hashlib
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
            video_record = VideoTranslate(
                customer_id=user_id,
                filename=unique_filename,
                original_filename=original_filename,
                filepath=os.path.abspath(save_path),
                video_url=video_url,
                file_size=file_size,
                created_at=datetime.utcnow()
            )
            
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
        """获取视频上传目录"""
        base_dir = Path(current_app.config['UPLOAD_BASE_DIR'])
        upload_dir = base_dir / 'videos' / datetime.now().strftime('%Y-%m-%d') / str(user_id)
        
        if not upload_dir.exists():
            upload_dir.mkdir(parents=True, exist_ok=True)
        
        return str(upload_dir)
    
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
        """生成视频访问URL"""
        base_url = os.getenv('VIDEO_BASE_URL', 'https://yourdomain.com')
        # 生成包含日期和用户ID目录的完整URL路径
        date_dir = datetime.now().strftime('%Y-%m-%d')
        return f"{base_url}/videos/{date_dir}/{user_id}/{filename}"


class VideoTranslateResource(Resource):
    """视频翻译接口"""
    
    @require_valid_token
    @jwt_required()
    def post(self):
        """启动视频翻译"""
        # 支持JSON和表单数据
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
            # 转换字符串值为适当类型
            if 'video_id' in data:
                data['video_id'] = int(data['video_id'])
            if 'speaker_num' in data:
                data['speaker_num'] = int(data['speaker_num'])
            if 'lipsync_enabled' in data:
                data['lipsync_enabled'] = data['lipsync_enabled'].lower() in ('true', '1', 'yes')
        
        required_fields = ['video_id', 'source_language', 'target_language']
        if not all(field in data for field in required_fields):
            current_app.logger.error(f"缺少必要参数，请求数据: {data}")
            return APIResponse.error('缺少必要参数', 400)
        
        try:
            current_app.logger.info(f"开始处理翻译请求，数据: {data}")
            current_app.logger.info(f"请求头: {dict(request.headers)}")
            current_app.logger.info(f"请求方法: {request.method}")
            current_app.logger.info(f"Content-Type: {request.content_type}")
            
            # 查询视频记录
            video = VideoTranslate.query.filter_by(
                id=data['video_id'],
                customer_id=get_jwt_identity(),
                deleted_flag='N'
            ).first()
            
            if not video:
                current_app.logger.error(f"视频记录不存在，video_id: {data['video_id']}, customer_id: {get_jwt_identity()}")
                return APIResponse.error('视频记录不存在', 404)
            
            current_app.logger.info(f"找到视频记录: {video.id}, 状态: {video.status}")
            
            if video.status != 'uploaded':
                return APIResponse.error('视频状态不允许翻译', 400)
            
            # 初始化Akool服务
            client_id = os.getenv('CLIENT_ID') or os.getenv('AKOOL_CLIENT_ID') or os.getenv('client_Id')
            client_secret = os.getenv('CLIENT_SECRET') or os.getenv('AKOOL_CLIENT_SECRET') or os.getenv('client_Secret')
            if not client_id or not client_secret:
                return APIResponse.error('Akool认证信息未配置', 500)
            
            current_app.logger.info(f"初始化Akool服务，Client ID: {client_id[:10]}...")
            akool_service = AkoolVideoService(client_id, client_secret)
            
            # 生成Webhook URL
            webhook_url = self._generate_webhook_url(video.id)
            
            # 调用Akool API
            result = akool_service.create_translation(
                video_url=video.video_url,
                source_language=data['source_language'],
                target_language=data['target_language'],
                lipsync=data.get('lipsync_enabled', False),
                webhook_url=webhook_url,
                speaker_num=data.get('speaker_num', 0)
            )
            
            # 更新视频记录
            video.source_language = data['source_language']
            video.target_language = data['target_language']
            video.lipsync_enabled = data.get('lipsync_enabled', False)
            video.akool_task_id = result.get('_id')
            video.status = 'processing'
            video.webhook_url = webhook_url
            video.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return APIResponse.success({
                'video_id': video.id,
                'akool_task_id': video.akool_task_id,
                'status': video.status,
                'message': '翻译任务已启动'
            })
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"启动视频翻译失败：{str(e)}")
            return APIResponse.error('启动翻译失败', 500)
    
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
            video = VideoTranslate.query.filter_by(
                id=video_id,
                customer_id=get_jwt_identity(),
                deleted_flag='N'
            ).first_or_404()
            
            # 如果正在处理中，查询Akool状态
            if video.status == 'processing' and video.akool_task_id:
                try:
                    client_id = os.getenv('CLIENT_ID') or os.getenv('AKOOL_CLIENT_ID') or os.getenv('client_Id')
                    client_secret = os.getenv('CLIENT_SECRET') or os.getenv('AKOOL_CLIENT_SECRET') or os.getenv('client_Secret')
                    if client_id and client_secret:
                        akool_service = AkoolVideoService(client_id, client_secret)
                        akool_status = akool_service.get_task_status(video.akool_task_id)
                    else:
                        akool_status = None
                    
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
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            status = request.args.get('status')
            
            query = VideoTranslate.query.filter_by(
                customer_id=get_jwt_identity(),
                deleted_flag='N'
            )
            
            if status:
                query = query.filter_by(status=status)
            
            videos = query.order_by(VideoTranslate.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            video_list = []
            for video in videos.items:
                video_data = video.to_dict()
                video_data['status_info'] = video.get_status_info()
                video_list.append(video_data)
            
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
            video = VideoTranslate.query.filter_by(
                id=video_id,
                customer_id=get_jwt_identity(),
                deleted_flag='N'
            ).first_or_404()
            
            customer = Customer.query.get(get_jwt_identity())
            
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
            video = VideoTranslate.query.filter_by(
                id=video_id,
                customer_id=get_jwt_identity(),
                deleted_flag='N'
            ).first_or_404()
            
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
            # 检查Client ID和Client Secret是否存在
            client_id = os.getenv('CLIENT_ID') or os.getenv('AKOOL_CLIENT_ID') or os.getenv('client_Id')
            client_secret = os.getenv('CLIENT_SECRET') or os.getenv('AKOOL_CLIENT_SECRET') or os.getenv('client_Secret')
            if not client_id or not client_secret:
                current_app.logger.error("AKOOL_CLIENT_ID/AKOOL_CLIENT_SECRET, client_Id/client_Secret 或 CLIENT_ID/CLIENT_SECRET 环境变量未设置")
                return APIResponse.error('Akool认证信息未配置', 500)
            
            akool_service = AkoolVideoService(client_id, client_secret)
            languages = akool_service.get_languages()
            
            return APIResponse.success({
                'languages': languages
            })
            
        except ValueError as e:
            current_app.logger.error(f"认证信息配置错误：{str(e)}")
            # 返回默认语言列表
            return APIResponse.success({
                'languages': self._get_default_languages()
            })
        except Exception as e:
            current_app.logger.error(f"获取语言列表失败：{str(e)}")
            # 返回默认语言列表
            return APIResponse.success({
                'languages': self._get_default_languages()
            })
    
    def _get_default_languages(self):
        """获取默认语言列表"""
        return [
            {"lang_code": "en", "lang_name": "English"},
            {"lang_code": "zh", "lang_name": "Chinese (Simplified)"},
            {"lang_code": "ja", "lang_name": "Japanese"},
            {"lang_code": "ko", "lang_name": "Korean"},
            {"lang_code": "fr", "lang_name": "French"},
            {"lang_code": "de", "lang_name": "German"},
            {"lang_code": "es", "lang_name": "Spanish"},
            {"lang_code": "it", "lang_name": "Italian"},
            {"lang_code": "pt", "lang_name": "Portuguese"},
            {"lang_code": "ru", "lang_name": "Russian"},
            {"lang_code": "ar", "lang_name": "Arabic"},
            {"lang_code": "hi", "lang_name": "Hindi"},
            {"lang_code": "th", "lang_name": "Thai"},
            {"lang_code": "vi", "lang_name": "Vietnamese"},
            {"lang_code": "id", "lang_name": "Indonesian"},
            {"lang_code": "ms", "lang_name": "Malay"},
            {"lang_code": "tl", "lang_name": "Filipino"},
            {"lang_code": "tr", "lang_name": "Turkish"},
            {"lang_code": "pl", "lang_name": "Polish"},
            {"lang_code": "nl", "lang_name": "Dutch"}
        ]


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
