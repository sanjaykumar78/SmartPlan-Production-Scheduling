CREATE DATABASE IF NOT EXISTS production_scheduler CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE production_scheduler;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS schedules;
DROP TABLE IF EXISTS disruptions;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS machines;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE users (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  username VARCHAR(80) NOT NULL,
  email VARCHAR(160) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(160) NOT NULL,
  role VARCHAR(80) NOT NULL DEFAULT 'Production Manager',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id), UNIQUE KEY uq_users_username (username), UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB;

CREATE TABLE machines (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  machine_id VARCHAR(40) NOT NULL,
  machine_name VARCHAR(160) NOT NULL,
  machine_type VARCHAR(80) NOT NULL,
  available_from DATETIME NOT NULL,
  status ENUM('Running','Available','Maintenance','Breakdown','Offline') NOT NULL DEFAULT 'Available',
  utilization DECIMAL(5,2) NOT NULL DEFAULT 0.00,
  maintenance_date DATE NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id), UNIQUE KEY uq_machines_machine_id (machine_id), KEY idx_machines_status (status),
  CONSTRAINT chk_machines_utilization CHECK (utilization BETWEEN 0 AND 100)
) ENGINE=InnoDB;

CREATE TABLE orders (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  order_number VARCHAR(40) NOT NULL,
  product_name VARCHAR(160) NOT NULL,
  quantity INT UNSIGNED NOT NULL,
  processing_time INT UNSIGNED NOT NULL COMMENT 'Minutes',
  priority ENUM('High','Medium','Low') NOT NULL DEFAULT 'Medium',
  deadline DATETIME NOT NULL,
  required_machine_type VARCHAR(80) NOT NULL,
  status ENUM('Pending','Scheduled','In Production','Completed','Delayed','Cancelled') NOT NULL DEFAULT 'Pending',
  notes TEXT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id), UNIQUE KEY uq_orders_order_number (order_number), KEY idx_orders_status (status), KEY idx_orders_deadline (deadline), KEY idx_orders_priority (priority)
) ENGINE=InnoDB;

CREATE TABLE schedules (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  order_id INT UNSIGNED NOT NULL,
  machine_id INT UNSIGNED NOT NULL,
  start_time DATETIME NOT NULL,
  end_time DATETIME NOT NULL,
  status ENUM('Scheduled','In Production','Completed','Delayed','Cancelled') NOT NULL DEFAULT 'Scheduled',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id), KEY idx_schedules_order (order_id), KEY idx_schedules_machine (machine_id), KEY idx_schedules_start (start_time),
  CONSTRAINT fk_schedules_order FOREIGN KEY (order_id) REFERENCES orders(id) ON UPDATE CASCADE ON DELETE CASCADE,
  CONSTRAINT fk_schedules_machine FOREIGN KEY (machine_id) REFERENCES machines(id) ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT chk_schedule_time CHECK (end_time > start_time)
) ENGINE=InnoDB;

CREATE TABLE disruptions (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  event_type ENUM('Machine Breakdown','Urgent Order','Maintenance','Processing Time Change') NOT NULL,
  machine_id INT UNSIGNED NULL,
  start_time DATETIME NOT NULL,
  end_time DATETIME NULL,
  description TEXT NOT NULL,
  severity ENUM('Low','Medium','High','Critical') NOT NULL DEFAULT 'Medium',
  status ENUM('Active','Resolved','Pending') NOT NULL DEFAULT 'Active',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id), KEY idx_disruptions_machine (machine_id), KEY idx_disruptions_status (status),
  CONSTRAINT fk_disruptions_machine FOREIGN KEY (machine_id) REFERENCES machines(id) ON UPDATE CASCADE ON DELETE SET NULL,
  CONSTRAINT chk_disruption_time CHECK (end_time IS NULL OR end_time > start_time)
) ENGINE=InnoDB;

INSERT INTO users (username,email,password_hash,full_name,role) VALUES
('factory.manager','manager@smartplan.local','$2b$12$replace_before_production','Factory Manager','Production Manager'),
('planner.one','planner@smartplan.local','$2b$12$replace_before_production','Jordan Lee','Production Planner');

INSERT INTO machines (machine_id,machine_name,machine_type,available_from,status,utilization,maintenance_date) VALUES
('CNC-01','CNC Machine 01','CNC','2026-09-18 14:30:00','Running',92,NULL),
('CNC-02','CNC Machine 02','CNC','2026-09-18 09:00:00','Available',64,NULL),
('CNC-03','CNC Machine 03','CNC','2026-09-18 16:00:00','Maintenance',45,'2026-09-18'),
('CNC-04','CNC Machine 04','CNC','2026-09-19 08:00:00','Breakdown',0,NULL),
('CNC-05','CNC Machine 05','CNC','2026-09-18 15:10:00','Running',88,NULL),
('CUT-01','Cutting Line 01','Cutting','2026-09-18 13:20:00','Running',76,NULL),
('CUT-02','Cutting Line 02','Cutting','2026-09-18 08:00:00','Available',51,NULL),
('CUT-03','Cutting Line 03','Cutting','2026-09-18 08:00:00','Available',59,NULL),
('ASM-01','Assembly Cell 01','Assembly','2026-09-18 12:45:00','Running',84,NULL),
('ASM-02','Assembly Cell 02','Assembly','2026-09-19 08:00:00','Offline',0,'2026-09-19');

INSERT INTO orders (order_number,product_name,quantity,processing_time,priority,deadline,required_machine_type,status,notes) VALUES
('ORD-1001','Industrial Gear',500,210,'High','2026-09-18 15:00:00','CNC','In Production','Rush order for Northstar Components.'),
('ORD-1002','Steel Housing',250,180,'Medium','2026-09-18 16:30:00','CNC','Scheduled','Verify surface finish.'),
('ORD-1003','Drive Shaft',120,240,'High','2026-09-18 14:00:00','CNC','Delayed','Awaiting machine reassignment.'),
('ORD-1004','Hydraulic Valve',320,150,'Medium','2026-09-18 17:00:00','Cutting','Scheduled','Dimensional inspection required.'),
('ORD-1005','Bearing Assembly',800,120,'Low','2026-09-19 12:00:00','Assembly','Pending','Standard replenishment order.'),
('ORD-1006','Pump Housing',180,195,'High','2026-09-19 10:00:00','CNC','Scheduled','Priority customer allocation.'),
('ORD-1007','Motor Shaft',430,175,'Medium','2026-09-19 15:00:00','CNC','Completed','Quality approval recorded.'),
('ORD-1008','Precision Bracket',650,100,'Low','2026-09-20 11:00:00','Cutting','Pending','Use corrosion-resistant stock.'),
('ORD-1009','Conveyor Roller',90,220,'High','2026-09-18 18:00:00','CNC','In Production','Customer line restart dependency.'),
('ORD-1010','Valve Block',275,130,'Medium','2026-09-20 14:00:00','Assembly','Scheduled','Include pressure certificate.'),
('ORD-1011','Rotor Plate',340,160,'Low','2026-09-21 12:00:00','CNC','Pending','Schedule after priority work.'),
('ORD-1012','Filter Housing',210,145,'Medium','2026-09-20 16:00:00','Cutting','Completed','Final inspection passed.'),
('ORD-1013','Gearbox Cover',185,190,'High','2026-09-19 17:00:00','CNC','Scheduled','Use fixture set B.'),
('ORD-1014','Actuator Rod',360,115,'Medium','2026-09-20 10:00:00','CNC','Pending','Chrome finish required.'),
('ORD-1015','Pump Impeller',240,205,'High','2026-09-19 13:00:00','CNC','Scheduled','Balance to ISO grade 6.3.'),
('ORD-1016','Mounting Plate',520,90,'Low','2026-09-21 16:00:00','Cutting','Pending','Use standard packaging.'),
('ORD-1017','Bearing Sleeve',700,105,'Medium','2026-09-20 18:00:00','Assembly','Pending','Pair with ORD-1005 components.'),
('ORD-1018','Welded Frame',75,260,'High','2026-09-19 18:00:00','Welding','Scheduled','Weld inspection required.'),
('ORD-1019','Control Panel Bracket',430,125,'Low','2026-09-22 12:00:00','Cutting','Pending','Late-shift production acceptable.'),
('ORD-1020','Transmission Hub',160,230,'High','2026-09-20 12:00:00','CNC','Scheduled','Critical spare-part order.');

INSERT INTO schedules (order_id,machine_id,start_time,end_time,status) VALUES
(1,1,'2026-09-18 08:00:00','2026-09-18 11:30:00','In Production'),
(2,2,'2026-09-18 09:00:00','2026-09-18 12:00:00','Scheduled'),
(3,3,'2026-09-18 10:00:00','2026-09-18 14:00:00','Delayed'),
(4,6,'2026-09-18 09:30:00','2026-09-18 12:00:00','Scheduled'),
(5,9,'2026-09-18 10:00:00','2026-09-18 12:00:00','Scheduled'),
(6,5,'2026-09-18 11:30:00','2026-09-18 14:45:00','Scheduled'),
(7,5,'2026-09-18 08:00:00','2026-09-18 10:55:00','Completed'),
(8,7,'2026-09-18 12:00:00','2026-09-18 13:40:00','Scheduled'),
(9,1,'2026-09-18 13:00:00','2026-09-18 16:40:00','In Production'),
(10,9,'2026-09-18 13:00:00','2026-09-18 15:10:00','Scheduled'),
(11,2,'2026-09-18 13:00:00','2026-09-18 15:40:00','Scheduled'),
(12,8,'2026-09-18 14:00:00','2026-09-18 16:25:00','Completed');

INSERT INTO disruptions (event_type,machine_id,start_time,end_time,description,severity,status) VALUES
('Machine Breakdown',1,'2026-09-18 12:00:00','2026-09-18 14:00:00','Motor failure detected during spindle inspection.','Critical','Active'),
('Maintenance',3,'2026-09-18 14:00:00','2026-09-18 16:00:00','Scheduled preventative maintenance on CNC-03.','Medium','Pending'),
('Urgent Order',NULL,'2026-09-18 09:15:00','2026-09-18 17:00:00','ORD-1050 inserted for same-day customer requirement.','High','Active'),
('Processing Time Change',2,'2026-09-18 10:30:00',NULL,'Steel hardness increased processing estimate.','Medium','Resolved'),
('Machine Breakdown',4,'2026-09-17 16:20:00','2026-09-18 08:00:00','Hydraulic pressure fault placed CNC-04 offline.','High','Resolved'),
('Maintenance',9,'2026-09-19 12:00:00','2026-09-19 13:30:00','Assembly cell calibration scheduled.','Low','Pending'),
('Processing Time Change',6,'2026-09-18 11:00:00',NULL,'Tool wear increased cutting time.','Medium','Active'),
('Urgent Order',NULL,'2026-09-18 08:30:00','2026-09-18 16:00:00','Expedited replacement components requested.','High','Resolved'),
('Machine Breakdown',7,'2026-09-16 13:45:00','2026-09-16 15:10:00','Coolant pump interruption on cutting line.','Medium','Resolved'),
('Maintenance',5,'2026-09-20 08:00:00','2026-09-20 10:00:00','Planned spindle alignment and inspection.','Low','Pending');
