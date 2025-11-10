-- 创建 comparison_sub 表
CREATE TABLE IF NOT EXISTS `comparison_sub` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `comparison_sub_id` int(11) NOT NULL COMMENT '主表id',
  `original` varchar(200) DEFAULT NULL COMMENT '原文',
  `comparison_text` varchar(200) DEFAULT NULL COMMENT '对照术语',
  `sort_order` int(11) DEFAULT 0,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_flag` char(1) DEFAULT 'N',
  PRIMARY KEY (`id`),
  KEY `idx_comparison_sub_id` (`comparison_sub_id`),
  KEY `idx_sort_order` (`sort_order`),
  CONSTRAINT `fk_comparison_sub_comparison` FOREIGN KEY (`comparison_sub_id`) REFERENCES `comparison` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='术语子表';

-- 修改 comparison 表，将 content 字段改为可为空
ALTER TABLE `comparison` MODIFY COLUMN `content` text NULL COMMENT '术语内容（已废弃）'; 