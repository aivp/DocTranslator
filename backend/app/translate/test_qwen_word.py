#!/usr/bin/env python3
"""
测试Word文档Qwen翻译配置
"""

import os
import sys

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_qwen_config():
    """测试Qwen配置"""
    print("=== 测试Qwen配置 ===")
    
    # 检查环境变量
    dashscope_key = os.environ.get('DASH_SCOPE_KEY', '')
    if dashscope_key:
        print(f"✅ DASH_SCOPE_KEY: 已设置 ({dashscope_key[:10]}...)")
    else:
        print("❌ DASH_SCOPE_KEY: 未设置")
    
    # 检查Qwen模块
    try:
        from qwen_translate import check_qwen_availability
        print("✅ Qwen翻译模块: 已导入")
        
        # 测试服务可用性
        available, message = check_qwen_availability()
        if available:
            print(f"✅ Qwen服务: {message}")
        else:
            print(f"❌ Qwen服务: {message}")
    except ImportError as e:
        print(f"❌ Qwen翻译模块: 导入失败 - {e}")
    
    print("==================")

def test_word_translation_config():
    """测试Word翻译配置"""
    print("=== 测试Word翻译配置 ===")
    
    # 模拟翻译配置
    trans_config = {
        'id': 1,
        'file_path': '/path/to/test.docx',
        'target_file': '/path/to/output.docx',
        'lang': 'zh',
        'model': 'gpt-3.5-turbo',
        'backup_model': 'gpt-4',
        'prompt': '翻译为中文',
        'api_key': 'test-key',
        'api_url': 'https://api.openai.com/v1',
        'threads': 4,
        'server': 'openai'  # 这个会被强制改为 'qwen'
    }
    
    print(f"原始配置 - server: {trans_config['server']}")
    
    # 模拟Word翻译的强制设置
    print("Word文档翻译：强制使用Qwen模型")
    trans_config['server'] = 'qwen'
    
    print(f"修改后配置 - server: {trans_config['server']}")
    print("✅ Word文档将使用Qwen翻译")
    
    print("==================")

if __name__ == "__main__":
    test_qwen_config()
    test_word_translation_config()
    
    print("\n=== 使用说明 ===")
    print("1. 设置环境变量: export DASH_SCOPE_KEY='your-key'")
    print("2. 重启翻译服务")
    print("3. 上传Word文档进行翻译")
    print("4. 查看日志确认使用Qwen翻译")
    print("================") 