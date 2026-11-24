
from src.database import get_connection


def generate_batch_id():
    """Tạo batch_id tăng tuần tự và lưu số thứ tự trong Database."""

    conn = get_connection()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS id_counters (
                counter_key TEXT PRIMARY KEY,
                counter_value INTEGER NOT NULL
            )
        """)

        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute("""
            SELECT counter_value
            FROM id_counters
            WHERE counter_key = 'batch'
        """).fetchone()

        if row is None:
            # Tìm số Batch lớn nhất đã tồn tại theo định dạng B001.
            existing_ids = conn.execute("""
                SELECT batch_id FROM batches
            """).fetchall()

            max_number = 0

            for item in existing_ids:
                batch_id = item["batch_id"]

                if (
                    isinstance(batch_id, str)
                    and batch_id.startswith("B")
                    and batch_id[1:].isdigit()
                ):
                    max_number = max(
                        max_number,
                        int(batch_id[1:])
                    )

            next_number = max_number + 1

            conn.execute("""
                INSERT INTO id_counters (counter_key, counter_value)
                VALUES ('batch', ?)
            """, (next_number,))

        else:
            next_number = row["counter_value"] + 1

            conn.execute("""
                UPDATE id_counters
                SET counter_value = ?
                WHERE counter_key = 'batch'
            """, (next_number,))

        conn.commit()

        return f"B{next_number:03d}"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def generate_review_id(batch_id):
    """Tạo review_id tăng tuần tự trong phạm vi một Batch."""

    if not batch_id:
        raise ValueError("Phải có batch_id để tạo review_id.")

    counter_key = f"review:{batch_id}"

    conn = get_connection()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS id_counters (
                counter_key TEXT PRIMARY KEY,
                counter_value INTEGER NOT NULL
            )
        """)

        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute("""
            SELECT counter_value
            FROM id_counters
            WHERE counter_key = ?
        """, (counter_key,)).fetchone()

        if row is None:
            next_number = 1

            conn.execute("""
                INSERT INTO id_counters (counter_key, counter_value)
                VALUES (?, ?)
            """, (counter_key, next_number))

        else:
            next_number = row["counter_value"] + 1

            conn.execute("""
                UPDATE id_counters
                SET counter_value = ?
                WHERE counter_key = ?
            """, (next_number, counter_key))

        conn.commit()

        return f"RV{next_number:04d}"

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
