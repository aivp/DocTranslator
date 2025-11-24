# -*- coding: utf-8 -*-
"""
Token使用记录工具
用于记录每次API调用的token使用情况
支持在子进程环境中运行（不依赖Flask应用上下文）
"""
import logging
from datetime import datetime
from app.utils.token_counter import count_tokens_from_api_response

# 尝试导入 db_simple（用于子进程环境）
try:
    from app.translate.db_simple import execute
    USE_DB_SIMPLE = True
except ImportError:
    USE_DB_SIMPLE = False
    # 如果在主进程中，可以使用 Flask-SQLAlchemy
    try:
        from app.extensions import db
        from app.models.token_usage import TokenUsage
    except ImportError:
        pass


def record_token_usage(
    translate_id: int,
    customer_id: int,
    tenant_id: int,
    uuid: str = None,
    completion=None,
    input_text: str = None,
    translated_text: str = None,
    model: str = "qwen-mt-plus",
    server: str = "qwen",
    api_duration_ms: int = None,
    status: str = "success",
    error_message: str = None,
    retry_count: int = 0,
    terms_tokens: int = 0
):
    """
    记录token使用情况到数据库
    
    Args:
        translate_id: 翻译任务ID
        customer_id: 用户ID
        tenant_id: 租户ID
        uuid: 翻译任务UUID
        completion: API响应对象
        input_text: 输入文本
        translated_text: 翻译后的文本（可选）
        model: 使用的模型
        server: 使用的服务
        api_duration_ms: API调用耗时（毫秒）
        status: 调用状态（success/failed）
        error_message: 错误信息（如果失败）
        retry_count: 重试次数
        terms_tokens: 术语表的token数量（计入输入token）
    """
    try:
        # 计算token使用量
        if completion:
            token_info = count_tokens_from_api_response(completion, input_text, model)
        else:
            # 如果completion为None（失败情况），手动计算
            from app.utils.token_counter import count_qwen_tokens
            token_info = {
                'input_tokens': count_qwen_tokens(input_text, model) if input_text else 0,
                'output_tokens': 0,
                'total_tokens': 0
            }
            if translated_text:
                token_info['output_tokens'] = count_qwen_tokens(translated_text, model)
            token_info['total_tokens'] = token_info['input_tokens'] + token_info['output_tokens']
        
        # 如果没有从API响应中获取到token信息，使用翻译后的文本计算
        if token_info['output_tokens'] == 0 and translated_text:
            from app.utils.token_counter import count_qwen_tokens
            token_info['output_tokens'] = count_qwen_tokens(translated_text, model)
            token_info['total_tokens'] = token_info['input_tokens'] + token_info['output_tokens']
        
        # 将术语表的token加入到输入token中
        if terms_tokens > 0:
            token_info['input_tokens'] += terms_tokens
            token_info['total_tokens'] = token_info['input_tokens'] + token_info['output_tokens']
            logging.debug(f"术语表token已加入: {terms_tokens} tokens")
        
        # 准备文本预览（前500字符）
        text_preview = (input_text[:500] if input_text else "")[:500]  # 确保不超过500字符
        
        # 使用 db_simple 执行 SQL（支持子进程环境）
        if USE_DB_SIMPLE:
            # 使用原始 SQL 插入（不依赖 Flask 应用上下文）
            sql = """
                INSERT INTO token_usage (
                    translate_id, customer_id, tenant_id, uuid,
                    input_tokens, output_tokens, total_tokens,
                    model, server,
                    text_length, translated_text_length, text_preview,
                    api_call_time, api_duration, status, error_message, retry_count,
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    NOW(), NOW()
                )
            """
            now = datetime.utcnow()
            success = execute(
                sql,
                translate_id, customer_id, tenant_id, uuid or "",
                token_info['input_tokens'], token_info['output_tokens'], token_info['total_tokens'],
                model, server,
                len(input_text) if input_text else 0,
                len(translated_text) if translated_text else 0,
                text_preview,
                now, api_duration_ms, status, error_message, retry_count
            )
            if success:
                logging.info(f"✅ Token使用记录已保存: translate_id={translate_id}, input={token_info['input_tokens']}, output={token_info['output_tokens']}, total={token_info['total_tokens']}")
            else:
                logging.error(f"❌ Token使用记录保存失败: translate_id={translate_id}")
        else:
            # 使用 Flask-SQLAlchemy ORM（主进程环境）
            try:
                from app.extensions import db
                from app.models.token_usage import TokenUsage
                
                token_usage = TokenUsage(
                    translate_id=translate_id,
                    customer_id=customer_id,
                    tenant_id=tenant_id,
                    uuid=uuid or "",
                    input_tokens=token_info['input_tokens'],
                    output_tokens=token_info['output_tokens'],
                    total_tokens=token_info['total_tokens'],
                    model=model,
                    server=server,
                    text_length=len(input_text) if input_text else 0,
                    translated_text_length=len(translated_text) if translated_text else 0,
                    text_preview=text_preview,
                    api_call_time=datetime.utcnow(),
                    api_duration=api_duration_ms,
                    status=status,
                    error_message=error_message,
                    retry_count=retry_count
                )
                
                db.session.add(token_usage)
                db.session.commit()
                logging.info(f"✅ Token使用记录已保存: translate_id={translate_id}, input={token_info['input_tokens']}, output={token_info['output_tokens']}, total={token_info['total_tokens']}")
            except Exception as orm_error:
                logging.error(f"❌ 使用ORM保存token使用记录失败: {orm_error}", exc_info=True)
                if 'db' in locals():
                    db.session.rollback()
        
    except Exception as e:
        # 记录token使用失败不应该影响翻译流程，只记录错误日志
        logging.error(f"❌ 记录token使用失败: {e}", exc_info=True)


def aggregate_tokens_for_translate(translate_id: int):
    """
    汇总某个翻译任务的所有token使用，更新到translate表
    支持在子进程环境中运行（不依赖Flask应用上下文）
    
    Args:
        translate_id: 翻译任务ID
    """
    try:
        # 使用 db_simple 执行 SQL（支持子进程环境）
        if USE_DB_SIMPLE:
            from app.translate.db_simple import get_all, execute
            
            # 查询该任务的所有token使用记录（包括成功和失败）
            sql = """
                SELECT 
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    SUM(total_tokens) as total_tokens_sum
                FROM token_usage
                WHERE translate_id = %s
            """
            result = get_all(sql, translate_id)
            
            if result and len(result) > 0:
                total_input = result[0].get('total_input_tokens') or 0
                total_output = result[0].get('total_output_tokens') or 0
                total_tokens = result[0].get('total_tokens_sum') or 0
                
                # 更新 translate 表
                update_sql = """
                    UPDATE translate 
                    SET input_tokens = %s,
                        output_tokens = %s,
                        total_tokens = %s
                    WHERE id = %s
                """
                success = execute(update_sql, total_input, total_output, total_tokens, translate_id)
                if success:
                    logging.info(f"✅ Token汇总完成: translate_id={translate_id}, input={total_input}, output={total_output}, total={total_tokens}")
                else:
                    logging.error(f"❌ Token汇总更新失败: translate_id={translate_id}")
            else:
                logging.warning(f"⚠️ 未找到token使用记录: translate_id={translate_id}")
        else:
            # 使用 Flask-SQLAlchemy ORM（主进程环境）
            from app.extensions import db
            from app.models.translate import Translate
            from app.models.token_usage import TokenUsage
            
            # 查询该任务的所有成功调用的token使用
            token_usages = TokenUsage.query.filter_by(
                translate_id=translate_id,
                status='success'
            ).all()
            
            # 汇总token
            total_input_tokens = sum(usage.input_tokens for usage in token_usages)
            total_output_tokens = sum(usage.output_tokens for usage in token_usages)
            total_tokens = sum(usage.total_tokens for usage in token_usages)
            
            # 更新translate表
            translate = Translate.query.get(translate_id)
            if translate:
                translate.input_tokens = total_input_tokens
                translate.output_tokens = total_output_tokens
                translate.total_tokens = total_tokens
                db.session.commit()
                
                logging.info(f"✅ Token汇总完成: translate_id={translate_id}, input={total_input_tokens}, output={total_output_tokens}, total={total_tokens}")
            else:
                logging.warning(f"⚠️ 未找到翻译任务: translate_id={translate_id}")
            
    except Exception as e:
        logging.error(f"❌ 汇总token失败: translate_id={translate_id}, 错误: {e}", exc_info=True)
        # 只有在使用 ORM 时才需要 rollback
        if not USE_DB_SIMPLE:
            try:
                from app.extensions import db
                db.session.rollback()
            except:
                pass

