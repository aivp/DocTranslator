from flask_restful import Resource
from app.models.setting import Setting
from app.utils.response import APIResponse
from flask import current_app


class SystemVersionResource(Resource):
    def get(self):
        """获取站点设置"""
        settings = Setting.query.filter_by(group='site_setting').all()
        if not settings:
            return APIResponse.success(data={'version': 'community'})
        data = {
            'version': settings[0].value,
            'site_title': settings[1].value,
            'site_name': settings[2].value,
            'update_time': settings[3].remark or None,
            'site_logo': settings[3].value,
        }
        return APIResponse.success(data=data)


class SystemSettingsResource(Resource):
    def get(self):
        settings = Setting.query.filter_by(group='site_setting').all()
        if not settings:
            return APIResponse.success(data={'version': 'community'})
        data = {
            'version': settings[0].value,
            'site_title': settings[1].value,
            'site_name': settings[2].value,
            'site_logo': settings[3].value,
            'update_time': settings[3].remark or None,
        }
        return APIResponse.success({
            'site_setting': data,
            'api_setting': {
                'api_url': current_app.config['API_URL'],
                'models': current_app.config['TRANSLATE_MODELS']
            },
            'message': 'success'
        })
