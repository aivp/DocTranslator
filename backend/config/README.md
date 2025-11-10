# Qwen-MT翻译配置说明

## 概述
这个配置文件用于配置阿里云Qwen-MT翻译模型，支持上下文翻译和术语库。

## 快速配置

### 1. 设置API密钥
```bash
export DASH_SCOPE_KEY="your-dashscope-api-key"
```

### 2. 启用Qwen翻译
```bash
export ENABLE_QWEN="True"
export QWEN_MODEL="qwen-mt-plus"
```

### 3. Docker配置
```yaml
# docker-compose.yml
environment:
  - DASH_SCOPE_KEY=your-dashscope-api-key
  - ENABLE_QWEN=True
  - QWEN_MODEL=qwen-mt-plus
```

## 配置选项

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `DASH_SCOPE_KEY` | 阿里云API密钥 | 需要设置 |
| `ENABLE_QWEN` | 是否启用Qwen翻译 | `True` |
| `QWEN_MODEL` | Qwen模型名称 | `qwen-mt-plus` |
| `QWEN_SOURCE_LANG` | 默认源语言 | `auto` |

## 使用方法

### 在翻译任务中启用Qwen
在创建翻译任务时，设置 `server` 参数为 `'qwen'`：

```python
trans_config = {
    'server': 'qwen',  # 使用Qwen翻译
    'lang': 'zh',      # 目标语言
    # ... 其他配置
}
```

### 功能特点
- ✅ 支持上下文翻译
- ✅ 支持术语库
- ✅ 支持领域定制
- ✅ 支持多语言翻译
- ✅ 完善的错误处理

## 调试

系统会在翻译开始时打印配置：
```
=== Qwen翻译配置 ===
启用Qwen: True
Qwen模型: qwen-mt-plus
默认源语言: auto
Qwen服务检查: Qwen翻译服务正常
===================
```

## 注意事项

1. 必须设置有效的 `DASH_SCOPE_KEY`
2. 修改配置后需要重启翻译服务
3. 建议在测试环境中先验证效果
4. 如果Qwen服务不可用，系统会使用备用方案 