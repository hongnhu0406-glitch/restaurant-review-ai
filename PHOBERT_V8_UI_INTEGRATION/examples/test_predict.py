from model_predict import predict_review, format_for_display

review = "Đồ ăn ngon nhưng phục vụ chậm."

# AI trả đủ 12 khía cạnh
results = predict_review(review)

# Dữ liệu cho Backend lưu
for row in results:
    print(row)

# Giao diện mặc định: chỉ khía cạnh được đề cập
display_rows = format_for_display(
    results,
    show_absent=False
)

print("\\nDISPLAY:")
for row in display_rows:
    print(row)

# Xem đầy đủ 12 khía cạnh
all_rows = format_for_display(
    results,
    show_absent=True
)
