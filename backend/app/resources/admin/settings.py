# resources/admin/setting.py
import json
import os
import shutil
from flask import request, current_app
from flask_restful import Resource
from flask_jwt_extended import jwt_required

from app import db
from app.models import Setting
from app.utils.response import APIResponse
from app.utils.validators import validate_id_list


class AdminSettingNoticeResource(Resource):
    def get(self):
        """获取通知设置"""
        setting = Setting.query.filter_by(alias='notice_setting').first()
        if not setting:
            return APIResponse.success(data={'users': []})
        return APIResponse.success(data={'users': eval(setting.value)})

    def post(self):
        """更新通知设置"""
        data = request.json
        users = validate_id_list(data.get('users'))

        setting = Setting.query.filter_by(alias='notice_setting').first()
        if not setting:
            setting = Setting(alias='notice_setting')

        setting.value = str(users)
        setting.serialized = True
        db.session.add(setting)
        db.session.commit()
        return APIResponse.success(message='通知设置已更新')


class AdminSettingApiResource(Resource):
    @jwt_required()
    def get(self):
        """
        获取API配置（支持租户级配置）
        - 超级管理员：可以指定tenant_id查看任意租户配置
        - 租户管理员：只能查看本租户配置
        """
        from flask import request
        from app.utils.admin_tenant_helper import is_super_admin, get_admin_tenant_id
        
        # 确定要查询的tenant_id
        target_tenant_id = None
        
        # 超级管理员可以从参数中指定tenant_id
        if is_super_admin():
            tenant_id_param = request.args.get('tenant_id')
            if tenant_id_param:
                try:
                    target_tenant_id = int(tenant_id_param)
                except ValueError:
                    target_tenant_id = None
        else:
            # 租户管理员只能查询本租户
            target_tenant_id = get_admin_tenant_id()
        
        # 获取配置字段（简化，只需要三个关键字段）
        fields = ['dashscope_key', 'akool_client_id', 'akool_client_secret']
        data = {}
        
        for alias in fields:
            # 1. 如果有目标租户，先查租户配置
            if target_tenant_id:
                tenant_setting = Setting.query.filter_by(
                    alias=alias,
                    group='api_setting',
                    tenant_id=target_tenant_id,
                    deleted_flag='N'
                ).first()
                
                if tenant_setting and tenant_setting.value:
                    data[alias] = tenant_setting.value
                    continue
            
            # 2. 查全局配置（fallback）
            global_setting = Setting.query.filter_by(
                alias=alias,
                group='api_setting',
                tenant_id=None,
                deleted_flag='N'
            ).first()
            
            data[alias] = global_setting.value if global_setting and global_setting.value else ''
        
        return APIResponse.success(data=data)

    @jwt_required()
    def post(self):
        """
        更新API配置（支持租户级配置）
        - 超级管理员：可以指定tenant_id保存任意租户配置
        - 租户管理员：自动保存到本租户
        """
        from flask import request as req, g
        from app.utils.admin_tenant_helper import is_super_admin, get_admin_tenant_id
        
        data = req.json
        # 不再强制要求必填字段，所有字段都可选
        
        # 确定保存的tenant_id
        save_tenant_id = None
        
        if is_super_admin():
            # 超级管理员可以从参数中指定tenant_id（可选，不指定则为全局配置）
            tenant_id_param = req.json.get('tenant_id')
            if tenant_id_param:
                try:
                    save_tenant_id = int(tenant_id_param)
                except (ValueError, TypeError):
                    save_tenant_id = None
        else:
            # 租户管理员自动保存到本租户
            save_tenant_id = get_admin_tenant_id()
            if not save_tenant_id:
                return APIResponse.error('未分配到租户', 403)
        
        # 定义可配置的字段
        allowed_fields = ['dashscope_key', 'akool_client_id', 'akool_client_secret']
        
        # 保存配置
        for alias, value in data.items():
            if alias == 'tenant_id':  # 跳过tenant_id参数本身
                continue
            
            # 只保存允许的字段
            if alias not in allowed_fields:
                continue
            
            setting = Setting.query.filter_by(
                alias=alias,
                group='api_setting',
                tenant_id=save_tenant_id
            ).first()
            
            if not setting:
                setting = Setting(
                    alias=alias,
                    group='api_setting',
                    tenant_id=save_tenant_id
                )
            
            setting.value = value if value else ''  # 允许空值
            db.session.add(setting)
        
        db.session.commit()
        
        # 返回成功消息
        if save_tenant_id:
            return APIResponse.success(message=f'租户{save_tenant_id}的API配置已更新')
        else:
            return APIResponse.success(message='全局API配置已更新')


class AdminInfoSettingOtherResource(Resource):
    @jwt_required()
    def get(self):
        """获取其他设置（支持租户级配置）"""
        from app.utils.admin_tenant_helper import is_super_admin, get_admin_tenant_id
        
        # 确定要查询的tenant_id
        target_tenant_id = None
        if is_super_admin():
            tenant_id_param = request.args.get('tenant_id')
            if tenant_id_param:
                try:
                    target_tenant_id = int(tenant_id_param)
                except ValueError:
                    target_tenant_id = None
        else:
            target_tenant_id = get_admin_tenant_id()
        
        # 获取配置 - 只返回email_limit
        fields = ['email_limit']
        data = {}
        
        for alias in fields:
            if target_tenant_id:
                tenant_setting = Setting.query.filter_by(
                    alias=alias,
                    group='other_setting',
                    tenant_id=target_tenant_id,
                    deleted_flag='N'
                ).first()
                
                if tenant_setting and tenant_setting.value:
                    data[alias] = tenant_setting.value
                    continue
            
            global_setting = Setting.query.filter_by(
                alias=alias,
                group='other_setting',
                tenant_id=None,
                deleted_flag='N'
            ).first()
            
            data[alias] = global_setting.value if global_setting and global_setting.value else ''
        
        return APIResponse.success(data=data)



class AdminEditSettingOtherResource(Resource):
    @jwt_required()
    def post(self):
        """更新其他设置（支持租户级配置）"""
        from app.utils.admin_tenant_helper import is_super_admin, get_admin_tenant_id
        
        data = request.json
        # email_limit 是可选的，不需要验证必填
        
        # 确定保存的tenant_id
        save_tenant_id = None
        if is_super_admin():
            tenant_id_param = data.get('tenant_id')
            if tenant_id_param:
                try:
                    save_tenant_id = int(tenant_id_param)
                except (ValueError, TypeError):
                    save_tenant_id = None
        else:
            save_tenant_id = get_admin_tenant_id()
            if not save_tenant_id:
                return APIResponse.error('未分配到租户', 403)
        
        for alias, value in data.items():
            if alias == 'tenant_id':
                continue
            
            # 只允许更新 email_limit
            if alias != 'email_limit':
                continue
                
            setting = Setting.query.filter_by(
                alias=alias,
                group='other_setting',
                tenant_id=save_tenant_id
            ).first()
            
            if not setting:
                setting = Setting(
                    alias=alias,
                    group='other_setting',
                    tenant_id=save_tenant_id
                )
            
            setting.value = value
            db.session.add(setting)
        
        db.session.commit()
        
        if save_tenant_id:
            return APIResponse.success(message=f'租户{save_tenant_id}的其他设置已更新')
        else:
            return APIResponse.success(message='全局其他设置已更新')


class AdminSettingSiteResource(Resource):
    @jwt_required()
    def get(self):
        """获取站点设置（支持租户级配置）"""
        from app.utils.admin_tenant_helper import is_super_admin, get_admin_tenant_id
        
        # 确定要查询的tenant_id
        target_tenant_id = None
        if is_super_admin():
            tenant_id_param = request.args.get('tenant_id')
            if tenant_id_param:
                try:
                    target_tenant_id = int(tenant_id_param)
                except ValueError:
                    target_tenant_id = None
        else:
            target_tenant_id = get_admin_tenant_id()
        
        # 获取配置
        fields = ['version', 'site_title', 'site_name', 'site_logo', 'admin_site_title']
        data = {}
        
        for alias in fields:
            if target_tenant_id:
                tenant_setting = Setting.query.filter_by(
                    alias=alias,
                    group='site_setting',
                    tenant_id=target_tenant_id,
                    deleted_flag='N'
                ).first()
                
                if tenant_setting and tenant_setting.value:
                    data[alias] = tenant_setting.value
                    continue
            
            global_setting = Setting.query.filter_by(
                alias=alias,
                group='site_setting',
                tenant_id=None,
                deleted_flag='N'
            ).first()
            
            if global_setting and global_setting.value:
                data[alias] = global_setting.value
            else:
                # 设置默认值
                data[alias] = '' if alias != 'version' else 'business'
        
        # 特殊处理 site_logo 的 remark
        logo_setting = Setting.query.filter_by(
            alias='site_logo',
            group='site_setting',
            tenant_id=target_tenant_id if target_tenant_id else None,
            deleted_flag='N'
        ).first()
        
        data['update_time'] = logo_setting.remark if logo_setting else None
        
        return APIResponse.success(data=data)

    @jwt_required()
    def post(self):
        """更新站点设置（支持租户级配置）"""
        from app.utils.admin_tenant_helper import is_super_admin, get_admin_tenant_id
        
        data = request.json
        if not data or not isinstance(data, dict):
            return APIResponse.error('请求参数错误', 400)
        
        # 确定保存的tenant_id
        save_tenant_id = None
        if is_super_admin():
            tenant_id_param = data.get('tenant_id')
            if tenant_id_param:
                try:
                    save_tenant_id = int(tenant_id_param)
                except (ValueError, TypeError):
                    save_tenant_id = None
        else:
            save_tenant_id = get_admin_tenant_id()
            if not save_tenant_id:
                return APIResponse.error('未分配到租户', 403)
        
        # 定义可更新字段及类型约束
        allowed_fields = {
            'version': str,
            'site_title': str,
            'site_name': str,
            'site_logo': str,
            'admin_site_title': str,
            'update_time': str
        }

        # 验证并更新字段
        for key, value in data.items():
            if key in allowed_fields:
                # 跳过tenant_id参数
                if key == 'tenant_id':
                    continue
                    
                # 类型检查
                if not isinstance(value, allowed_fields[key]):
                    return APIResponse.error(f'字段 {key} 类型错误', 400)

                # 更新字段
                setting = Setting.query.filter_by(
                    alias=key,
                    group='site_setting',
                    tenant_id=save_tenant_id
                ).first()
                
                if not setting:
                    setting = Setting(
                        alias=key,
                        group='site_setting',
                        tenant_id=save_tenant_id
                    )
                
                setting.value = str(value)
                
                # 额外处理 site_logo 的 remark
                if key == 'site_logo' and 'update_time' in data:
                    setting.remark = data['update_time']
                
                db.session.add(setting)

        db.session.commit()
        
        if save_tenant_id:
            return APIResponse.success(message=f'租户{save_tenant_id}的站点设置已更新')
        else:
            return APIResponse.success(message='全局站点设置已更新')


# ----系统存储设置-----
# 获取系统路径存储文件列表/删除
class SystemStorageResource(Resource):
    @jwt_required()
    def get(self):
        """获取文件列表（支持租户隔离）"""
        from app.utils.admin_tenant_helper import is_super_admin, get_admin_tenant_id
        
        try:
            # 存储目录直接使用 /app/storage
            storage_path = '/app/storage'
            
            if not os.path.exists(storage_path):
                current_app.logger.error(f"storage目录不存在: {storage_path}")
                return APIResponse.error(message='存储路径配置错误，请联系管理员', code=500)

            # 获取租户ID
            tenant_id = get_admin_tenant_id()
            is_super = is_super_admin()
            
            result = {}

            # 根据用户角色决定扫描范围
            scan_categories = []
            if is_super:
                # 超级管理员：扫描所有分类
                scan_categories = os.listdir(storage_path)
            else:
                # 租户管理员：只扫描自己租户的文件
                if tenant_id:
                    for category in os.listdir(storage_path):
                        category_path = os.path.join(storage_path, category)
                        if not os.path.isdir(category_path):
                            continue
                        # 检查是否是租户目录（例如 tenant_1, tenant_2）
                        for sub_dir in os.listdir(category_path):
                            if f"tenant_{tenant_id}" in sub_dir or sub_dir.startswith(f"{tenant_id}/"):
                                scan_categories.append(category)
                                break

            for category in scan_categories:
                category_path = os.path.join(storage_path, category)
                if not os.path.isdir(category_path):
                    continue

                category_data = {"size": 0, "dates": {}}

                # 处理video目录的特殊结构：video/tenant_X/user_Y/date/
                if category == 'video':
                    # video目录结构：tenant_X/user_Y/date
                    for tenant_dir in os.listdir(category_path):
                        tenant_path = os.path.join(category_path, tenant_dir)
                        if not os.path.isdir(tenant_path):
                            continue
                        
                        # 租户过滤
                        if not is_super and tenant_id:
                            if f"tenant_{tenant_id}" not in tenant_path:
                                continue
                        
                        # 遍历用户目录
                        for user_dir in os.listdir(tenant_path):
                            user_path = os.path.join(tenant_path, user_dir)
                            if not os.path.isdir(user_path):
                                continue
                            
                            # 遍历日期目录
                            for date_dir in os.listdir(user_path):
                                date_path = os.path.join(user_path, date_dir)
                                if not os.path.isdir(date_path):
                                    continue
                                
                                # 租户过滤：检查路径中是否包含租户信息
                                if not is_super and tenant_id:
                                    if f"tenant_{tenant_id}" not in date_path:
                                        continue
                                
                                date_data = {"size": 0, "files": []}
                                
                                # 保持系统原生路径格式
                                for root, _, files in os.walk(date_path):
                                    for file in files:
                                        file_path = os.path.join(root, file)
                                        try:
                                            size = os.path.getsize(file_path)
                                            date_data["files"].append({
                                                "path": file_path,
                                                "size": size,
                                                "name": file
                                            })
                                            date_data["size"] += size
                                        except OSError:
                                            continue
                                
                                # 使用完整路径作为key，包含租户和用户信息
                                key = f"{tenant_dir}/{user_dir}/{date_dir}"
                                category_data["size"] += date_data["size"]
                                category_data["dates"][key] = date_data
                else:
                    # 其他目录的标准结构：category/tenant_X/user_Y/date/
                    for tenant_dir in os.listdir(category_path):
                        tenant_path = os.path.join(category_path, tenant_dir)
                        if not os.path.isdir(tenant_path):
                            continue
                        
                        # 遍历用户目录
                        for user_dir in os.listdir(tenant_path):
                            user_path = os.path.join(tenant_path, user_dir)
                            if not os.path.isdir(user_path):
                                continue
                            
                            # 遍历日期目录
                            for date_dir in os.listdir(user_path):
                                date_path = os.path.join(user_path, date_dir)
                                if not os.path.isdir(date_path):
                                    continue
                                
                                # 租户过滤：检查路径中是否包含租户信息
                                if not is_super and tenant_id:
                                    if f"tenant_{tenant_id}" not in date_path:
                                        continue
                                
                                date_data = {"size": 0, "files": []}
                                
                                # 保持系统原生路径格式
                                for root, _, files in os.walk(date_path):
                                    for file in files:
                                        file_path = os.path.join(root, file)
                                        try:
                                            size = os.path.getsize(file_path)
                                            date_data["files"].append({
                                                "path": file_path,
                                                "size": size,
                                                "name": file
                                            })
                                            date_data["size"] += size
                                        except OSError:
                                            continue
                                
                                # 使用完整路径作为key
                                key = f"{tenant_dir}/{user_dir}/{date_dir}"
                                category_data["size"] += date_data["size"]
                                category_data["dates"][key] = date_data

                result[category] = category_data

            return APIResponse.success(data=result)

        except Exception as e:
            current_app.logger.error(f"获取文件列表失败: {str(e)}")
            return APIResponse.error("获取文件列表失败")

    @jwt_required()
    def delete(self):
        """删除（自动清理空目录，支持租户隔离）"""
        from app.utils.admin_tenant_helper import is_super_admin, get_admin_tenant_id
        
        try:
            req = request.get_json()
            target = req.get("target")
            delete_type = req.get("type")

            if not target or not delete_type:
                return APIResponse.error("缺少必要参数")

            base_dir = os.path.dirname(current_app.root_path)
            target_path = os.path.join(base_dir, 'storage', *target.split('/'))

            # 安全检查
            storage_path = os.path.join(base_dir, 'storage')
            if not os.path.abspath(target_path).startswith(os.path.abspath(storage_path)):
                return APIResponse.error("非法路径")
            
            # 租户隔离：非超级管理员只能删除自己租户的文件
            tenant_id = get_admin_tenant_id()
            is_super = is_super_admin()
            
            if not is_super and tenant_id:
                # 检查目标路径是否属于该租户
                if f"tenant_{tenant_id}" not in target_path:
                    return APIResponse.error("无权删除其他租户的文件", 403)

            # 执行删除
            if delete_type == "file":
                if not os.path.exists(target_path):
                    return APIResponse.not_found("文件不存在")

                # 删除文件
                os.remove(target_path)
                self._clean_empty_dirs(target_path)  # 自动清理空目录

            elif delete_type == "date":
                if not os.path.exists(target_path):
                    return APIResponse.not_found("日期目录不存在")
                shutil.rmtree(target_path)  # 删除整个日期目录

            elif delete_type == "category":
                if not os.path.exists(target_path):
                    return APIResponse.not_found("分类目录不存在")
                shutil.rmtree(target_path)  # 删除整个分类目录

            else:
                return APIResponse.error("无效操作类型")

            return APIResponse.success(message="删除成功")

        except PermissionError:
            return APIResponse.error("权限不足")
        except Exception as e:
            current_app.logger.error(f"删除失败: {str(e)}")
            return APIResponse.error("删除操作失败")

    def _clean_empty_dirs(self, file_path):
        """递归清理空目录（私有方法）"""
        current_dir = os.path.dirname(file_path)
        storage_root = os.path.join(os.path.dirname(current_app.root_path), 'storage')

        # 从文件所在目录向上清理，直到storage根目录
        while len(current_dir) > len(storage_root):
            try:
                if not os.listdir(current_dir):  # 如果是空目录
                    os.rmdir(current_dir)
                    current_dir = os.path.dirname(current_dir)  # 继续检查上级目录
                else:
                    break
            except OSError:
                break
