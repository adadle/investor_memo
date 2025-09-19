create database;

-- 每日收益数据
CREATE TABLE `daily_profit` (
  `id` int NOT NULL AUTO_INCREMENT,
  `data_date` date NOT NULL,
  `channel` varchar(10) NOT NULL,
  `is_tx_date` tinyint(1) DEFAULT NULL,
  `profit` decimal(14,2) DEFAULT NULL,
  `last_update_time` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `data_date` (`data_date`,`channel`)
) ENGINE=InnoDB AUTO_INCREMENT=1037 DEFAULT CHARSET=utf8mb3