# Sử dụng bản Python 3.11 gọn nhẹ chuẩn Linux
FROM python:3.11-slim

WORKDIR /app

# Cấu hình tối ưu cho Python chạy trong Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Sao chép file danh sách thư viện vào trước
COPY requirements.txt .

# Nâng cấp pip và cài đặt toàn bộ thư viện
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào trong Docker
COPY . .

# Lệnh mặc định khi khởi chạy
CMD ["python", "crawler_vbpl.py"]