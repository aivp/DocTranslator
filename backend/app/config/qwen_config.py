# Qwen翻译配置文件
# 用于配置Qwen-MT翻译模型

import os

def get_env_or_default(key, default):
    """从环境变量获取配置，如果没有则使用默认值"""
    return os.environ.get(key, default)

# Qwen翻译配置
QWEN_CONFIG = {
    # 是否启用Qwen翻译
    'enable_qwen': get_env_or_default('ENABLE_QWEN', 'True').lower() == 'true',
    
    # Qwen模型名称
    'qwen_model': get_env_or_default('QWEN_MODEL', 'qwen-mt-plus'),
    
    # 默认源语言
    'default_source_lang': get_env_or_default('QWEN_SOURCE_LANG', 'auto'),
}

def is_qwen_enabled():
    """是否启用Qwen翻译"""
    return QWEN_CONFIG.get('enable_qwen', True)

def get_qwen_model():
    """获取Qwen模型名称"""
    return QWEN_CONFIG.get('qwen_model', 'qwen-mt-plus')

def get_qwen_source_lang():
    """获取Qwen默认源语言"""
    return QWEN_CONFIG.get('default_source_lang', 'auto')

def print_qwen_config():
    """打印Qwen配置（用于调试）"""
    print("=== Qwen翻译配置 ===")
    print(f"启用Qwen: {is_qwen_enabled()}")
    print(f"Qwen模型: {get_qwen_model()}")
    print(f"默认源语言: {get_qwen_source_lang()}")
    print("===================") 