# app/models/storage_analytics.py

from sqlalchemy import Column, String, Integer, DateTime, BigInteger, DECIMAL
from app.database.connection import Base  # Đảm bảo rằng 'Base' được import từ connection.py
from datetime import datetime

class StorageAnalytics(Base):
    __tablename__ = 'storage_analytics'  # Tên bảng trong cơ sở dữ liệu

    # Các trường trong bảng `storage_analytics`
    id = Column(String(36), primary_key=True)  # Khoá chính là id, kiểu String dài 36 ký tự
    analytics_date = Column(DateTime, nullable=False)  # Ngày phân tích
    storage_provider = Column(String(50), nullable=False)  # Nhà cung cấp lưu trữ (tối đa 50 ký tự)

    total_files = Column(Integer, default=0)  # Tổng số tệp
    total_size = Column(BigInteger, default=0)  # Tổng dung lượng (BigInteger cho số lượng lớn)
    average_file_size = Column(BigInteger, default=0)  # Kích thước trung bình của tệp

    storage_cost = Column(DECIMAL(10, 4), default=0)  # Chi phí lưu trữ (với độ chính xác đến 4 chữ số thập phân)
    bandwidth_cost = Column(DECIMAL(10, 4), default=0)  # Chi phí băng thông (với độ chính xác đến 4 chữ số thập phân)

    average_load_time_ms = Column(Integer, default=0)  # Thời gian tải trung bình (tính bằng mili giây)
    cache_hit_rate = Column(DECIMAL(5, 2), default=0)  # Tỷ lệ trúng cache (với độ chính xác 2 chữ số thập phân)

    created_at = Column(DateTime, default=datetime.utcnow)  # Thời gian tạo bản ghi (mặc định là thời gian hiện tại)
    