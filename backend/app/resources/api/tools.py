"""
工具相关API资源
"""
import os
import base64
import requests
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from io import BytesIO
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import request, current_app, send_file
from app.utils.response import APIResponse
from app.utils.token_checker import require_valid_token
from app.utils.api_key_helper import get_dashscope_key, get_current_tenant_id_from_request
from app.utils.tenant_path import get_tenant_upload_dir
from app.models.customer import Customer
from app.models.image_translate import ImageTranslate
from app.extensions import db


class ImageUploadResource(Resource):
    """图片上传资源 - 使用时间戳重命名"""
    
    @require_valid_token
    @jwt_required()
    def post(self):
        """图片上传接口"""
        try:
            # 验证文件存在
            if 'file' not in request.files:
                return APIResponse.error('未选择文件', 400)
            file = request.files['file']

            # 验证文件名有效性
            if file.filename == '':
                return APIResponse.error('无效文件名', 400)

            # 验证文件类型（只允许图片）
            allowed_extensions = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
            file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
            if file_ext not in allowed_extensions:
                return APIResponse.error(f'仅支持以下图片格式：{", ".join(allowed_extensions)}', 400)

            # 获取用户存储信息
            user_id = get_jwt_identity()
            tenant_id = get_current_tenant_id_from_request()
            customer = Customer.query.get(user_id)
            file_size = request.content_length or 0

            # 验证存储空间
            if customer.storage + file_size > customer.total_storage:
                return APIResponse.error('用户存储空间不足', 403)

            # 生成存储路径（按租户ID和用户ID隔离）
            save_dir = get_tenant_upload_dir(user_id, tenant_id)
            
            # 使用时间戳重命名文件
            timestamp = int(datetime.now().timestamp() * 1000)  # 毫秒时间戳
            file_ext = file.filename.rsplit('.', 1)[1].lower()
            new_filename = f"{timestamp}.{file_ext}"
            original_filename = file.filename
            
            save_path = os.path.join(save_dir, new_filename)

            # 检查路径是否安全
            if not self.is_safe_path(save_dir, save_path):
                return APIResponse.error('文件名包含非法字符', 400)

            # 保存文件（每次都创建新记录，允许用户用不同语言对翻译同一张图片）
            file.save(save_path)
            absolute_path = os.path.abspath(save_path)
            
            # 更新用户存储空间
            customer.storage += file_size
            
            # 创建图片翻译记录（状态为uploaded，等待翻译）
            image_record = ImageTranslate(
                customer_id=user_id,
                tenant_id=tenant_id or 1,
                filename=new_filename,
                original_filename=original_filename,
                filepath=absolute_path,
                file_size=file_size,
                source_language=None,  # 上传时还未选择语言
                target_language=None,  # 上传时还未选择语言
                status='uploaded',
                created_at=datetime.utcnow()
            )
            db.session.add(image_record)
            db.session.commit()
            
            # 返回响应（包含id）
            return APIResponse.success({
                'id': image_record.id,
                'filename': new_filename,
                'original_filename': original_filename,
                'name': original_filename,  # 前端用于匹配的字段
                'save_path': absolute_path,
                'file_size': file_size
            })

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"图片上传失败：{str(e)}")
            return APIResponse.error('图片上传失败', 500)
    
    @staticmethod
    def is_safe_path(base_dir, file_path):
        """检查文件路径是否安全，防止路径遍历攻击"""
        base_dir = Path(base_dir).resolve()
        file_path = Path(file_path).resolve()
        return file_path.is_relative_to(base_dir)


class ImageTranslateResource(Resource):
    """图片翻译资源 - 集成 Qwen-MT-Image（只提交任务，不等待结果）"""
    
    @require_valid_token
    @jwt_required()
    def post(self):
        """提交图片翻译任务"""
        try:
            # 获取JSON数据
            if not request.is_json:
                current_app.logger.error(f"请求Content-Type错误: {request.content_type}")
                return APIResponse.error('请求Content-Type必须是application/json', 415)
            
            data = request.get_json(silent=True)
            
            # 验证必要参数
            if not data:
                current_app.logger.error("请求参数为空或JSON解析失败")
                return APIResponse.error('请求参数不能为空或JSON格式错误', 400)
            
            image_id = data.get('image_id')
            source_language = data.get('source_language')
            target_language = data.get('target_language', 'zh')
            
            # 验证参数
            if not image_id:
                return APIResponse.error('缺少必要参数: image_id', 400)
            
            if not source_language:
                return APIResponse.error('源语言不能为空，请选择源语言', 400)
            
            if not target_language:
                return APIResponse.error('目标语言不能为空，请选择目标语言', 400)
            
            # 验证语言组合
            is_source_zh_or_en = source_language in ['zh', 'en']
            is_target_zh_or_en = target_language in ['zh', 'en']
            
            if not is_source_zh_or_en and not is_target_zh_or_en:
                return APIResponse.error(
                    '源语言和目标语言必须至少有一种是中文或英文。不支持在两个非中、英语种之间直接翻译（例如：从日语翻译为韩语）', 
                    400
                )
            
            # 获取用户ID和租户ID
            user_id = get_jwt_identity()
            tenant_id = get_current_tenant_id_from_request()
            
            # 查询图片记录
            image_record = ImageTranslate.query.filter_by(
                id=image_id,
                customer_id=user_id,
                deleted_flag='N'
            ).first()
            
            if not image_record:
                return APIResponse.error('图片记录不存在', 404)
            
            # 检查状态
            if image_record.status == 'translating':
                return APIResponse.error('翻译任务已提交，请等待完成', 400)
            
            if image_record.status == 'completed':
                return APIResponse.error('翻译任务已完成', 400)
            
            # 优先使用图片记录中的 tenant_id（上传时已设置），如果为空则使用请求中的 tenant_id
            # 这样可以确保使用正确的租户配置
            effective_tenant_id = image_record.tenant_id or tenant_id
            current_app.logger.info(f"图片翻译获取API Key: image_id={image_id}, image_record.tenant_id={image_record.tenant_id}, request_tenant_id={tenant_id}, effective_tenant_id={effective_tenant_id}")
            
            # 获取 DashScope API Key
            try:
                api_key = get_dashscope_key(effective_tenant_id)
            except ValueError as e:
                current_app.logger.error(f"获取API Key失败: {str(e)}")
                return APIResponse.error('未配置翻译服务API密钥，请联系管理员', 400)
            
            # 转换文件路径为URL
            image_url = image_record.filepath
            image_url_for_api = None
            if image_url.startswith('http://') or image_url.startswith('https://'):
                image_url_for_api = image_url
            else:
                image_url_for_api = self._convert_filepath_to_url(image_url)
                if not image_url_for_api:
                    return APIResponse.error('无法生成图片访问URL，请检查文件路径', 400)
            
            # 调用 Qwen-MT-Image API 创建任务（只提交，不等待结果）
            task_result = self._create_qwen_mt_image_task(api_key, image_url_for_api, source_language, target_language)
            
            if not task_result.get('success'):
                return APIResponse.error(task_result.get('error', '创建翻译任务失败'), 500)
            
            # 获取task_id
            task_id = task_result.get('task_id')
            if not task_id:
                return APIResponse.error('未获取到任务ID', 500)
            
            # 更新数据库记录：保存task_id，状态改为translating
            image_record.status = 'translating'
            image_record.source_language = source_language
            image_record.target_language = target_language
            image_record.qwen_task_id = task_id
            db.session.commit()
            
            # 立即返回，不等待结果
            return APIResponse.success({
                'image_id': image_record.id,
                'task_id': task_id,
                'status': 'translating',
                'message': '翻译任务已提交，请稍后查询结果'
            })
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"提交图片翻译任务失败: {str(e)}")
            return APIResponse.error(f'提交翻译任务失败: {str(e)}', 500)
    
    def _create_qwen_mt_image_task(self, api_key, image_url, source_language, target_language):
        """
        创建 Qwen-MT-Image 翻译任务（只提交，不等待结果）
        
        Args:
            api_key: DashScope API Key
            image_url: 图片URL（必须是公网可访问的URL）
            source_language: 源语言代码
            target_language: 目标语言代码
            
        Returns:
            dict: 包含task_id的字典
        """
        try:
            api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis"
            
            input_params = {
                "image_url": image_url,
                "source_lang": source_language,
                "target_lang": target_language
            }
            
            payload = {
                "model": "qwen-mt-image",
                "input": input_params
            }
            
            current_app.logger.info(f"创建Qwen-MT-Image翻译任务: source_lang={source_language}, target_lang={target_language}, image_url={image_url}")
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable"  # 启用异步模式
            }
            
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                current_app.logger.info(f"Qwen-MT-Image API响应: {result}")
                
                # 获取task_id
                task_id = result.get('task_id') or result.get('output', {}).get('task_id')
                
                if task_id:
                    return {
                        'success': True,
                        'task_id': task_id
                    }
                else:
                    current_app.logger.error(f"未找到task_id，响应: {result}")
                    return {
                        'success': False,
                        'error': 'API返回格式异常，未找到task_id'
                    }
            else:
                error_msg = f"API请求失败: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message') or error_data.get('error') or error_msg
                    current_app.logger.error(f"Qwen-MT-Image API错误响应: {error_data}")
                except:
                    error_msg = response.text or error_msg
                    current_app.logger.error(f"Qwen-MT-Image API错误: {error_msg}")
                
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': '请求超时，请稍后重试'
            }
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"API请求异常: {str(e)}")
            return {
                'success': False,
                'error': f'网络请求失败: {str(e)}'
            }
        except Exception as e:
            current_app.logger.error(f"创建Qwen-MT-Image任务异常: {str(e)}")
            return {
                'success': False,
                'error': f'创建任务失败: {str(e)}'
            }
    
    def _convert_filepath_to_url(self, filepath):
        """
        将本地文件路径转换为公网可访问的URL
        参考视频翻译的实现，使用VIDEO_BASE_URL环境变量
        """
        try:
            # 使用VIDEO_BASE_URL环境变量（与视频翻译保持一致，包含端口号）
            base_url = os.getenv('VIDEO_BASE_URL', 'http://localhost:1475')
            
            path_str = filepath.replace('\\', '/')
            if '/uploads/' in path_str:
                relative_path = path_str.split('/uploads/', 1)[1]
                image_url = f"{base_url}/uploads/{relative_path}"
                current_app.logger.info(f"转换文件路径为URL: {filepath} -> {image_url}")
                return image_url
            elif 'uploads' in path_str:
                idx = path_str.find('uploads')
                relative_path = path_str[idx:]
                image_url = f"{base_url}/{relative_path}"
                current_app.logger.info(f"转换文件路径为URL: {filepath} -> {image_url}")
                return image_url
            else:
                current_app.logger.error(f"无法从文件路径提取相对路径: {filepath}")
                return None
                
        except Exception as e:
            current_app.logger.error(f"转换文件路径为URL失败: {str(e)}")
            return None


class ImageTranslateBatchResource(Resource):
    """图片批量翻译资源 - 后端控制并发和延迟，避免触发API速率限制"""

    @require_valid_token
    @jwt_required()
    def post(self):
        """批量提交图片翻译任务"""
        try:
            if not request.is_json:
                return APIResponse.error('请求Content-Type必须是application/json', 415)

            data = request.get_json(silent=True)
            if not data:
                return APIResponse.error('请求参数不能为空或JSON格式错误', 400)

            image_ids = data.get('image_ids', [])
            source_language = data.get('source_language')
            target_language = data.get('target_language', 'zh')

            if not image_ids or not isinstance(image_ids, list):
                return APIResponse.error('缺少必要参数: image_ids（数组）', 400)

            if not source_language:
                return APIResponse.error('源语言不能为空，请选择源语言', 400)

            if not target_language:
                return APIResponse.error('目标语言不能为空，请选择目标语言', 400)

            # 验证语言组合
            is_source_zh_or_en = source_language in ['zh', 'en']
            is_target_zh_or_en = target_language in ['zh', 'en']
            if not is_source_zh_or_en and not is_target_zh_or_en:
                return APIResponse.error(
                    '源语言和目标语言必须至少有一种是中文或英文。不支持在两个非中、英语种之间直接翻译（例如：从日语翻译为韩语）',
                    400
                )

            user_id = get_jwt_identity()
            tenant_id = get_current_tenant_id_from_request()

            # 查询所有图片记录
            image_records = ImageTranslate.query.filter(
                ImageTranslate.id.in_(image_ids),
                ImageTranslate.customer_id == user_id,
                ImageTranslate.deleted_flag == 'N'
            ).all()

            # 检查是否有记录不存在
            found_ids = {record.id for record in image_records}
            missing_ids = set(image_ids) - found_ids
            if missing_ids:
                return APIResponse.error(f'部分图片记录不存在或不属于当前用户: {missing_ids}', 404)

            # 将任务加入队列（更新状态为uploaded，设置语言，由队列管理器异步处理）
            results = []
            records_to_update = []

            for image_record in image_records:
                # 检查状态
                if image_record.status == 'translating':
                    results.append({
                        'image_id': image_record.id,
                        'success': False,
                        'error': '翻译任务已提交，请等待完成'
                    })
                    continue

                if image_record.status == 'completed':
                    results.append({
                        'image_id': image_record.id,
                        'success': False,
                        'error': '翻译任务已完成'
                    })
                    continue

                # 更新记录：设置语言，状态保持为uploaded（队列管理器会处理）
                image_record.source_language = source_language
                image_record.target_language = target_language
                # 状态保持为uploaded，队列管理器会将其改为translating
                records_to_update.append(image_record)
                results.append({
                    'image_id': image_record.id,
                    'success': True,
                    'message': '任务已加入队列，等待处理'
                })

            # 统一提交所有更新的记录
            try:
                if records_to_update:
                    db.session.commit()
                    current_app.logger.info(f"批量提交翻译任务：{len(records_to_update)}个任务已加入队列")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"批量提交翻译任务时数据库提交失败: {str(e)}", exc_info=True)
                return APIResponse.error('数据库提交失败', 500)

            # 统计结果
            success_count = sum(1 for r in results if r.get('success'))
            failed_count = len(results) - success_count

            return APIResponse.success({
                'total': len(results),
                'success_count': success_count,
                'failed_count': failed_count,
                'results': results,
                'message': f'{success_count}个任务已加入队列，等待处理（最多同时处理20个，间隔1秒）'
            })

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"批量提交图片翻译任务失败: {str(e)}")
            return APIResponse.error(f'批量提交翻译任务失败: {str(e)}', 500)

    def _convert_filepath_to_url(self, filepath):
        """将本地文件路径转换为公网可访问的URL（复用ImageTranslateResource的方法）"""
        try:
            base_url = os.getenv('VIDEO_BASE_URL', 'http://localhost:1475')
            path_str = filepath.replace('\\', '/')
            if '/uploads/' in path_str:
                relative_path = path_str.split('/uploads/', 1)[1]
                image_url = f"{base_url}/uploads/{relative_path}"
                return image_url
            elif 'uploads' in path_str:
                idx = path_str.find('uploads')
                relative_path = path_str[idx:]
                image_url = f"{base_url}/{relative_path}"
                return image_url
            else:
                current_app.logger.error(f"无法从文件路径提取相对路径: {filepath}")
                return None
        except Exception as e:
            current_app.logger.error(f"转换文件路径为URL失败: {str(e)}")
            return None

    def _create_qwen_mt_image_task(self, api_key, image_url, source_language, target_language):
        """创建 Qwen-MT-Image 翻译任务（复用ImageTranslateResource的方法）"""
        try:
            api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image2image/image-synthesis"
            input_params = {
                "image_url": image_url,
                "source_lang": source_language,
                "target_lang": target_language
            }
            payload = {
                "model": "qwen-mt-image",
                "input": input_params
            }
            current_app.logger.info(f"创建Qwen-MT-Image翻译任务: source_lang={source_language}, target_lang={target_language}, image_url={image_url}")
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-DashScope-Async": "enable"
            }
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                result = response.json()
                current_app.logger.info(f"Qwen-MT-Image API响应: {result}")
                task_id = result.get('task_id') or result.get('output', {}).get('task_id')
                if task_id:
                    return {'success': True, 'task_id': task_id}
                else:
                    current_app.logger.error(f"未找到task_id，响应: {result}")
                    return {'success': False, 'error': 'API返回格式异常，未找到task_id'}
            else:
                error_msg = f"API请求失败: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message') or error_data.get('error') or error_msg
                    current_app.logger.error(f"Qwen-MT-Image API错误响应: {error_data}")
                except:
                    error_msg = response.text or error_msg
                    current_app.logger.error(f"Qwen-MT-Image API错误: {error_msg}")
                return {'success': False, 'error': error_msg}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': '请求超时，请稍后重试'}
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"API请求异常: {str(e)}")
            return {'success': False, 'error': f'网络请求失败: {str(e)}'}
        except Exception as e:
            current_app.logger.error(f"创建Qwen-MT-Image任务异常: {str(e)}")
            return {'success': False, 'error': f'创建任务失败: {str(e)}'}


class ImageTranslateStatusResource(Resource):
    """图片翻译状态查询资源"""
    
    @require_valid_token
    @jwt_required()
    def get(self, image_id):
        """查询图片翻译状态"""
        try:
            user_id = get_jwt_identity()
            tenant_id = get_current_tenant_id_from_request()
            
            # 查询图片记录
            image_record = ImageTranslate.query.filter_by(
                id=image_id,
                customer_id=user_id,
                deleted_flag='N'
            ).first()
            
            if not image_record:
                return APIResponse.error('图片记录不存在', 404)
            
            # 如果正在翻译中，查询Qwen API状态
            if image_record.status == 'translating' and image_record.qwen_task_id:
                try:
                    # 优先使用图片记录中的 tenant_id
                    effective_tenant_id = image_record.tenant_id or tenant_id
                    current_app.logger.info(f"查询图片翻译状态获取API Key: image_id={image_id}, image_record.tenant_id={image_record.tenant_id}, request_tenant_id={tenant_id}, effective_tenant_id={effective_tenant_id}")
                    api_key = get_dashscope_key(effective_tenant_id)
                    qwen_status = self._query_qwen_task_status(api_key, image_record.qwen_task_id)
                    
                    if qwen_status.get('success'):
                        task_status = qwen_status.get('task_status')
                        
                        # 根据API文档，task_status的可能值：
                        # PENDING: 任务排队中
                        # RUNNING: 任务处理中
                        # SUCCEEDED: 任务执行成功
                        # FAILED: 任务执行失败
                        # CANCELED: 任务已取消
                        # UNKNOWN: 任务不存在或状态未知
                        
                        if task_status == 'SUCCEEDED':
                            # 任务成功完成
                            output = qwen_status.get('output', {})
                            # 根据文档，成功后会返回url字段（24小时有效）
                            translated_image_url = output.get('url') or output.get('image_url')
                            
                            # 更新数据库
                            image_record.status = 'completed'
                            image_record.translated_image_url = translated_image_url
                            # 如果有文本结果，也保存
                            image_record.original_text = output.get('original_text', '')
                            image_record.translated_text = output.get('translated_text', '')
                            image_record.detected_language = output.get('detected_language', '')
                            db.session.commit()
                        elif task_status == 'FAILED':
                            # 任务失败
                            output = qwen_status.get('output', {})
                            # 从output中获取错误信息（Qwen API的错误信息在output.message中）
                            error_msg = output.get('message') or output.get('code') or qwen_status.get('error_message', '翻译失败')
                            # 如果错误信息包含code，组合显示
                            if output.get('code') and output.get('message'):
                                error_msg = f"{output.get('code')}: {output.get('message')}"
                            elif output.get('code'):
                                error_msg = output.get('code')
                            elif output.get('message'):
                                error_msg = output.get('message')
                            
                            image_record.status = 'failed'
                            image_record.error_message = error_msg
                            db.session.commit()
                            current_app.logger.error(f"图片翻译任务失败: image_id={image_record.id}, task_id={image_record.qwen_task_id}, error={error_msg}, output={output}")
                        elif task_status == 'CANCELED':
                            # 任务已取消
                            image_record.status = 'failed'
                            image_record.error_message = '任务已取消'
                            db.session.commit()
                        elif task_status == 'UNKNOWN':
                            # 任务不存在或已过期（超过24小时）
                            image_record.status = 'failed'
                            image_record.error_message = '任务不存在或已过期（超过24小时）'
                            db.session.commit()
                        # 如果状态是PENDING或RUNNING，保持translating状态，继续轮询
                        
                except Exception as e:
                    current_app.logger.error(f"查询Qwen任务状态失败：{str(e)}")
                    # 查询失败不影响返回当前状态
            
            # 返回状态信息
            return APIResponse.success({
                'image_id': image_record.id,
                'status': image_record.status,
                'source_language': image_record.source_language,
                'target_language': image_record.target_language,
                'detected_language': image_record.detected_language,
                'original_text': image_record.original_text,
                'translated_text': image_record.translated_text,
                'translated_image_url': image_record.translated_image_url,
                'error_message': image_record.error_message,
                'created_at': image_record.created_at.isoformat() if image_record.created_at else None,
                'updated_at': image_record.updated_at.isoformat() if image_record.updated_at else None
            })
            
        except Exception as e:
            current_app.logger.error(f"查询图片翻译状态失败: {str(e)}")
            return APIResponse.error('查询状态失败', 500)
    
    def _query_qwen_task_status(self, api_key, task_id):
        """
        查询Qwen API任务状态
        
        Args:
            api_key: DashScope API Key
            task_id: Qwen API返回的任务ID
            
        Returns:
            dict: 任务状态信息
        """
        try:
            api_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                # 根据API文档，task_status在output字段中
                output = result.get('output', {})
                task_status = output.get('task_status')
                
                current_app.logger.info(f"查询Qwen任务状态: task_id={task_id}, task_status={task_status}, 完整响应: {result}")
                
                # 返回状态信息
                error_message = None
                if task_status == 'FAILED':
                    # 失败时，错误信息在output.message或output.code中
                    if output.get('message'):
                        error_message = output.get('message')
                    elif output.get('code'):
                        error_message = output.get('code')
                    # 如果有code和message，组合显示
                    if output.get('code') and output.get('message'):
                        error_message = f"{output.get('code')}: {output.get('message')}"
                
                return {
                    'success': True,
                    'task_status': task_status,
                    'output': output,
                    'error_message': error_message or result.get('message') or result.get('error')
                }
            else:
                error_msg = f"查询任务状态失败: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message') or error_msg
                except:
                    error_msg = response.text or error_msg
                
                current_app.logger.error(f"查询Qwen任务状态失败: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"查询Qwen任务状态异常: {str(e)}")
            return {
                'success': False,
                'error': f'网络请求失败: {str(e)}'
            }
        except Exception as e:
            current_app.logger.error(f"查询Qwen任务状态异常: {str(e)}")
            return {
                'success': False,
                'error': f'查询失败: {str(e)}'
            }


class ImageListResource(Resource):
    """图片列表资源"""
    
    @require_valid_token
    @jwt_required()
    def get(self):
        """获取图片翻译列表"""
        try:
            user_id = get_jwt_identity()
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 20, type=int)
            status = request.args.get('status')  # 可选：按状态筛选
            
            # 构建查询
            query = ImageTranslate.query.filter_by(
                customer_id=user_id,
                deleted_flag='N'
            )
            
            # 状态筛选
            if status:
                query = query.filter_by(status=status)
            
            # 排序：最新的在前
            query = query.order_by(ImageTranslate.created_at.desc())
            
            # 分页
            pagination = query.paginate(page=page, per_page=limit, error_out=False)
            
            # 转换为字典列表，并添加过期标记
            images = []
            now = datetime.utcnow()
            for img in pagination.items:
                img_dict = img.to_dict()
                # 检查是否超过24小时
                if img.created_at:
                    time_diff = (now - img.created_at).total_seconds()
                    img_dict['is_expired'] = time_diff > 24 * 60 * 60  # 24小时
                else:
                    img_dict['is_expired'] = False
                images.append(img_dict)
            
            return APIResponse.success({
                'data': images,
                'total': pagination.total,
                'page': page,
                'limit': limit,
                'pages': pagination.pages
            })
            
        except Exception as e:
            current_app.logger.error(f"获取图片列表失败: {str(e)}")
            return APIResponse.error('获取图片列表失败', 500)


class ImageDeleteResource(Resource):
    """图片删除资源"""
    
    @require_valid_token
    @jwt_required()
    def delete(self, image_id):
        """删除图片翻译记录"""
        try:
            user_id = get_jwt_identity()
            image_record = ImageTranslate.query.filter_by(
                id=image_id,
                customer_id=user_id,
                deleted_flag='N'
            ).first()

            if not image_record:
                return APIResponse.error('图片记录不存在', 404)

            try:
                # 删除物理文件
                if os.path.exists(image_record.filepath):
                    os.remove(image_record.filepath)
                    # 更新用户存储空间
                    customer = Customer.query.get(user_id)
                    if customer:
                        customer.storage -= image_record.file_size
                        db.session.commit()
                else:
                    current_app.logger.warning(f"图片文件不存在：{image_record.filepath}")

                # 标记为删除
                image_record.deleted_flag = 'Y'
                image_record.deleted_at = datetime.utcnow()
                db.session.commit()

                return APIResponse.success(message='图片删除成功')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"图片删除失败：{str(e)}")
                return APIResponse.error('图片删除失败', 500)
                
        except Exception as e:
            current_app.logger.error(f"删除图片失败: {str(e)}")
            return APIResponse.error('删除失败', 500)


class ImageBatchDeleteResource(Resource):
    """图片批量删除资源"""
    
    @require_valid_token
    @jwt_required()
    def post(self):
        """批量删除图片翻译记录"""
        try:
            if not request.is_json:
                return APIResponse.error('请求Content-Type必须是application/json', 415)

            data = request.get_json(silent=True)
            if not data:
                return APIResponse.error('请求参数不能为空或JSON格式错误', 400)

            image_ids = data.get('image_ids', [])
            if not image_ids or not isinstance(image_ids, list):
                return APIResponse.error('缺少必要参数: image_ids（数组）', 400)

            if len(image_ids) > 100:
                return APIResponse.error('单次最多删除100条记录', 400)

            user_id = get_jwt_identity()
            
            # 查询所有图片记录
            image_records = ImageTranslate.query.filter(
                ImageTranslate.id.in_(image_ids),
                ImageTranslate.customer_id == user_id,
                ImageTranslate.deleted_flag == 'N'
            ).all()

            if not image_records:
                return APIResponse.error('没有找到可删除的记录', 404)

            deleted_count = 0
            failed_count = 0
            total_size = 0

            for image_record in image_records:
                try:
                    # 删除物理文件
                    if os.path.exists(image_record.filepath):
                        os.remove(image_record.filepath)
                        total_size += image_record.file_size
                    else:
                        current_app.logger.warning(f"图片文件不存在：{image_record.filepath}")

                    # 标记为删除
                    image_record.deleted_flag = 'Y'
                    image_record.deleted_at = datetime.utcnow()
                    deleted_count += 1
                except Exception as e:
                    current_app.logger.error(f"删除图片 {image_record.id} 失败：{str(e)}")
                    failed_count += 1

            # 更新用户存储空间
            if total_size > 0:
                customer = Customer.query.get(user_id)
                if customer:
                    customer.storage = max(0, customer.storage - total_size)

            # 提交所有更改
            db.session.commit()

            return APIResponse.success({
                'deleted_count': deleted_count,
                'failed_count': failed_count,
                'total_size': total_size,
                'message': f'成功删除{deleted_count}条记录，失败{failed_count}条'
            })

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"批量删除图片失败: {str(e)}")
            return APIResponse.error('批量删除失败', 500)


class ImageTranslateRetryResource(Resource):
    """图片翻译重试资源"""
    
    @require_valid_token
    @jwt_required()
    def post(self, image_id):
        """重试失败的翻译任务"""
        try:
            user_id = get_jwt_identity()
            
            # 查询图片记录
            image_record = ImageTranslate.query.filter_by(
                id=image_id,
                customer_id=user_id,
                deleted_flag='N'
            ).first()
            
            if not image_record:
                return APIResponse.error('图片记录不存在', 404)
            
            # 只有失败状态的任务才能重试
            if image_record.status != 'failed':
                return APIResponse.error('只有失败的任务才能重试', 400)
            
            # 检查是否有语言设置
            if not image_record.source_language or not image_record.target_language:
                return APIResponse.error('缺少语言设置，无法重试', 400)
            
            # 重置状态为uploaded，清空错误信息和task_id，让队列管理器重新处理
            image_record.status = 'uploaded'
            image_record.error_message = None
            image_record.qwen_task_id = None
            image_record.translated_image_url = None
            image_record.original_text = None
            image_record.translated_text = None
            image_record.detected_language = None
            db.session.commit()
            
            current_app.logger.info(f"图片翻译任务已重置为可重试状态: image_id={image_id}")
            
            return APIResponse.success({
                'image_id': image_record.id,
                'status': 'uploaded',
                'message': '任务已加入队列，等待重新处理'
            })
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"重试图片翻译任务失败: {str(e)}")
            return APIResponse.error('重试失败', 500)


class ImageTranslateBatchDownloadResource(Resource):
    """图片翻译批量下载资源"""
    
    @require_valid_token
    @jwt_required()
    def post(self):
        """批量下载翻译后的图片"""
        try:
            if not request.is_json:
                return APIResponse.error('请求Content-Type必须是application/json', 415)

            data = request.get_json(silent=True)
            if not data:
                return APIResponse.error('请求参数不能为空或JSON格式错误', 400)

            image_ids = data.get('image_ids', [])
            if not image_ids or not isinstance(image_ids, list):
                return APIResponse.error('缺少必要参数: image_ids（数组）', 400)

            if len(image_ids) > 100:
                return APIResponse.error('单次最多下载100条记录', 400)

            user_id = get_jwt_identity()
            
            # 查询所有图片记录
            image_records = ImageTranslate.query.filter(
                ImageTranslate.id.in_(image_ids),
                ImageTranslate.customer_id == user_id,
                ImageTranslate.deleted_flag == 'N',
                ImageTranslate.status == 'completed',  # 只下载已完成的
                ImageTranslate.translated_image_url.isnot(None)  # 必须有翻译后的图片URL
            ).all()

            if not image_records:
                return APIResponse.error('没有找到可下载的记录（只有已完成的翻译任务可以下载）', 404)

            # 生成内存 ZIP 文件
            zip_buffer = BytesIO()
            downloaded_count = 0
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for image_record in image_records:
                    try:
                        # 获取翻译后的图片URL
                        translated_url = image_record.translated_image_url
                        if not translated_url:
                            continue
                        
                        # 下载图片
                        response = requests.get(translated_url, timeout=30, stream=True)
                        if response.status_code == 200:
                            # 生成文件名（使用原始文件名+翻译标识）
                            original_name = os.path.splitext(image_record.original_filename)[0]
                            original_ext = os.path.splitext(image_record.original_filename)[1] or '.png'
                            zip_filename = f"{original_name}_translated{original_ext}"
                            
                            # 将图片内容添加到ZIP
                            zip_file.writestr(zip_filename, response.content)
                            downloaded_count += 1
                        else:
                            current_app.logger.warning(f"下载图片失败: image_id={image_record.id}, url={translated_url}, status={response.status_code}")
                    except Exception as e:
                        current_app.logger.error(f"处理图片 {image_record.id} 下载失败: {str(e)}")
                        continue

            if downloaded_count == 0:
                return APIResponse.error('没有成功下载任何图片', 400)

            # 重置缓冲区指针
            zip_buffer.seek(0)

            # 返回 ZIP 文件
            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f"translated_images_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            )

        except Exception as e:
            current_app.logger.error(f"批量下载图片翻译失败: {str(e)}")
            return APIResponse.error('批量下载失败', 500)


class PDFToImageResource(Resource):
    """PDF转图片资源"""
    
    @require_valid_token
    @jwt_required()
    def post(self):
        """将PDF转换为图片"""
        try:
            if 'file' not in request.files:
                return APIResponse.error('未选择文件', 400)
            
            file = request.files['file']
            if file.filename == '':
                return APIResponse.error('无效文件名', 400)
            
            # 检查文件格式
            if not file.filename.lower().endswith('.pdf'):
                return APIResponse.error('仅支持PDF格式文件', 400)
            
            # 获取参数
            image_format = request.form.get('image_format', 'png').lower()
            dpi = int(request.form.get('dpi', 200))
            page_range = request.form.get('page_range')  # 格式: "1-5" 或 None（全部）
            
            # 验证图片格式
            supported_formats = ['png', 'jpg', 'jpeg', 'webp']
            if image_format not in supported_formats:
                return APIResponse.error(f'不支持的图片格式，支持的格式: {", ".join(supported_formats)}', 400)
            
            # 验证DPI
            if dpi < 72 or dpi > 600:
                return APIResponse.error('DPI必须在72-600之间', 400)
            
            user_id = get_jwt_identity()
            tenant_id = get_current_tenant_id_from_request()
            customer = Customer.query.get(user_id)
            
            # 创建临时目录存储PDF和转换后的图片
            from app.utils.tenant_path import get_tenant_upload_dir
            temp_dir = get_tenant_upload_dir(user_id, tenant_id)
            pdf_dir = os.path.join(temp_dir, 'pdf_to_image')
            os.makedirs(pdf_dir, exist_ok=True)
            
            # 保存PDF文件
            timestamp = int(datetime.now().timestamp() * 1000)
            pdf_filename = f"{timestamp}.pdf"
            pdf_path = os.path.join(pdf_dir, pdf_filename)
            file.save(pdf_path)
            
            # 解析页面范围
            page_range_tuple = None
            if page_range:
                try:
                    if '-' in page_range:
                        start, end = page_range.split('-')
                        page_range_tuple = (int(start.strip()), int(end.strip()))
                    else:
                        page_num = int(page_range.strip())
                        page_range_tuple = (page_num, page_num)
                except ValueError:
                    return APIResponse.error('页面范围格式错误，格式应为: 1-5 或 1', 400)
            
            # 转换PDF为图片
            from app.utils.pdf_to_image import pdf_to_images
            output_dir = os.path.join(pdf_dir, f"{timestamp}_images")
            os.makedirs(output_dir, exist_ok=True)
            
            try:
                image_paths = pdf_to_images(
                    pdf_path=pdf_path,
                    output_dir=output_dir,
                    dpi=dpi,
                    page_range=page_range_tuple,
                    prefix="page",
                    image_format=image_format
                )
            except Exception as e:
                current_app.logger.error(f"PDF转图片失败: {str(e)}")
                return APIResponse.error(f'PDF转换失败: {str(e)}', 500)
            
            if not image_paths:
                return APIResponse.error('未生成任何图片', 500)
            
            # 将图片路径转换为URL（复用ImageTranslateResource的方法）
            image_translate_resource = ImageTranslateResource()
            image_urls = []
            for img_path in image_paths:
                image_url = image_translate_resource._convert_filepath_to_url(img_path)
                if not image_url:
                    current_app.logger.warning(f"无法转换图片路径为URL: {img_path}")
                    continue
                
                image_urls.append({
                    'url': image_url,
                    'filename': os.path.basename(img_path),
                    'path': img_path
                })
            
            # 打包为ZIP（如果有多张图片）
            zip_path = None
            zip_url = None
            if len(image_paths) > 1:
                zip_filename = f"{timestamp}_images.zip"
                zip_path = os.path.join(pdf_dir, zip_filename)
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for img_path in image_paths:
                        zip_file.write(img_path, os.path.basename(img_path))
                
                # 转换ZIP路径为URL
                zip_url = image_translate_resource._convert_filepath_to_url(zip_path)
            
            # 转换成功后，删除源PDF文件以节省存储空间
            try:
                if os.path.exists(pdf_path):
                    file_size = os.path.getsize(pdf_path)
                    os.remove(pdf_path)
                    current_app.logger.info(f"已删除源PDF文件: {pdf_path}, 释放空间: {file_size} 字节")
            except Exception as e:
                current_app.logger.warning(f"删除源PDF文件失败: {str(e)}，但不影响转换结果")
            
            return APIResponse.success({
                'total_pages': len(image_paths),
                'image_format': image_format.upper(),
                'dpi': dpi,
                'images': image_urls,
                'zip_url': zip_url,
                'message': f'成功转换{len(image_paths)}页PDF为{image_format.upper()}格式图片'
            })
            
        except Exception as e:
            current_app.logger.error(f"PDF转图片处理失败: {str(e)}")
            return APIResponse.error(f'处理失败: {str(e)}', 500)


class ImagesToPdfResource(Resource):
    """图片合并为PDF资源"""
    
    @require_valid_token
    @jwt_required()
    def post(self):
        """将多个图片合并为一个PDF文件"""
        try:
            if 'files' not in request.files:
                return APIResponse.error('未选择文件', 400)
            
            files = request.files.getlist('files')
            if not files or all(f.filename == '' for f in files):
                return APIResponse.error('未选择有效的图片文件', 400)
            
            # 获取参数
            data = request.form.get('data')
            if data:
                import json
                params = json.loads(data)
            else:
                params = {}
            
            page_size_preset = params.get('page_size_preset', 'A4')
            page_size = params.get('page_size')  # (width, height) 或 None
            fit_mode = params.get('fit_mode', 'fit')  # fit, stretch, center, custom
            margin = float(params.get('margin', 0))
            custom_settings = params.get('custom_settings')  # 每张图片的自定义设置
            image_order = params.get('image_order', [])  # 图片顺序索引列表
            
            # 验证适应模式
            valid_fit_modes = ['fit', 'stretch', 'center', 'custom']
            if fit_mode not in valid_fit_modes:
                return APIResponse.error(f'不支持的适应模式，支持的模式: {", ".join(valid_fit_modes)}', 400)
            
            user_id = get_jwt_identity()
            tenant_id = get_current_tenant_id_from_request()
            
            # 创建临时目录存储图片和PDF
            temp_dir = get_tenant_upload_dir(user_id, tenant_id)
            images_dir = os.path.join(temp_dir, 'images_to_pdf')
            os.makedirs(images_dir, exist_ok=True)
            
            image_paths = []
            uploaded_files = []
            
            try:
                # 保存上传的图片文件
                for idx, file in enumerate(files):
                    if file.filename == '':
                        continue
                    
                    # 检查文件格式
                    filename_lower = file.filename.lower()
                    if not any(filename_lower.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp']):
                        continue
                    
                    # 生成唯一文件名
                    file_ext = os.path.splitext(file.filename)[1]
                    unique_filename = f"{uuid.uuid4().hex}{file_ext}"
                    file_path = os.path.join(images_dir, unique_filename)
                    
                    file.save(file_path)
                    uploaded_files.append(file_path)
                
                if not uploaded_files:
                    return APIResponse.error('没有有效的图片文件', 400)
                
                # 根据用户指定的顺序重新排列图片
                if image_order and len(image_order) == len(uploaded_files):
                    try:
                        # image_order是索引列表，例如 [2, 0, 1] 表示重新排序
                        ordered_files = [uploaded_files[i] for i in image_order]
                        image_paths = ordered_files
                    except (IndexError, TypeError):
                        # 如果顺序无效，使用原始顺序
                        image_paths = uploaded_files
                else:
                    image_paths = uploaded_files
                
                # 生成PDF文件名
                pdf_filename = f"{uuid.uuid4().hex}.pdf"
                pdf_path = os.path.join(images_dir, pdf_filename)
                
                # 调用合并函数
                from app.utils.images_to_pdf import images_to_pdf
                images_to_pdf(
                    image_paths=image_paths,
                    output_pdf_path=pdf_path,
                    page_size=page_size,
                    page_size_preset=page_size_preset,
                    fit_mode=fit_mode,
                    margin=margin,
                    custom_settings=custom_settings
                )
                
                # 转换PDF路径为URL（复用ImageTranslateResource的方法）
                image_translate_resource = ImageTranslateResource()
                pdf_url = image_translate_resource._convert_filepath_to_url(pdf_path)
                
                # 清理上传的图片文件（保留PDF供下载）
                for img_path in uploaded_files:
                    try:
                        if os.path.exists(img_path):
                            os.remove(img_path)
                    except Exception as e:
                        current_app.logger.warning(f"删除临时图片文件失败: {img_path}, {str(e)}")
                
                return APIResponse.success({
                    'pdf_url': pdf_url,
                    'pdf_path': pdf_path,
                    'message': f'成功合并{len(image_paths)}张图片为PDF'
                })
                
            except Exception as e:
                # 清理临时文件
                for file_path in uploaded_files + ([pdf_path] if 'pdf_path' in locals() else []):
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    except:
                        pass
                raise
                
        except Exception as e:
            current_app.logger.error(f"图片合并PDF处理失败: {str(e)}")
            return APIResponse.error(f'处理失败: {str(e)}', 500)
