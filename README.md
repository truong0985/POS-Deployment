# Hệ thống Quản lý Cửa hàng / POS — triển khai Docker

## 1. Công nghệ
- Flask + Gunicorn: giao diện POS và REST-like endpoints.
- MySQL 8.4: sản phẩm, tồn kho, hóa đơn.
- Nginx: reverse proxy và HTTP security headers.
- Prometheus + Grafana + cAdvisor + Node Exporter: giám sát.
- Loki + Promtail: tập trung log.
- phpMyAdmin: quản trị CSDL (profile `admin`).

## 2. Yêu cầu
Docker Desktop (Windows) hoặc Docker Engine + Docker Compose plugin (Linux/Ubuntu), tối thiểu khuyến nghị 4 GB RAM. Trên Linux, hãy kiểm tra quyền truy cập Docker.

## 3. Cài đặt
1. Clone/copy thư mục dự án.
2. Sao chép `.env.example` thành `.env`.
3. Sửa các mật khẩu trong `.env` thành giá trị mạnh, không dùng giá trị ví dụ.
4. Khởi động các dịch vụ:
   ```bash
   docker compose up -d --build
   ```
5. Mở giao diện:
   - POS: http://localhost:8080
   - Prometheus: http://localhost:9090
   - Grafana: http://localhost:3000
6. Nếu cần phpMyAdmin, khởi chạy profile quản trị:
   ```bash
   docker compose --profile admin up -d
   ```
   phpMyAdmin: http://localhost:8081

## 4. Kiểm tra
```bash
docker compose ps
docker compose logs -f pos_app
curl -I http://localhost:8080
curl http://localhost:8080/health
```
Trong Prometheus, kiểm tra `Status > Targets`; truy vấn thử `pos_http_requests_total`. Trong Grafana Explore, chọn Loki và thử `{job="nginx"}` hoặc `{job="pos_app"}`.

## 5. Dừng / làm sạch
```bash
docker compose down
```
Muốn xóa cả dữ liệu MySQL và metrics đã lưu (cẩn thận vì mất dữ liệu):
```bash
docker compose down -v
```

## 6. Cấu trúc
- `app/`: ứng dụng Flask, Dockerfile, dependencies.
- `database/init.sql`: tạo bảng và dữ liệu demo.
- `nginx/`: reverse proxy.
- `monitoring/`: Prometheus, Grafana datasource, Loki, Promtail.
- `.env.example`: mẫu biến môi trường; tạo `.env` cục bộ và không commit.

## 7. Lưu ý bảo mật và giới hạn
Đây là đồ án học tập/demo. phpMyAdmin chỉ bật khi cần và không nên mở công khai. HTTPS chưa được cấu hình; khi triển khai thật cần TLS, backup/restore, xác thực nhân viên, phân quyền, CSRF protection, kiểm soát nhập liệu đầy đủ và quản lý secrets phù hợp. cAdvisor cần quyền truy cập sâu vào host nên cần đánh giá rủi ro trước khi dùng production.
