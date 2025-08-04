
SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- 数据库： `trans`
--

-- --------------------------------------------------------

--
-- 表的结构 `alembic_version`
--

CREATE TABLE `alembic_version` (
  `version_num` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- --------------------------------------------------------

--
-- 表的结构 `comparison`
--

CREATE TABLE `comparison` (
  `id` int(11) NOT NULL,
  `title` text NOT NULL,
  `origin_lang` text NOT NULL,
  `target_lang` text NOT NULL,
  `share_flag` text,
  `added_count` int(11) DEFAULT NULL,
  `content` longtext NOT NULL,
  `customer_id` int(11) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `deleted_flag` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 表的结构 `comparison_fav`
--

CREATE TABLE `comparison_fav` (
  `id` int(11) NOT NULL,
  `comparison_id` int(11) NOT NULL,
  `customer_id` int(11) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------


-- --------------------------------------------------------

--
-- 表的结构 `customer`
--

CREATE TABLE `customer` (
  `id` int(11) NOT NULL,
  `customer_no` text,
  `phone` text,
  `name` text,
  `password` text NOT NULL,
  `email` text NOT NULL,
  `level` text,
  `status` text,
  `deleted_flag` text,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `storage` bigint(20) DEFAULT NULL,
  `total_storage` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------


--
-- 表的结构 `prompt`
--

CREATE TABLE `prompt` (
  `id` int(11) NOT NULL,
  `title` text NOT NULL,
  `share_flag` text,
  `added_count` int(11) DEFAULT NULL,
  `content` longtext NOT NULL,
  `customer_id` int(11) DEFAULT NULL,
  `created_at` date DEFAULT NULL,
  `updated_at` date DEFAULT NULL,
  `deleted_flag` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 表的结构 `prompt_fav`
--

CREATE TABLE `prompt_fav` (
  `id` int(11) NOT NULL,
  `prompt_id` int(11) NOT NULL,
  `customer_id` int(11) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 表的结构 `send_code`
--

CREATE TABLE `send_code` (
  `id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `send_type` int(11) NOT NULL,
  `send_to` text NOT NULL,
  `code` text NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 表的结构 `setting`
--

CREATE TABLE `setting` (
  `id` int(11) NOT NULL,
  `alias` text,
  `value` longtext,
  `serialized` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `deleted_flag` text,
  `group` text,
  `remark` varchar(255) DEFAULT NULL COMMENT '配置备注/版本标识'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 表的结构 `translate`
--

CREATE TABLE `translate` (
  `id` int(11) NOT NULL,
  `translate_no` text,
  `uuid` text,
  `customer_id` int(11) DEFAULT NULL,
  `rand_user_id` text,
  `origin_filename` text NOT NULL,
  `origin_filepath` text NOT NULL,
  `target_filepath` text NOT NULL,
  `status` text,
  `start_at` datetime DEFAULT NULL,
  `end_at` datetime DEFAULT NULL,
  `deleted_flag` text,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `origin_filesize` bigint(20) DEFAULT NULL,
  `target_filesize` bigint(20) DEFAULT NULL,
  `lang` text,
  `model` text,
  `prompt` text,
  `api_url` text,
  `api_key` text,
  `threads` int(11) DEFAULT NULL,
  `failed_reason` longtext,
  `failed_count` int(11) DEFAULT NULL,
  `word_count` int(11) DEFAULT NULL,
  `backup_model` text,
  `md5` text,
  `type` text,
  `origin_lang` text,
  `process` float DEFAULT NULL,
  `doc2x_flag` text,
  `doc2x_secret_key` text,
  `prompt_id` bigint(20) DEFAULT NULL,
  `comparison_id` bigint(20) DEFAULT NULL,
  `size` bigint(20) DEFAULT NULL,
  `server` text,
  `app_id` text,
  `app_key` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 表的结构 `user`
--

CREATE TABLE `user` (
  `id` int(11) NOT NULL,
  `name` text,
  `password` text NOT NULL,
  `email` text NOT NULL,
  `deleted_flag` text,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 表的结构 `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `email` varchar(120) NOT NULL,
  `username` varchar(50) DEFAULT NULL,
  `password_hash` varchar(256) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- 表的结构 `verification_codes`
--

CREATE TABLE `verification_codes` (
  `id` int(11) NOT NULL,
  `email` varchar(120) DEFAULT NULL,
  `code` varchar(6) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `is_used` tinyint(1) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- 转储表的索引
--

--
-- 表的索引 `alembic_version`
--
ALTER TABLE `alembic_version`
  ADD PRIMARY KEY (`version_num`(255));



--
-- 表的索引 `comparison`
--
ALTER TABLE `comparison`
  ADD PRIMARY KEY (`id`);

--
-- 表的索引 `comparison_fav`
--
ALTER TABLE `comparison_fav`
  ADD PRIMARY KEY (`id`);


--
-- 表的索引 `customer`
--
ALTER TABLE `customer`
  ADD PRIMARY KEY (`id`);

--
-- 表的索引 `income`
--
ALTER TABLE `income`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_year_region` (`year`,`region`);

--
-- 表的索引 `prompt`
--
ALTER TABLE `prompt`
  ADD PRIMARY KEY (`id`);

--
-- 表的索引 `prompt_fav`
--
ALTER TABLE `prompt_fav`
  ADD PRIMARY KEY (`id`);

--
-- 表的索引 `send_code`
--
ALTER TABLE `send_code`
  ADD PRIMARY KEY (`id`);

--
-- 表的索引 `setting`
--
ALTER TABLE `setting`
  ADD PRIMARY KEY (`id`);

--
-- 表的索引 `translate`
--
ALTER TABLE `translate`
  ADD PRIMARY KEY (`id`);

--
-- 表的索引 `user`
--
ALTER TABLE `user`
  ADD PRIMARY KEY (`id`);

--
-- 表的索引 `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ix_users_email` (`email`);

--
-- 表的索引 `verification_codes`
--
ALTER TABLE `verification_codes`
  ADD PRIMARY KEY (`id`),
  ADD KEY `ix_verification_codes_email` (`email`);

--
-- 在导出的表使用AUTO_INCREMENT
--

--
-- 使用表AUTO_INCREMENT `comparison`
--
ALTER TABLE `comparison`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- 使用表AUTO_INCREMENT `comparison_fav`
--
ALTER TABLE `comparison_fav`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;


--
-- 使用表AUTO_INCREMENT `customer`
--
ALTER TABLE `customer`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;


--
-- 使用表AUTO_INCREMENT `prompt`
--
ALTER TABLE `prompt`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- 使用表AUTO_INCREMENT `prompt_fav`
--
ALTER TABLE `prompt_fav`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- 使用表AUTO_INCREMENT `send_code`
--
ALTER TABLE `send_code`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- 使用表AUTO_INCREMENT `setting`
--
ALTER TABLE `setting`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- 使用表AUTO_INCREMENT `translate`
--
ALTER TABLE `translate`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- 使用表AUTO_INCREMENT `user`
--
ALTER TABLE `user`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- 使用表AUTO_INCREMENT `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- 使用表AUTO_INCREMENT `verification_codes`
--
ALTER TABLE `verification_codes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
