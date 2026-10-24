CREATE DATABASE IF NOT EXISTS pos_db;
USE pos_db;
CREATE TABLE IF NOT EXISTS products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  sku VARCHAR(60) NOT NULL UNIQUE,
  price DECIMAL(12,2) NOT NULL DEFAULT 0,
  stock INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sales (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  product_id INT NOT NULL,
  product_name VARCHAR(150) NOT NULL,
  quantity INT NOT NULL,
  unit_price DECIMAL(12,2) NOT NULL,
  total DECIMAL(14,2) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_sales_created_at (created_at),
  CONSTRAINT fk_sales_product FOREIGN KEY (product_id) REFERENCES products(id)
);
INSERT IGNORE INTO products(name,sku,price,stock) VALUES
('Cà phê rang xay','CF001',65000,30),
('Trà xanh hộp','TR001',42000,25),
('Nước suối 500ml','NS001',8000,100);
