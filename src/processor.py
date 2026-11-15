import pandas as pd
from pathlib import Path

from src.identifiers import generate_batch_id, generate_review_id
from src.validator import (
    validate_review,
    validate_prediction_results
)
from src.predictor import predict_review
from src.database import (
    save_batch,
    create_batch,
    update_batch_status
)
from src.constants import OUTPUT_COLUMNS


def create_review_record(review, batch_id=None, review_id=None):
    """Tạo bản ghi đánh giá hoàn chỉnh."""

    review = validate_review(review)

    if batch_id is None:
        batch_id = generate_batch_id()

    if review_id is None:
        review_id = generate_review_id()

    return {
        "batch_id": batch_id,
        "review_id": review_id,
        "Review": review
    }


def analyze_single_review(review):
    """Analyze and persist one restaurant review as a completed batch."""
    record = create_review_record(review)
    batch_id = record["batch_id"]
    create_batch(batch_id)

    try:
        predictions = predict_review(record["Review"])
        validate_prediction_results(predictions)

        results = [
            {
                "batch_id": batch_id,
                "review_id": record["review_id"],
                "Review": record["Review"],
                "Aspect": prediction["Aspect"],
                "Sentiment": prediction["Sentiment"],
                "Confidence": prediction["Confidence"],
            }
            for prediction in predictions
        ]

        save_batch({
            "batch_id": batch_id,
            "status": "Completed",
            "total_rows": 1,
            "total_reviews": 1,
            "skipped_rows": 0,
            "total_results": len(results),
            "results": results,
        })

        return results

    except Exception as error:
        update_batch_status(
            batch_id=batch_id,
            status="Failed",
            total_rows=1,
            total_reviews=1,
            skipped_rows=0,
            total_results=0,
            error_message=str(error)[:5000],
        )
        raise


def load_reviews_csv(file_path):
    """Đọc và kiểm tra dữ liệu đánh giá từ CSV."""

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file: {file_path}"
        )

    if file_path.suffix.lower() != ".csv":
        raise ValueError("Chỉ chấp nhận file CSV.")

    # Đọc CSV, ưu tiên UTF-8-SIG.
    try:
        df = pd.read_csv(
            file_path,
            encoding="utf-8-sig"
        )
    except UnicodeDecodeError:
        df = pd.read_csv(
            file_path,
            encoding="cp1258"
        )

    total_rows = len(df)

    if "Review" not in df.columns:
        raise ValueError(
            "File CSV bắt buộc phải có cột Review."
        )

    # Loại bỏ dòng rỗng.
    df = df.dropna(subset=["Review"]).copy()
    df["Review"] = df["Review"].astype(str).str.strip()
    df = df[df["Review"] != ""].copy()

    # Chuẩn hóa review_id.
    if "review_id" not in df.columns:
        df["review_id"] = None

    for index in df.index:
        current_id = df.at[index, "review_id"]

        if pd.isna(current_id) or str(current_id).strip() == "":
            df.at[index, "review_id"] = generate_review_id()
        else:
            df.at[index, "review_id"] = str(current_id).strip()

    # Không cho phép ID trùng nhau trong cùng CSV.
    duplicated = df["review_id"].duplicated(keep=False)

    if duplicated.any():
        duplicated_ids = (
            df.loc[duplicated, "review_id"]
            .astype(str)
            .unique()
            .tolist()
        )

        raise ValueError(
            f"Phát hiện review_id trùng lặp: {duplicated_ids[:20]}"
        )

    cleaned_df = df[["review_id", "Review"]].reset_index(drop=True)

    cleaned_df.attrs["total_rows"] = total_rows
    cleaned_df.attrs["skipped_rows"] = total_rows - len(cleaned_df)

    return cleaned_df


def process_batch_csv(file_path):
    """
    Xử lý CSV theo Batch.

    Tiếp tục kiểm tra các review còn lại nếu một review lỗi.
    Nếu có bất kỳ review nào lỗi, Batch sẽ Failed và không
    lưu kết quả phân tích một phần vào bảng results.
    """

    batch_id = generate_batch_id()
    create_batch(batch_id)

    total_rows = 0
    total_reviews = 0
    skipped_rows = 0

    try:
        # 1. Đọc và kiểm tra CSV.
        df = load_reviews_csv(file_path)

        total_rows = df.attrs["total_rows"]
        total_reviews = len(df)
        skipped_rows = df.attrs["skipped_rows"]

        if df.empty:
            raise ValueError(
                "Batch không có đánh giá hợp lệ để phân tích."
            )

        all_results = []
        review_errors = []

        # 2. Phân tích từng review.
        for _, row in df.iterrows():
            review_id = row["review_id"]
            review = row["Review"]

            try:
                # Chuẩn hóa và kiểm tra review.
                review = validate_review(review)

                # Dự đoán.
                predictions = predict_review(review)

                # Kiểm tra đủ 12 Aspect và định dạng.
                validate_prediction_results(predictions)

                # Kết hợp kết quả.
                for prediction in predictions:
                    all_results.append({
                        "batch_id": batch_id,
                        "review_id": review_id,
                        "Review": review,
                        "Aspect": prediction["Aspect"],
                        "Sentiment": prediction["Sentiment"],
                        "Confidence": prediction["Confidence"]
                    })

            except Exception as error:
                review_errors.append(
                    f"{review_id}: {str(error)}"
                )

                # Tiếp tục xử lý review tiếp theo.
                continue

        # 3. Nếu có review lỗi, không lưu kết quả một phần.
        if review_errors:
            error_summary = (
                f"Có {len(review_errors)} review không phân tích được. "
                + "; ".join(review_errors[:10])
            )

            if len(review_errors) > 10:
                error_summary += (
                    f"; và {len(review_errors) - 10} lỗi khác."
                )

            raise RuntimeError(error_summary)

        # 4. Kiểm tra tính toàn vẹn.
        expected_results = total_reviews * 12

        if len(all_results) != expected_results:
            raise ValueError(
                f"Kết quả không đầy đủ: cần {expected_results}, "
                f"nhưng nhận được {len(all_results)}."
            )

        # 5. Chuẩn bị batch.
        batch_result = {
            "batch_id": batch_id,
            "status": "Completed",
            "total_rows": total_rows,
            "total_reviews": total_reviews,
            "skipped_rows": skipped_rows,
            "total_results": len(all_results),
            "results": all_results
        }

        # 6. Database tự kiểm tra và commit transaction.
        save_batch(batch_result)

        return batch_result

    except Exception as error:
        # Chỉ cập nhật trạng thái Failed một lần.
        update_batch_status(
            batch_id=batch_id,
            status="Failed",
            total_rows=total_rows,
            total_reviews=total_reviews,
            skipped_rows=skipped_rows,
            total_results=0,
            error_message=str(error)[:5000]
        )

        raise


def export_results_csv(batch_result, output_path=None):
    """Xuất kết quả CSV của Batch Completed."""

    if batch_result["status"] != "Completed":
        raise ValueError(
            "Chỉ được xuất dữ liệu của batch đã Completed."
        )

    df = pd.DataFrame(
        batch_result["results"],
        columns=OUTPUT_COLUMNS
    )

    if output_path is None:
        output_path = (
            Path("exports")
            / f"{batch_result['batch_id']}_results.csv"
        )
    else:
        output_path = Path(output_path)

    # Tạo thư mục nếu chưa tồn tại.
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    return str(output_path)


def export_batch_csv(batch_id, output_path=None):
    """Xuất kết quả CSV theo batch_id."""

    from src.database import get_batch_detail

    batch_detail = get_batch_detail(batch_id)
    batch_info = batch_detail["batch"]

    if batch_info["status"] != "Completed":
        raise ValueError(
            "Chỉ được xuất dữ liệu của Batch đã Completed."
        )

    batch_result = {
        "batch_id": batch_id,
        "status": batch_info["status"],
        "results": batch_detail["results"]
    }

    return export_results_csv(
        batch_result,
        output_path
    )