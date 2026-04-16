CREATE DATABASE IF NOT EXISTS metabase CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'metabase_user'@'%' IDENTIFIED WITH mysql_native_password BY 'metabase_password';
GRANT ALL PRIVILEGES ON metabase.* TO 'metabase_user'@'%';
FLUSH PRIVILEGES;
