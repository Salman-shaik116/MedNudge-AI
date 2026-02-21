-- Drop existing tables if they exist
DROP TABLE IF EXISTS `website_appointment`;
DROP TABLE IF EXISTS `website_doctor`;

-- Create Doctor table with correct structure
CREATE TABLE `website_doctor` (
    `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, 
    `name` varchar(100) NOT NULL, 
    `email` varchar(254) NOT NULL UNIQUE, 
    `phone` varchar(20) NOT NULL, 
    `specialization` varchar(50) NOT NULL, 
    `experience` integer NOT NULL, 
    `qualification` varchar(100) NOT NULL, 
    `address` longtext NOT NULL, 
    `photo` varchar(100) NOT NULL, 
    `created_at` datetime(6) NOT NULL
);

-- Create Appointment table
CREATE TABLE `website_appointment` (
    `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY, 
    `patient_name` varchar(100) NOT NULL, 
    `patient_email` varchar(254) NOT NULL, 
    `patient_phone` varchar(20) NOT NULL, 
    `appointment_date` date NOT NULL, 
    `time_slot` varchar(20) NOT NULL, 
    `created_at` datetime(6) NOT NULL, 
    `doctor_id` bigint NOT NULL,
    FOREIGN KEY (`doctor_id`) REFERENCES `website_doctor` (`id`)
);
