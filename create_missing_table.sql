CREATE TABLE IF NOT EXISTS `website_medicalreport` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `report_file` varchar(100) DEFAULT NULL,
  `analysis` longtext NOT NULL,
  `uploaded_at` datetime(6) NOT NULL,
  `user_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `website_medicalreport_user_id_idx` (`user_id`),
  CONSTRAINT `website_medicalreport_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
