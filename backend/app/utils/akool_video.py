import requests
import os
import json
import time
from flask import current_app
from typing import Dict, List, Optional


class AkoolVideoService:
    """Akool视频翻译服务"""
    
    # 类级别的token缓存
    _cached_token = None
    _token_expires_at = 0
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        self.client_id = client_id or os.getenv('CLIENT_ID') or os.getenv('AKOOL_CLIENT_ID') or os.getenv('client_Id')
        self.client_secret = client_secret or os.getenv('CLIENT_SECRET') or os.getenv('AKOOL_CLIENT_SECRET') or os.getenv('client_Secret')
        self.base_url = "https://openapi.akool.com/api/open/v3"
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Akool Client ID and Client Secret are required")
        
        # 获取或使用缓存的访问令牌
        self.access_token = self._get_or_refresh_token()

    def _get_or_refresh_token(self):
        """获取或刷新访问令牌（带缓存）"""
        current_time = time.time()
        
        # 如果缓存token存在且未过期，直接使用
        if (self._cached_token and 
            self._token_expires_at > current_time):
            current_app.logger.info("使用缓存的Akool访问令牌")
            return self._cached_token
        
        # 获取新token
        try:
            url = f"{self.base_url}/getToken"
            data = {
                'clientId': self.client_id,
                'clientSecret': self.client_secret
            }
            headers = {
                'Content-Type': 'application/json'
            }
            
            current_app.logger.info("正在获取新的Akool访问令牌...")
            current_app.logger.info(f"请求URL: {url}")
            current_app.logger.info(f"请求数据: {data}")
            response = requests.post(url, headers=headers, json=data)
            current_app.logger.info(f"响应状态码: {response.status_code}")
            current_app.logger.info(f"响应内容: {response.text}")
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') == 1000:
                token = result.get('token')
                
                # 缓存token，设置过期时间（提前1小时过期）
                self._cached_token = token
                # Akool token有效期超过1年，我们设置11个月后过期
                self._token_expires_at = current_time + (11 * 30 * 24 * 3600)
                
                current_app.logger.info("成功获取并缓存Akool访问令牌")
                return token
            else:
                error_msg = result.get('msg', 'Unknown error')
                current_app.logger.error(f"获取访问令牌失败: {error_msg}")
                raise Exception(f"获取访问令牌失败: {error_msg}")
                
        except Exception as e:
            current_app.logger.error(f"获取访问令牌异常: {str(e)}")
            raise

    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """发送HTTP请求"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=data)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Akool API请求失败: {str(e)}")
            # 如果是401错误，可能是token过期，清除缓存并重试一次
            if hasattr(e, 'response') and e.response and e.response.status_code == 401:
                current_app.logger.warning("Token可能已过期，清除缓存并重试...")
                self._cached_token = None
                self._token_expires_at = 0
                # 重新获取token
                self.access_token = self._get_or_refresh_token()
                # 重试请求
                headers = {
                    'Authorization': f'Bearer {self.access_token}',
                    'Content-Type': 'application/json'
                }
                if method.upper() == 'GET':
                    response = requests.get(url, headers=headers, params=data)
                elif method.upper() == 'POST':
                    response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()
            raise

    def get_languages(self) -> List[Dict]:
        """获取支持的语言列表"""
        try:
            current_app.logger.info(f"正在获取Akool语言列表，Token: {self.access_token[:20]}...")
            result = self._make_request('GET', '/language/list')
            current_app.logger.info(f"Akool API响应: {result}")
            
            if result.get('code') == 1000:
                lang_list = result.get('data', {}).get('lang_list', [])
                current_app.logger.info(f"成功获取语言列表，共{len(lang_list)}种语言")
                return lang_list
            else:
                error_msg = result.get('msg', 'Unknown error')
                current_app.logger.error(f"获取语言列表失败: {error_msg}")
                return []
        except Exception as e:
            current_app.logger.error(f"获取语言列表异常: {str(e)}")
            return []

    def create_translation(self, video_url: str, source_language: str, 
                          target_language: str, lipsync: bool = False, 
                          webhook_url: str = None, speaker_num: int = 0) -> Dict:
        """创建视频翻译任务"""
        data = {
            'url': video_url,
            'source_language': source_language,
            'language': target_language,
            'lipsync': lipsync,
            'speaker_num': speaker_num
        }
        
        if webhook_url:
            data['webhookUrl'] = webhook_url
            
        try:
            result = self._make_request('POST', '/content/video/createbytranslate', data)
            if result.get('code') == 1000:
                return result.get('data', {})
            else:
                error_msg = result.get('msg', 'Unknown error')
                current_app.logger.error(f"创建翻译任务失败: {error_msg}")
                raise Exception(f"Akool API错误: {error_msg}")
        except Exception as e:
            current_app.logger.error(f"创建翻译任务异常: {str(e)}")
            raise

    def get_task_status(self, task_id: str) -> Dict:
        """查询翻译任务状态"""
        try:
            result = self._make_request('GET', f'/content/video/infobymodelid?video_model_id={task_id}')
            if result.get('code') == 1000:
                return result.get('data', {})
            else:
                error_msg = result.get('msg', 'Unknown error')
                current_app.logger.error(f"查询任务状态失败: {error_msg}")
                return {}
        except Exception as e:
            current_app.logger.error(f"查询任务状态异常: {str(e)}")
            return {}

    def check_video_expiration(self):
        """检查视频是否过期（7天）"""
        from datetime import datetime, timedelta
        from app.models.video_translate import VideoTranslate
        
        # 查找7天前完成但未标记为过期的视频
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        
        expired_videos = VideoTranslate.query.filter(
            VideoTranslate.status == 'completed',
            VideoTranslate.expires_at <= datetime.utcnow(),
            VideoTranslate.deleted_flag == 'N'
        ).all()
        
        for video in expired_videos:
            video.status = 'expired'
            current_app.logger.info(f"视频 {video.filename} 已过期")
        
        if expired_videos:
            from app.extensions import db
            db.session.commit()
            
        return len(expired_videos)
    
    @classmethod
    def clear_token_cache(cls):
        """清除token缓存（用于测试或强制刷新）"""
        cls._cached_token = None
        cls._token_expires_at = 0
        current_app.logger.info("已清除Akool token缓存")
    
    @classmethod
    def get_token_info(cls):
        """获取当前token缓存信息"""
        current_time = time.time()
        expires_in = cls._token_expires_at - current_time if cls._token_expires_at > current_time else 0
        
        return {
            'has_token': cls._cached_token is not None,
            'expires_in_seconds': expires_in,
            'expires_in_days': expires_in / (24 * 3600) if expires_in > 0 else 0,
            'is_expired': expires_in <= 0
        }
