# resources/file.py
import hashlib
import uuid
from werkzeug.utils import secure_filename
import os
from app.extensions import db
from app.models.customer import Customer
from app.models.translate import Translate
from app.utils.response import APIResponse
from pathlib import Path
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import request, current_app
from datetime import datetime
from app.utils.token_checker import require_valid_token
from app.utils.tenant_path import get_tenant_upload_dir


class FileUploadResource(Resource):
    @require_valid_token  # 先检查token
    @jwt_required()
    def post(self):
        """文件上传接口"""
        # 验证文件存在
        if 'file' not in request.files:
            return APIResponse.error('未选择文件', 400)
        file = request.files['file']

        # 验证文件名有效性
        if file.filename == '':
            return APIResponse.error('无效文件名', 400)

        # 验证文件类型
        if not self.allowed_file(file.filename):
            return APIResponse.error(
                f"仅支持以下格式：{', '.join(current_app.config['ALLOWED_EXTENSIONS'])}", 400)

        # 验证文件大小
        # if not self.validate_file_size(file.stream):
        #     return APIResponse.error(
        #         f"文件大小超过{current_app.config['MAX_FILE_SIZE'] // (1024 * 1024)}MB", 400)

        # 获取用户存储信息
        user_id = get_jwt_identity()
        customer = Customer.query.get(user_id)
        file_size = request.content_length  # 使用实际内容长度

        # 验证存储空间current_app.config['MAX_USER_STORAGE']
        if customer.storage + file_size > customer.total_storage:
            return APIResponse.error('用户存储空间不足', 403)

        try:
            # 生成存储路径（按租户ID和用户ID隔离）
            save_dir = get_tenant_upload_dir(user_id)
            original_filename = file.filename  # 保存用户上传的原始文件名
            filename = original_filename  # 用于实际存储的文件名

            # 检查同名文件是否存在，如果存在则生成唯一文件名避免覆盖
            original_save_path = os.path.join(save_dir, filename)
            
            # 如果同名文件存在，生成唯一文件名避免覆盖
            if os.path.exists(original_save_path):
                # 查询是否有使用该文件路径的翻译任务正在运行
                active_statuses = ['queued', 'changing', 'process']
                active_task = Translate.query.filter(
                    Translate.origin_filepath == os.path.abspath(original_save_path),
                    Translate.status.in_(active_statuses),
                    Translate.deleted_flag == 'N'
                ).first()
                
                # 生成唯一文件名避免覆盖（只修改实际存储的文件名，保留原始文件名）
                base_name, ext = os.path.splitext(filename)
                timestamp = int(datetime.now().timestamp() * 1000)  # 毫秒时间戳
                filename = f"{base_name}_{timestamp}{ext}"
                
                if active_task:
                    current_app.logger.warning(
                        f"检测到同名文件正在翻译，生成新文件名: {filename} (原文件: {original_filename})"
                    )
                else:
                    current_app.logger.info(
                        f"检测到同名文件已存在，生成新文件名避免覆盖: {filename} (原文件: {original_filename})"
                    )
            
            save_path = os.path.join(save_dir, filename)

            # 检查路径是否安全
            if not self.is_safe_path(save_dir, save_path):
                return APIResponse.error('文件名包含非法字符', 400)

            # 保存文件
            file.save(save_path)
            # 更新用户存储空间
            customer.storage += file_size
            db.session.commit()
            # 生成 UUID
            file_uuid = str(uuid.uuid4())
            # 计算文件的 MD5
            file_md5 = self.calculate_md5(save_path)

            # 创建翻译记录
            translate_record = Translate(
                translate_no=f"TRANS{datetime.now().strftime('%Y%m%d%H%M%S')}",
                uuid=file_uuid,
                customer_id=user_id,
                origin_filename=original_filename,  # 保存用户上传的原始文件名
                stored_filename=filename,  # 保存实际存储的文件名（如果重命名了，就是重命名后的）
                origin_filepath=os.path.abspath(save_path),  # 使用绝对路径（实际存储的文件路径）
                target_filepath='',  # 目标文件路径暂为空
                status='none',  # 初始状态为 none
                origin_filesize=file_size,
                size=file_size,
                md5=file_md5,
                created_at=datetime.utcnow()
            )
            db.session.add(translate_record)
            db.session.commit()

            # 返回响应，包含文件名、UUID 和翻译记录 ID
            return APIResponse.success({
                'filename': filename,
                'uuid': file_uuid,
                'translate_id': translate_record.id,
                'save_path': os.path.abspath(save_path)  # 返回绝对路径
            })

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"文件上传失败：{str(e)}")
            return APIResponse.error('文件上传失败', 500)

    @staticmethod
    def allowed_file(filename):
        # """验证文件类型是否允许"""
        # 文档格式
        DOCUMENT_EXTENSIONS = {'docx', 'xlsx','pdf', 'pptx', 'txt', 'md', 'csv', 'xls', 'doc'}
        # 图片格式（用于工具页面）
        IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
        # 合并所有允许的格式
        ALLOWED_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @staticmethod
    def validate_file_size(file_stream):
        """验证文件大小是否超过限制"""
        MAX_FILE_SIZE = current_app.config['MAX_FILE_SIZE']# 30 * 1024 * 1024  # 30MB
        file_stream.seek(0, os.SEEK_END)
        file_size = file_stream.tell()
        file_stream.seek(0)
        return file_size <= MAX_FILE_SIZE

    @staticmethod
    def get_upload_dir(user_id):
        """获取按租户ID和用户ID分类的上传目录（已废弃，使用get_tenant_upload_dir）"""
        # 兼容旧方法，调用新的租户路径工具
        return get_tenant_upload_dir(user_id)

    @staticmethod
    def calculate_md5(file_path):
        """计算文件的 MD5 值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def is_safe_path(base_dir, file_path):
        """检查文件路径是否安全，防止路径遍历攻击"""
        base_dir = Path(base_dir).resolve()
        file_path = Path(file_path).resolve()
        return file_path.is_relative_to(base_dir)



class FileDeleteResource(Resource):
    @require_valid_token  # 先检查token
    @jwt_required()
    def post(self):
        """文件删除接口[^1]"""
        data = request.form
        if 'uuid' not in data:
            return APIResponse.error('缺少必要参数', 400)

        try:
            user_id = get_jwt_identity()
            customer = Customer.query.get(user_id)
            
            # 根据 UUID 查询翻译记录
            translate_record = Translate.query.filter_by(uuid=data['uuid']).first()
            
            if translate_record:
                # 记录存在，正常删除流程
                file_path = translate_record.origin_filepath
                file_size = translate_record.origin_filesize or 0
                
                # 检查文件是否正在被翻译
                active_statuses = ['queued', 'changing', 'process']
                if translate_record.status in active_statuses:
                    return APIResponse.error(
                        f'文件正在翻译中（状态：{translate_record.status}），无法删除。请等待翻译完成后再删除。', 
                        400
                    )
                
                # 检查是否有其他任务正在使用该文件
                other_active_task = Translate.query.filter(
                    Translate.origin_filepath == file_path,
                    Translate.status.in_(active_statuses),
                    Translate.deleted_flag == 'N',
                    Translate.id != translate_record.id
                ).first()
                
                if other_active_task:
                    return APIResponse.error(
                        f'该文件正在被其他翻译任务使用（任务ID：{other_active_task.id}），无法删除。', 
                        400
                    )

                # 删除物理文件
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        current_app.logger.info(f"已删除物理文件：{file_path}")
                    except Exception as e:
                        current_app.logger.warning(f"删除物理文件失败：{file_path} - {e}")

                # 更新用户存储空间
                if file_size > 0:
                    customer.storage = max(0, customer.storage - file_size)

                # 删除数据库记录
                db.session.delete(translate_record)
                db.session.commit()
                
                return APIResponse.success(message='文件删除成功')
            else:
                # 记录不存在，可能是上传中删除的情况
                # 如果提供了 filepath，尝试删除物理文件
                file_path = data.get('filepath', '')
                
                if file_path and os.path.exists(file_path):
                    # 检查该文件是否正在被其他翻译任务使用
                    active_statuses = ['queued', 'changing', 'process']
                    active_task = Translate.query.filter(
                        Translate.origin_filepath == os.path.abspath(file_path),
                        Translate.status.in_(active_statuses),
                        Translate.deleted_flag == 'N'
                    ).first()
                    
                    if active_task:
                        return APIResponse.error(
                            f'该文件正在被翻译任务使用（任务ID：{active_task.id}），无法删除。', 
                            400
                        )
                    
                    try:
                        # 获取文件大小
                        file_size = os.path.getsize(file_path)
                        # 删除物理文件
                        os.remove(file_path)
                        current_app.logger.info(f"已删除物理文件（记录不存在）：{file_path}")
                        
                        # 更新用户存储空间
                        if file_size > 0:
                            customer.storage = max(0, customer.storage - file_size)
                            db.session.commit()
                        
                        return APIResponse.success(message='文件删除成功')
                    except Exception as e:
                        current_app.logger.warning(f"删除物理文件失败（记录不存在）：{file_path} - {e}")
                        # 即使删除失败，也返回成功，因为记录本身就不存在
                        return APIResponse.success(message='文件删除成功')
                else:
                    # 记录不存在且没有 filepath，可能是上传还没完成
                    # 返回成功，不报错
                    current_app.logger.info(f"删除请求：UUID {data['uuid']} 的记录不存在，可能是上传中删除")
                    return APIResponse.success(message='文件删除成功')

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"文件删除失败：{str(e)}", exc_info=True)
            return APIResponse.error('文件删除失败', 500)


