package recruit.demo.extraction.pdf;

/**
 * Một khối văn bản đã khôi phục thứ tự đọc, kèm tọa độ để truy vết.
 *
 * @param page     số trang (bắt đầu từ 1)
 * @param order    thứ tự đọc trong toàn CV (0, 1, 2, ...)
 * @param x0       biên trái (đơn vị PDF user space)
 * @param y0       biên trên
 * @param x1       biên phải
 * @param y1       biên dưới
 * @param fontSize cỡ chữ trung bình của block
 * @param text     nội dung đã chuẩn hóa nhẹ (giữ xuống dòng giữa các dòng gốc)
 */
public record TextBlock(
        int page,
        int order,
        float x0,
        float y0,
        float x1,
        float y1,
        float fontSize,
        String text
) {
}
