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
        review_id = generate_review_id(batch_id)

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



def load_reviews_csv(file_path, batch_id):
    """Đọc và kiểm tra toàn bộ dữ liệu Review từ CSV."""

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Không tìm thấy file: {file_path}"
        )

    if file_path.suffix.lower() != ".csv":
        raise ValueError("Chỉ chấp nhận file CSV.")

    # 1. Đọc CSV
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

    # 2. Lưu số thứ tự dòng dữ liệu trong file
    df = df.copy()
    df["row_number"] = df.index + 2

    # 3. Chuẩn hóa Review và kiểm tra từng dòng
    errors = []

    for index, row in df.iterrows():
        row_number = row["row_number"]
        review = row["Review"]

        try:
            if pd.isna(review):
                raise ValueError(
                    "Nội dung Review không được để trống."
                )

            df.at[index, "Review"] = validate_review(
                str(review)
            )

        except (TypeError, ValueError) as error:
            errors.append(
                f"Dòng {row_number}: {str(error)}"
            )

    # 4. Chuẩn hóa review_id
    if "review_id" not in df.columns:
        df["review_id"] = None

    df["review_id"] = df["review_id"].apply(
        lambda value: (
            str(value).strip()
            if pd.notna(value) and str(value).strip()
            else None
        )
    )

    # 5. Kiểm tra review_id trùng lặp
    duplicated = df["review_id"].notna() & (
        df["review_id"].duplicated(keep=False)
    )

    for _, row in df[duplicated].iterrows():
        errors.append(
            f"Dòng {row['row_number']}: "
            f"review_id '{row['review_id']}' bị trùng."
        )

    # 6. Nếu có lỗi, dừng trước khi phân tích
    if errors:
        error_message = (
            f"File CSV có {len(errors)} lỗi đầu vào:\n"
            + "\n".join(errors)
        )
        raise ValueError(error_message)

    # 7. Tự sinh review_id cho các dòng chưa có ID
    existing_ids = set(df["review_id"].dropna())

    for index in df.index:
        if df.at[index, "review_id"] is None:
            new_id = generate_review_id(batch_id)

            while new_id in existing_ids:
                new_id = generate_review_id(batch_id)

            df.at[index, "review_id"] = new_id
            existing_ids.add(new_id)

    # 8. Trả về dữ liệu hợp lệ
    cleaned_df = df[
        ["review_id", "Review", "row_number"]
    ].reset_index(drop=True)

    cleaned_df.attrs["total_rows"] = total_rows
    cleaned_df.attrs["skipped_rows"] = 0

    return cleaned_df



def process_batch_csv(file_path):
    """
    Xử lý CSV theo Batch:
    - Kiểm tra toàn bộ dữ liệu đầu vào trước khi chạy mô hình.
    - Nếu CSV có lỗi đầu vào: dừng, không gọi PhoBERT.
    - Chỉ lưu kết quả khi toàn bộ review được phân tích thành công.
    """

    batch_id = generate_batch_id()
    create_batch(batch_id)

    total_rows = 0
    total_reviews = 0
    skipped_rows = 0

    try:
        # 1. Kiểm tra toàn bộ CSV trước khi phân tích.
        df = load_reviews_csv(file_path, batch_id)

        total_rows = df.attrs["total_rows"]
        total_reviews = len(df)
        skipped_rows = df.attrs["skipped_rows"]

        if df.empty:
            raise ValueError(
                "Batch không có đánh giá hợp lệ để phân tích."
            )

        all_results = []

        # 2. Chỉ chạy PhoBERT khi toàn bộ dữ liệu đầu vào hợp lệ.
        for _, row in df.iterrows():
            review_id = row["review_id"]
            review = row["Review"]
            row_number = row["row_number"]

            try:
                predictions = predict_review(review)

                # Kiểm tra kết quả dự đoán.
                validate_prediction_results(predictions)

                # Lưu kết quả tạm thời trong bộ nhớ.
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
                raise RuntimeError(
                    f"Lỗi khi phân tích dòng {row_number} "
                    f"(review_id: {review_id}): {str(error)}"
                ) from error

        # 3. Kiểm tra số lượng kết quả.
        expected_results = total_reviews * 12

        if len(all_results) != expected_results:
            raise ValueError(
                f"Kết quả không đầy đủ: cần {expected_results}, "
                f"nhưng nhận được {len(all_results)}."
            )

        # 4. Chuẩn bị dữ liệu Batch.
        batch_result = {
            "batch_id": batch_id,
            "status": "Completed",
            "total_rows": total_rows,
            "total_reviews": total_reviews,
            "skipped_rows": skipped_rows,
            "total_results": len(all_results),
            "results": all_results
        }

        # 5. Chỉ lưu khi toàn bộ quá trình thành công.
        save_batch(batch_result)

        return batch_result

    except Exception as error:
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