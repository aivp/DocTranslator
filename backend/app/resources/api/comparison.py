# resources/comparison.py

import zipfile
from io import BytesIO
import pandas as pd
import pytz
from flask import request, current_app, send_file
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.models import Customer
from app.models.comparison import Comparison, ComparisonFav
from app.utils.response import APIResponse
from sqlalchemy import func
from datetime import datetime
from app.utils.token_checker import require_valid_token



class MyComparisonListResource(Resource):
    @require_valid_token
    @jwt_required()
    def get(self):
        """获取我的术语表列表[^1]"""
        # 直接查询所有数据（不解析查询参数）
        query = Comparison.query.filter_by(customer_id=get_jwt_identity())
        comparisons = [self._format_comparison(comparison) for comparison in query.all()]

        # 返回结果
        return APIResponse.success({
            'data': comparisons,
            'total': len(comparisons)
        })

    def _format_comparison(self, comparison):
        """格式化术语表数据"""
        # 解析 content 字段
        content_list = []
        if comparison.content:
            for item in comparison.content.split('; '):
                if ':' in item:
                    origin, target = item.split(':', 1)
                    content_list.append({
                        'origin': origin.strip(),
                        'target': target.strip()
                    })

        # 返回格式化后的数据
        return {
            'id': comparison.id,
            'title': comparison.title,
            'origin_lang': comparison.origin_lang,
            'target_lang': comparison.target_lang,
            'share_flag': comparison.share_flag,
            'added_count': comparison.added_count,
            'content': content_list,  # 返回解析后的数组
            'customer_id': comparison.customer_id,
            'created_at': comparison.created_at.strftime(
                '%Y-%m-%d %H:%M') if comparison.created_at else None,  # 格式化时间
            'updated_at': comparison.updated_at.strftime(
                '%Y-%m-%d %H:%M') if comparison.updated_at else None,  # 格式化时间
            'deleted_flag': comparison.deleted_flag
        }


# 获取共享术语表列表
class SharedComparisonListResource(Resource):
    @require_valid_token
    @jwt_required()
    def get(self):
        """获取共享术语表列表[^3]"""
        # 从查询字符串中解析参数
        parser = reqparse.RequestParser()
        parser.add_argument('page', type=int, default=1, location='args')  # 分页参数
        parser.add_argument('limit', type=int, default=10, location='args')  # 分页参数
        parser.add_argument('order', type=str, default='latest', location='args')  # 排序参数
        args = parser.parse_args()

        # 查询共享的术语表，并关联 Customer 表获取用户 email
        query = db.session.query(
            Comparison,
            func.count(ComparisonFav.id).label('fav_count'),  # 动态计算收藏量
            Customer.email.label('customer_email')  # 获取用户的 email
        ).outerjoin(
            ComparisonFav, Comparison.id == ComparisonFav.comparison_id
        ).outerjoin(
            Customer, Comparison.customer_id == Customer.id  # 通过 customer_id 关联 Customer
        ).filter(
            Comparison.share_flag == 'Y',
            Comparison.deleted_flag == 'N'
        ).group_by(
            Comparison.id
        )

        # 根据 order 参数排序
        if args['order'] == 'latest':
            query = query.order_by(Comparison.created_at.desc())  # 按最新发表排序
        elif args['order'] == 'added':
            query = query.order_by(Comparison.added_count.desc())  # 按添加量排序
        elif args['order'] == 'fav':
            query = query.order_by(func.count(ComparisonFav.id).desc())  # 按收藏量排序

        # 分页查询
        pagination = query.paginate(page=args['page'], per_page=args['limit'], error_out=False)
        comparisons = [{
            'id': comparison.id,
            'title': comparison.title,
            'origin_lang': comparison.origin_lang,
            'target_lang': comparison.target_lang,
            'content': self.parse_content(comparison.content),  # 解析 content 字段为数组
            'email': customer_email if customer_email else '匿名用户',  # 返回用户 email
            'added_count': comparison.added_count,
            'created_at': comparison.created_at.strftime('%Y-%m-%d %H:%M'),  # 格式化时间
            'faved': self.check_faved(comparison.id),  # 检查是否被当前用户收藏
            'fav_count': fav_count  # 添加收藏量
        } for comparison, fav_count, customer_email in pagination.items]

        # 返回结果
        return APIResponse.success({
            'data': comparisons,
            'total': pagination.total,
            'current_page': pagination.page,
            'per_page': pagination.per_page
        })

    def parse_content(self, content_str):
        """将 content 字符串解析为数组格式"""
        content_list = []
        if content_str:
            for item in content_str.split('; '):
                if ':' in item:
                    origin, target = item.split(':', 1)  # 分割为 origin 和 target
                    content_list.append({
                        'origin': origin.strip(),
                        'target': target.strip()
                    })
        return content_list

    def check_faved(self, comparison_id):
        """检查当前用户是否收藏了该术语表"""
        # 假设当前用户的 ID 存储在 JWT 中
        user_id = get_jwt_identity()
        if user_id:
            fav = ComparisonFav.query.filter_by(
                comparison_id=comparison_id,
                customer_id=user_id
            ).first()
            return 1 if fav else 0
        return 0


class SharedComparisonListResource111(Resource):
    def get(self):
        """获取共享术语表列表[^3]"""
        # 从查询字符串中解析参数
        parser = reqparse.RequestParser()
        parser.add_argument('page', type=int, default=1, location='args')  # 分页参数
        parser.add_argument('limit', type=int, default=10, location='args')  # 分页参数
        parser.add_argument('order', type=str, default='latest', location='args')  # 排序参数
        args = parser.parse_args()

        # 查询共享的术语表，并关联 Customer 表获取用户 email
        query = db.session.query(
            Comparison,
            func.count(ComparisonFav.id).label('fav_count'),  # 动态计算收藏量
            Customer.email.label('customer_email')  # 获取用户的 email
        ).outerjoin(
            ComparisonFav, Comparison.id == ComparisonFav.comparison_id
        ).outerjoin(
            Customer, Comparison.customer_id == Customer.id  # 通过 customer_id 关联 Customer
        ).filter(
            Comparison.share_flag == 'Y',
            Comparison.deleted_flag == 'N'
        ).group_by(
            Comparison.id
        )

        # 根据 order 参数排序
        if args['order'] == 'latest':
            query = query.order_by(Comparison.created_at.desc())  # 按最新发表排序
        elif args['order'] == 'added':
            query = query.order_by(Comparison.added_count.desc())  # 按添加量排序
        elif args['order'] == 'fav':
            query = query.order_by(func.count(ComparisonFav.id).desc())  # 按收藏量排序

        # 分页查询
        pagination = query.paginate(page=args['page'], per_page=args['limit'], error_out=False)
        comparisons = [{
            'id': comparison.id,
            'title': comparison.title,
            'content': comparison.content[:100] + '...' if len(
                comparison.content) > 100 else comparison.content,
            'share_flag': comparison.share_flag,
            'created_at': comparison.created_at.strftime('%Y-%m-%d %H:%M'),  # 格式化时间
            'author': customer_email if customer_email else '匿名用户',  # 返回用户 email
            'fav_count': fav_count  # 添加收藏量
        } for comparison, fav_count, customer_email in pagination.items]

        # 返回结果
        return APIResponse.success({
            'data': comparisons,
            'total': pagination.total,
            'current_page': pagination.page,
            'per_page': pagination.per_page
        })


# 编辑术语列表
class EditComparisonResource(Resource):
    @require_valid_token
    @jwt_required()
    def post(self, id):
        """编辑术语表"""
        comparison = Comparison.query.filter_by(
            id=id,
            customer_id=get_jwt_identity()
        ).first_or_404()

        data = request.form
        if 'title' in data:
            comparison.title = data['title']
        if 'origin_lang' in data:
            comparison.origin_lang = data['origin_lang']
        if 'target_lang' in data:
            comparison.target_lang = data['target_lang']
        if 'share_flag' in data:
            comparison.share_flag = data['share_flag']
        if 'added_count' in data:
            try:
                comparison.added_count = int(data['added_count'])
            except ValueError:
                return APIResponse.error("无效的 added_count 格式", 400)

        # 更新 content
        content_list = []
        for key, value in data.items():
            if key.startswith('content[') and '][origin]' in key:
                # 提取索引
                index = key.split('[')[1].split(']')[0]
                origin = value
                target = data.get(f'content[{index}][target]', '')
                content_list.append(f"{origin}: {target}")

        # 将 content_list 转换为字符串
        content_str = '; '.join(content_list)
        comparison.content = content_str

        # 获取应用配置中的时区
        timezone_str = current_app.config['TIMEZONE']
        timezone = pytz.timezone(timezone_str)

        # 更新 updated_at 字段
        comparison.updated_at = datetime.now(timezone)

        db.session.commit()
        return APIResponse.success(message='术语表更新成功')


# 更新术语表共享状态
class ShareComparisonResource(Resource):
    @require_valid_token
    @jwt_required()
    def post(self, id):
        """修改共享状态[^4]"""
        comparison = Comparison.query.filter_by(
            id=id,
            customer_id=get_jwt_identity()
        ).first_or_404()

        data = request.form
        if 'share_flag' not in data or data['share_flag'] not in ['Y', 'N']:
            return APIResponse.error('share_flag 参数无效', 400)

        comparison.share_flag = data['share_flag']
        db.session.commit()
        return APIResponse.success(message='共享状态已更新')


# 复制到我的术语库
class CopyComparisonResource(Resource):
    @require_valid_token
    @jwt_required()
    def post(self, id):
        """复制到我的术语库[^5]"""
        comparison = Comparison.query.filter_by(
            id=id,
            share_flag='Y'
        ).first_or_404()

        new_comparison = Comparison(
            title=f"{comparison.title} (副本)",
            content=comparison.content,
            origin_lang=comparison.origin_lang,
            target_lang=comparison.target_lang,
            customer_id=get_jwt_identity(),
            share_flag='N'
        )
        db.session.add(new_comparison)
        db.session.commit()
        return APIResponse.success({
            'new_id': new_comparison.id
        })


# 收藏/取消收藏
class FavoriteComparisonResource(Resource):
    @require_valid_token
    @jwt_required()
    def post(self, id):
        """收藏/取消收藏[^6]"""
        comparison = Comparison.query.filter_by(id=id).first_or_404()
        customer_id = get_jwt_identity()

        favorite = ComparisonFav.query.filter_by(
            comparison_id=id,
            customer_id=customer_id
        ).first()

        if favorite:
            db.session.delete(favorite)
            message = '已取消收藏'
        else:
            new_favorite = ComparisonFav(
                comparison_id=id,
                customer_id=customer_id
            )
            db.session.add(new_favorite)
            message = '已收藏'

        db.session.commit()
        return APIResponse.success(message=message)


# 创建新术语表
class CreateComparisonResource(Resource):
    @require_valid_token
    @jwt_required()
    def post(self):
        """创建新术语表[^1]"""
        data = request.form
        required_fields = ['title', 'share_flag', 'origin_lang', 'target_lang']
        if not all(field in data for field in required_fields):
            return APIResponse.error('缺少必要参数', 400)

        # 解析 content 参数
        content_list = []
        for key, value in data.items():
            if key.startswith('content[') and '][origin]' in key:
                # 提取索引
                index = key.split('[')[1].split(']')[0]
                origin = value
                target = data.get(f'content[{index}][target]', '')
                content_list.append(f"{origin}: {target}")

        # 将 content_list 转换为字符串
        content_str = '; '.join(content_list)

        # 获取应用配置中的时区
        timezone_str = current_app.config['TIMEZONE']
        timezone = pytz.timezone(timezone_str)


        # 获取当前时间
        current_time = datetime.now(timezone)

        # 创建术语表
        comparison = Comparison(
            title=data['title'],
            origin_lang=data['origin_lang'],
            target_lang=data['target_lang'],
            content=content_str,  # 插入转换后的 content 字符串
            customer_id=get_jwt_identity(),
            share_flag=data.get('share_flag', 'N'),
            created_at=current_time,  # 显式赋值
            updated_at=current_time  # 显式赋值
        )
        db.session.add(comparison)
        db.session.commit()
        return APIResponse.success({
            'id': comparison.id
        })


# 删除术语表
class DeleteComparisonResource(Resource):
    @require_valid_token
    @jwt_required()
    def delete(self, id):
        """删除术语表[^2]"""
        comparison = Comparison.query.filter_by(
            id=id,
            customer_id=get_jwt_identity()
        ).first_or_404()

        db.session.delete(comparison)
        db.session.commit()
        return APIResponse.success(message='删除成功')


# 下载模板文件
class DownloadTemplateResource(Resource):
    def get(self):
        """下载模板文件[^3]"""
        from flask import send_file
        import os

        # 静态模板文件路径
        template_path = os.path.join(current_app.root_path, 'static', 'templates', '术语表模板.xlsx')
        
        # 检查文件是否存在
        if not os.path.exists(template_path):
            return APIResponse.error('模板文件不存在', 404)

        return send_file(
            template_path,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='术语表模板.xlsx'
        )


# 导入术语表
class ImportComparisonResource(Resource):
    @require_valid_token
    @jwt_required()
    def post(self):
        """
        导入 Excel 文件
        """
        print("开始导入文件")
        # 检查是否上传了文件
        if 'file' not in request.files:
            print("未找到文件")
            return APIResponse.error('未选择文件', 400)
        file = request.files['file']
        print(f"文件信息: {file.filename}, 文件大小: {len(file.read()) if hasattr(file, 'read') else 'unknown'}")
        file.seek(0)  # 重置文件指针

        try:
            # 读取 Excel 文件
            import pandas as pd
            df = pd.read_excel(file, header=None)  # 不指定header，按行读取
            
            # 添加调试信息
            print(f"文件行数: {len(df)}")
            print(f"文件列数: {len(df.columns) if len(df) > 0 else 0}")
            if len(df) >= 6:
                print(f"第6行内容: {df.iloc[5].tolist()}")
            if len(df) >= 2:
                print(f"第2行内容: {df.iloc[1].tolist()}")
            if len(df) >= 4:
                print(f"第4行内容: {df.iloc[3].tolist()}")

            # 检查文件是否包含所需的列（验证逻辑不变）
            # 从第6行开始查找列标题
            if len(df) < 6:
                return APIResponse.error(f'请正确填写语义对照表后再上传', 406)
            row = df.iloc[0]
            if '术语表标题' not in row.values:
                return APIResponse.error(f'请获取正确的导入模板并按格式填写上传', 406)
            row = df.iloc[2]
            if '源语种' not in row.values or '对照语种' not in row.values:
                return APIResponse.error(f'请获取正确的导入模板并按格式填写上传', 406)
            row = df.iloc[4]
            if '源术语' not in row.values or '目标术语' not in row.values:
                return APIResponse.error(f'请获取正确的导入模板并按格式填写上传', 406)
            
            # 检查第6行是否有数据（不是列标题行）
            row_6 = df.iloc[5]  # 第6行（索引5）
            print(f"第6行内容: {row_6.tolist()}")
            
            # 直接使用A列和B列作为源术语和目标术语
            source_col = 0  # A列
            target_col = 1  # B列
            
            # 从第6行开始解析术语数据
            content_list = []
            for i in range(5, len(df)):  # 从第6行开始（索引5）
                row = df.iloc[i]
                source_term = row[source_col]
                target_term = row[target_col]
                
                # 检查是否为空值
                if pd.notna(source_term) and pd.notna(target_term) and str(source_term).strip() and str(target_term).strip():
                    content_list.append(f"{str(source_term).strip()}: {str(target_term).strip()}")
            
            content = '; '.join(content_list)
            
            # 尝试从模板中获取额外信息，如果缺少则使用默认值
            title = '导入的术语表'
            origin_lang = '未知'
            target_lang = '未知'
            
            # 检查是否有术语表标题（A2单元格）
            if len(df) >= 2 and pd.notna(df.iloc[1, 0]):
                title_value = str(df.iloc[1, 0]).strip()
                if title_value and title_value != '术语表标题':
                    title = title_value
            
            # 检查是否有源语种和对照语种信息（A4和B4单元格）
            if len(df) >= 4:
                # 从第4行获取语言信息
                if pd.notna(df.iloc[3, 0]):  # A4单元格
                    origin_lang = str(df.iloc[3, 0]).strip()
                if pd.notna(df.iloc[3, 1]):  # B4单元格
                    target_lang = str(df.iloc[3, 1]).strip()
            
            # 创建术语表
            comparison = Comparison(
                title=title,
                origin_lang=origin_lang,
                target_lang=target_lang,
                content=content,
                customer_id=get_jwt_identity(),
                share_flag='N'
            )
            db.session.add(comparison)
            db.session.commit()

            # 返回成功响应
            return APIResponse.success({
                'id': comparison.id
            })
        except Exception as e:
            # 捕获并返回错误信息
            return APIResponse.error(f"文件导入失败：{str(e)}", 500)


# 导出单个术语表
class ExportComparisonResource(Resource):
    @require_valid_token
    @jwt_required()
    def get(self, id):
        """
        导出单个术语表
        """
        # 获取当前用户 ID
        current_user_id = get_jwt_identity()

        # 查询术语表
        comparison = Comparison.query.get_or_404(id)
        print(comparison.customer_id, current_user_id)
        # 检查术语表是否共享或属于当前用户
        if comparison.share_flag == 'Y' or comparison.customer_id != int(current_user_id):
            return {'message': '术语表未共享或无权限访问', 'code': 403}, 403

        # 解析术语内容
        terms = [term.split(': ') for term in comparison.content.split(';')]  # 按 ': ' 分割
        df = pd.DataFrame(terms, columns=['源术语', '目标术语'])

        # 创建 Excel 文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        # 返回文件下载响应
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'{comparison.title}.xlsx'
        )


class ExportComparisonResource6666(Resource):
    def get(self, id):
        """导出单个术语表[^5]"""
        comparison = Comparison.query.get_or_404(id)
        if comparison.share_flag != 'Y':
            return APIResponse.error('术语表未共享', 403)

        from flask import send_file
        from io import BytesIO
        import pandas as pd

        # 解析术语内容
        terms = [term.split(',') for term in comparison.content.split(';')]
        df = pd.DataFrame(terms, columns=['源术语', '目标术语'])

        # 创建 Excel 文件
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'{comparison.title}.xlsx'
        )


# 批量导出所有术语表
class ExportAllComparisonsResource(Resource):
    @require_valid_token
    @jwt_required()
    def get(self):
        """
        批量导出所有术语表
        """
        # 获取当前用户 ID
        current_user_id = get_jwt_identity()

        # 查询当前用户的所有术语表
        comparisons = Comparison.query.filter_by(customer_id=current_user_id).all()

        # 创建 ZIP 文件
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            for comparison in comparisons:
                # 解析术语内容
                terms = [term.split(': ') for term in comparison.content.split(';')]  # 按 ': ' 分割
                df = pd.DataFrame(terms, columns=['源术语', '目标术语'])

                # 创建 Excel 文件
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                output.seek(0)

                # 将 Excel 文件添加到 ZIP 中
                zf.writestr(f"{comparison.title}.xlsx", output.getvalue())

        memory_file.seek(0)

        # 返回 ZIP 文件下载响应
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'术语表_{datetime.now().strftime("%Y%m%d")}.zip'
        )
