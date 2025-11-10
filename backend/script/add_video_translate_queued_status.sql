-- 为video_translate表添加'queued'状态
-- 执行前请备份数据库

-- 修改status字段的ENUM类型，添加'queued'状态
ALTER TABLE video_translate 
MODIFY COLUMN status ENUM('uploaded', 'queued', 'processing', 'completed', 'failed', 'expired') 
DEFAULT 'uploaded' 
COMMENT '翻译状态';

-- 验证修改是否成功
SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_DEFAULT, COLUMN_COMMENT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'video_translate' 
AND COLUMN_NAME = 'status';

