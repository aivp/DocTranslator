import os

import requests
import time
from flask import current_app


class Doc2XService:
    BASE_URL = "https://v2.doc2x.noedgeai.com/api/v2"

    @staticmethod
    def _make_request(api_key, method, endpoint, data=None, files=None):
        """统一请求方法"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        } if method != "upload" else {
            "Authorization": f"Bearer {api_key}"
        }

        url = f"{Doc2XService.BASE_URL}/{endpoint}"
        try:
            if method == "upload":
                response = requests.post(url, headers=headers, data=files)
            else:
                response = requests.request(
                    method.lower(),
                    url,
                    headers=headers,
                    json=data if data else None
                )

            result = response.json()
            if result.get("code") != "success":
                error_msg = result.get("msg", "API 请求失败")
                # 提供更友好的错误信息
                if "文件不合法" in error_msg:
                    error_msg = "上传的文件格式不支持或文件损坏，请检查是否为有效的PDF文件"
                elif "文件过大" in error_msg:
                    error_msg = "文件大小超过限制，请压缩文件后重试"
                elif "API密钥" in error_msg or "key" in error_msg.lower():
                    error_msg = "API密钥无效或已过期，请检查密钥设置"
                raise Exception(error_msg)
            return result["data"]
        except Exception as e:
            current_app.logger.error(f"doc2x 请求失败: {str(e)}")
            raise

    @staticmethod
    def start_task(api_key: str, file_path: str) -> str:
        """阶段1: 启动任务 (parse/pdf)"""
        # 验证文件是否存在
        if not os.path.exists(file_path):
            raise Exception(f"文件不存在: {file_path}")
        
        # 验证文件大小
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise Exception("文件为空，无法处理")
        
        # 验证文件扩展名
        if not file_path.lower().endswith('.pdf'):
            raise Exception("只支持PDF文件格式")
        
        # 验证文件是否可读
        try:
            with open(file_path, 'rb') as f:
                # 读取文件头部验证PDF格式
                header = f.read(4)
                if header != b'%PDF':
                    raise Exception("文件不是有效的PDF格式")
                f.seek(0)  # 重置文件指针
                
                return Doc2XService._make_request(
                    api_key,
                    "upload",
                    "parse/pdf",
                    files=f
                )["uid"]
        except Exception as e:
            if "文件不是有效的PDF格式" in str(e):
                raise e
            raise Exception(f"文件读取失败: {str(e)}")

    @staticmethod
    def check_parse_status(api_key: str, uid: str) -> dict:
        """检查解析状态"""
        data = Doc2XService._make_request(
            api_key,
            "GET",
            f"parse/status?uid={uid}"
        )

        # 确保包含所有doc2x可能返回的状态
        if "status" not in data:
            raise Exception("无效的API响应：缺少status字段")

        return {
            "status": data["status"],  # processing/success/failed
            "progress": data.get("progress", 0),
            "detail": data.get("detail", "")
        }

    @staticmethod
    def trigger_export(api_key: str, uid: str, filename: str) -> bool:
        """触发导出（返回是否成功触发）"""
        data = {
            "uid": uid,
            "to": "docx",  # 导出为Word文档
            "formula_mode": "normal",
            "filename": f"{filename}.docx"  # 确保扩展名正确
        }
        result = Doc2XService._make_request(
            api_key,
            "POST",
            "convert/parse",
            data=data
        )
        return result.get("status") == "processing"

    @staticmethod
    def download_file(url: str, save_path: str) -> bool:
        """下载文件并验证完整性"""
        try:
            # 创建临时文件
            temp_path = f"{save_path}.tmp"

            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(temp_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            # 验证文件大小
            if os.path.getsize(temp_path) == 0:
                raise Exception("下载文件为空")

            # 重命名为正式文件
            os.rename(temp_path, save_path)
            return True

        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            current_app.logger.error(f"文件下载失败: {str(e)}")
            raise

    @staticmethod
    def check_export_status(api_key: str, uid: str, timeout=300) -> str:
        """阶段4: 轮询导出结果 (convert/parse/result)"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            data = Doc2XService._make_request(
                api_key,
                "GET",
                f"convert/parse/result?uid={uid}"
            )
            if data["status"] == "success":
                return data["url"]
            elif data["status"] == "failed":
                raise Exception("导出任务失败")
            time.sleep(2)  # 合理轮询间隔
        raise TimeoutError("导出结果等待超时")
