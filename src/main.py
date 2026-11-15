
from pathlib import Path
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.processor import (
    analyze_single_review,
    process_batch_csv,
    export_batch_csv
)

from contextlib import asynccontextmanager

from src.database import (
    init_database,
    fail_stale_batches,
    get_all_batches,
    get_batch_detail,
    get_dashboard_data
)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo database
    init_database()

    # Kiểm tra Batch bị treo quá 30 phút
    failed_count = fail_stale_batches(timeout_minutes=30)

    print(
        f"Đã kiểm tra Batch cũ. "
        f"Số Batch chuyển sang Failed: {failed_count}"
    )

    yield
app = FastAPI(
    title="Restaurant AI API",
    description="API phân tích đánh giá nhà hàng bằng AI",
    version="1.0.0",
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ReviewRequest(BaseModel):
    review: str = Field(
        ...,
        description="Nội dung đánh giá nhà hàng"
    )


@app.get("/")
def home():
    return {
        "message": "Restaurant AI API is running!",
        "status": "success"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@app.post("/analyze")
def analyze_review(request: ReviewRequest):
    try:
        results = analyze_single_review(request.review)

        return {
            "status": "success",
            "batch_id": results[0]["batch_id"],
            "review_id": results[0]["review_id"],
            "review": results[0]["Review"],
            "total_aspects": len(results),
            "results": results
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@app.post("/analyze/batch")
async def analyze_batch(file: UploadFile = File(...)):
    """
    Nhận file CSV và phân tích hàng loạt đánh giá.
    Mỗi lần upload sử dụng một file tạm riêng.
    """

    # Giới hạn dung lượng file: 10 MB
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # Kích thước mỗi lần đọc: 1 MB
    CHUNK_SIZE = 1024 * 1024

    # 1. Kiểm tra định dạng file
    if not file.filename or not file.filename.lower().endswith(".csv"):
        await file.close()
        raise HTTPException(
            status_code=400,
            detail="Chỉ chấp nhận file CSV."
        )

    temp_path = None

    try:
        # 2. Tạo thư mục lưu file tạm
        temp_dir = Path("data/temp")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 3. Tạo tên file riêng bằng UUID
        temp_path = temp_dir / f"upload_{uuid.uuid4().hex}.csv"

        total_size = 0

        # 4. Đọc file theo từng phần và ghi xuống ổ đĩa
        with temp_path.open("wb") as temp_file:

            while True:
                chunk = await file.read(CHUNK_SIZE)

                if not chunk:
                    break

                total_size += len(chunk)

                # 5. Kiểm tra dung lượng
                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File CSV vượt quá dung lượng tối đa 10 MB."
                    )

                temp_file.write(chunk)

        # 6. Kiểm tra file rỗng
        if total_size == 0:
            raise HTTPException(
                status_code=400,
                detail="File CSV không được để trống."
            )

        # 7. Gọi chức năng xử lý CSV hiện có
        batch_result = process_batch_csv(temp_path)

        # 8. Trả kết quả
        return {
            "status": batch_result["status"],
            "batch_id": batch_result["batch_id"],
            "total_rows": batch_result["total_rows"],
            "total_reviews": batch_result["total_reviews"],
            "skipped_rows": batch_result["skipped_rows"],
            "total_results": batch_result["total_results"]
        }

    except HTTPException:
        raise

    except (ValueError, FileNotFoundError) as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Đã xảy ra lỗi trong quá trình phân tích CSV."
        )

    finally:
        # Xóa file tạm sau khi xử lý
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

        # Đóng file upload
        await file.close()

@app.get("/batches")
def get_batches():
    """
    Lấy danh sách lịch sử phân tích Batch.
    """
    try:
        batches = get_all_batches()

        return {
            "status": "success",
            "total_batches": len(batches),
            "batches": batches
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Không thể lấy lịch sử Batch."
        )


@app.get("/batches/{batch_id}")
def get_batch(batch_id: str):
    """
    Lấy thông tin chi tiết một Batch.
    """
    try:
        batch_detail = get_batch_detail(batch_id)

        return {
            "status": "success",
            "batch": batch_detail["batch"],
            "total_results": len(batch_detail["results"]),
            "results": batch_detail["results"]
        }

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Không thể lấy chi tiết Batch."
        )


@app.get("/dashboard/{batch_id}")
def get_dashboard(batch_id: str):
    """
    Lấy dữ liệu Dashboard theo Batch ID.
    Chỉ chấp nhận Batch Completed.
    """
    try:
        dashboard_data = get_dashboard_data(batch_id)

        return {
            "status": "success",
            "batch": dashboard_data["batch"],
            "overall_statistics": dashboard_data[
                "overall_statistics"
            ],
            "aspect_statistics": dashboard_data[
                "aspect_statistics"
            ],
            "total_results": len(dashboard_data["results"]),
            "results": dashboard_data["results"]
        }

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Không thể lấy dữ liệu Dashboard."
        )



@app.get("/batches/{batch_id}/export")
def export_batch(batch_id: str):
    """
    Xuất kết quả phân tích của Batch thành file CSV.
    Chỉ cho phép xuất Batch Completed.
    """
    try:
        output_path = export_batch_csv(batch_id)

        return FileResponse(
            path=output_path,
            filename=f"{batch_id}_results.csv",
            media_type="text/csv"
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Không thể xuất file CSV."
        )
