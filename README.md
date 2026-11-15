# Restaurant Review AI

Project AI phân tích đánh giá nhà hàng theo khía cạnh, tích hợp backend FastAPI và giao diện Streamlit.

## Cài đặt

1. Tạo môi trường ảo (nếu chưa có):

   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

2. Cài đặt dependency:

   ```bash
   pip install -r requirements.txt
   ```

## Chạy ứng dụng

Có 2 cách:

### 1. Chạy nhanh bằng script

Từ thư mục gốc:

```bash
python start_app.py
```

Script sẽ tự khởi động:
- FastAPI backend tại http://127.0.0.1:8000
- Streamlit UI tại http://127.0.0.1:8501

### 2. Chạy thủ công

Backend:

```bash
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend:

```bash
python -m streamlit run single_review.py --server.address 127.0.0.1 --server.port 8501
```

## GitHub branch

Branch đang dùng cho phiên bản backend + streamlit UI hiện tại:

```bash
feature/duc-backend-streamlit
```

## Lưu ý

- Trước khi mở giao diện, hãy đảm bảo backend đang chạy.
- Nếu port 8501 hoặc 8000 đang bận, hãy đổi port trong lệnh tương ứng.
- Nếu cần chạy máy chủ API riêng, hãy dùng dữ liệu được cung cấp trong project và giữ nguyên cấu trúc thư mục `src/`.
