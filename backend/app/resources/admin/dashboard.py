# resources/admin/dashboard.py
from datetime import datetime, timedelta
from decimal import Decimal
import psutil
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required
from sqlalchemy import func, distinct

from app import db
from app.models.translate import Translate
from app.models.customer import Customer
from app.models.tenant_customer import TenantCustomer
from app.utils.response import APIResponse
from app.utils.admin_tenant_helper import get_admin_tenant_id, is_super_admin


def decimal_to_float(value):
    """将Decimal类型转换为float，如果为None则返回0"""
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


class DashboardStatisticsResource(Resource):
    """看板统计数据"""
    @jwt_required()
    def get(self):
        """获取看板统计数据"""
        try:
            tenant_id = get_admin_tenant_id()
            
            # 构建基础查询
            base_query = Translate.query.filter(Translate.deleted_flag == 'N')
            customer_query = Customer.query.filter(Customer.deleted_flag == 'N')
            
            # 租户过滤
            if tenant_id is not None and not is_super_admin():
                # 翻译任务需要通过租户客户关联表过滤
                base_query = base_query.join(
                    TenantCustomer, Translate.customer_id == TenantCustomer.customer_id
                ).filter(TenantCustomer.tenant_id == tenant_id)
                
                # 用户也需要过滤
                customer_ids = db.session.query(TenantCustomer.customer_id).filter(
                    TenantCustomer.tenant_id == tenant_id
                ).subquery()
                customer_query = customer_query.filter(Customer.id.in_(customer_ids))
            
            # 1. 今日翻译任务数
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_tasks = base_query.filter(Translate.created_at >= today_start).count()
            
            # 2. 翻译成功率
            total_tasks = base_query.count()
            completed_tasks = base_query.filter(Translate.status == 'done').count()
            success_rate = round((completed_tasks / total_tasks * 100), 2) if total_tasks > 0 else 0
            
            # 3. 今日活跃用户数（今天有翻译任务的用户数）- 使用正确的去重统计
            active_users = base_query.filter(
                Translate.created_at >= today_start
            ).with_entities(
                func.count(func.distinct(Translate.customer_id))
            ).scalar() or 0
            
            # 4. 存储使用率
            total_storage = decimal_to_float(
                customer_query.with_entities(
                    func.sum(Customer.total_storage)
                ).scalar()
            )
            used_storage = decimal_to_float(
                customer_query.with_entities(
                    func.sum(Customer.storage)
                ).scalar()
            )
            storage_usage = round((used_storage / total_storage * 100), 2) if total_storage > 0 else 0
            
            return APIResponse.success({
                'today_tasks': today_tasks,
                'success_rate': success_rate,
                'active_users': active_users,
                'storage_usage': storage_usage
            })
        except Exception as e:
            return APIResponse.error(f'获取统计信息失败: {str(e)}', 500)


class DashboardTrendResource(Resource):
    """看板趋势数据"""
    @jwt_required()
    def get(self):
        """获取翻译趋势数据"""
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('days', type=int, default=7, location='args')
            args = parser.parse_args()
            
            tenant_id = get_admin_tenant_id()
            days = args['days']
            
            # 构建查询
            base_query = Translate.query.filter(Translate.deleted_flag == 'N')
            
            if tenant_id is not None and not is_super_admin():
                base_query = base_query.join(
                    TenantCustomer, Translate.customer_id == TenantCustomer.customer_id
                ).filter(TenantCustomer.tenant_id == tenant_id) 
            
            # 获取日期范围
            end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            start_date = (end_date - timedelta(days=days)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 按天统计
            results = base_query.filter(
                Translate.created_at >= start_date,
                Translate.created_at <= end_date
            ).with_entities(
                func.date(Translate.created_at).label('date'),
                func.count(Translate.id).label('count')
            ).group_by(func.date(Translate.created_at)).all()
            
            # 格式化日期并构建完整日期列表
            dates = []
            counts = []
            for i in range(days):
                date = (start_date + timedelta(days=i)).date()
                dates.append(date.strftime('%Y-%m-%d'))
                counts.append(0)  # 默认值
            
            # 填充实际数据
            for result in results:
                date_str = result.date.strftime('%Y-%m-%d')
                if date_str in dates:
                    idx = dates.index(date_str)
                    counts[idx] = result.count
            
            return APIResponse.success({
                'dates': dates,
                'counts': counts
            })
        except Exception as e:
            return APIResponse.error(f'获取趋势数据失败: {str(e)}', 500)


class DashboardStatusDistributionResource(Resource):
    """任务状态分布"""
    @jwt_required()
    def get(self):
        """获取任务状态分布"""
        try:
            tenant_id = get_admin_tenant_id()
            
            # 构建查询
            base_query = Translate.query.filter(Translate.deleted_flag == 'N')
            
            if tenant_id is not None and not is_super_admin():
                base_query = base_query.join(
                    TenantCustomer, Translate.customer_id == TenantCustomer.customer_id
                ).filter(TenantCustomer.tenant_id == tenant_id)
            
            # 按状态分组统计
            results = base_query.with_entities(
                Translate.status,
                func.count(Translate.id).label('count')
            ).group_by(Translate.status).all()
            
            # 格式化数据
            distribution = {
                'done': 0,
                'process': 0,
                'failed': 0,
                'queued': 0,
                'none': 0
            }
            
            for result in results:
                status = result.status
                count = result.count
                if status in distribution:
                    distribution[status] = count
            
            return APIResponse.success(distribution)
        except Exception as e:
            return APIResponse.error(f'获取状态分布失败: {str(e)}', 500)


class DashboardRecentTasksResource(Resource):
    """最近任务列表"""
    @jwt_required()
    def get(self):
        """获取最近任务列表"""
        try:
            parser = reqparse.RequestParser()
            parser.add_argument('limit', type=int, default=10, location='args')
            args = parser.parse_args()
            
            tenant_id = get_admin_tenant_id()
            limit = args['limit']
            
            # 构建查询
            base_query = Translate.query.filter(Translate.deleted_flag == 'N')
            
            if tenant_id is not None and not is_super_admin():
                base_query = base_query.join(
                    TenantCustomer, Translate.customer_id == TenantCustomer.customer_id
                ).filter(TenantCustomer.tenant_id == tenant_id)
            
            # 获取最近任务
            tasks = base_query.order_by(
                Translate.created_at.desc()
            ).limit(limit).all()
            
            # 转换为字典
            task_list = []
            for task in tasks:
                task_data = task.to_dict()
                # 直接从模型对象获取 total_tokens（因为 to_dict 可能不包含此字段）
                total_tokens = task.total_tokens if task.total_tokens is not None else 0
                # 只返回必要字段
                task_list.append({
                    'id': task_data.get('id'),
                    'translate_no': task.translate_no,  # 直接从模型获取
                    'origin_filename': task_data.get('origin_filename'),
                    'status': task_data.get('status'),
                    'created_at': task_data.get('created_at'),
                    'customer_id': task_data.get('customer_id'),
                    'total_tokens': total_tokens  # 总token消耗量
                })
            
            return APIResponse.success({'tasks': task_list})
        except Exception as e:
            return APIResponse.error(f'获取最近任务失败: {str(e)}', 500)


class DashboardSystemStatusResource(Resource):
    """系统状态监控"""
    @jwt_required()
    def get(self):
        """获取系统状态"""
        try:
            tenant_id = get_admin_tenant_id()
            
            # 构建查询
            base_query = Translate.query.filter(Translate.deleted_flag == 'N')
            
            if tenant_id is not None and not is_super_admin():
                base_query = base_query.join(
                    TenantCustomer, Translate.customer_id == TenantCustomer.customer_id
                ).filter(TenantCustomer.tenant_id == tenant_id)
            
            # 1. 队列状态
            queue_count = base_query.filter(
                Translate.status.in_(['queued', 'process'])
            ).count()
            
            # 2. 服务器系统信息
            try:
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=0.1)
                
                # 内存使用率
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_total = memory.total
                memory_used = memory.used
                
                # 磁盘使用率（系统磁盘，通常是根目录）
                disk = psutil.disk_usage('/')
                disk_percent = disk.percent
                disk_total = disk.total
                disk_used = disk.used
                
                # 系统运行时间
                boot_time = psutil.boot_time()
                uptime_seconds = datetime.now().timestamp() - boot_time
                uptime_days = int(uptime_seconds / 86400)
                uptime_hours = int((uptime_seconds % 86400) / 3600)
                uptime = f"{uptime_days}天{uptime_hours}小时"
                
            except Exception as e:
                # 如果获取系统信息失败，使用默认值
                cpu_percent = 0
                memory_percent = 0
                memory_total = 0
                memory_used = 0
                disk_percent = 0
                disk_total = 0
                disk_used = 0
                uptime = "未知"
            
            # 3. 用户存储使用 - 从用户存储数据计算
            customer_query = Customer.query.filter(Customer.deleted_flag == 'N')
            
            if tenant_id is not None and not is_super_admin():
                customer_ids = db.session.query(TenantCustomer.customer_id).filter(
                    TenantCustomer.tenant_id == tenant_id
                ).subquery()
                customer_query = customer_query.filter(Customer.id.in_(customer_ids))
            
            total_storage = decimal_to_float(
                customer_query.with_entities(
                    func.sum(Customer.total_storage)
                ).scalar()
            )
            used_storage = decimal_to_float(
                customer_query.with_entities(
                    func.sum(Customer.storage)
                ).scalar()
            )
            user_storage_percentage = round((used_storage / total_storage * 100), 2) if total_storage > 0 else 0
            
            return APIResponse.success({
                'queue_count': queue_count,
                'server_info': {
                    'cpu_percent': round(cpu_percent, 1),
                    'memory_percent': round(memory_percent, 1),
                    'memory_total': int(memory_total),
                    'memory_used': int(memory_used),
                    'disk_percent': round(disk_percent, 1),
                    'disk_total': int(disk_total),
                    'disk_used': int(disk_used),
                    'uptime': uptime
                },
                'user_storage': {
                    'percentage': user_storage_percentage,
                    'used': used_storage,
                    'total': total_storage
                }
            })
        except Exception as e:
            return APIResponse.error(f'获取系统状态失败: {str(e)}', 500)

