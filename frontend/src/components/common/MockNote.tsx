/** Nhãn cho màn dùng dữ liệu mẫu (src/api/mock), sẽ bỏ khi nối API thật. */
export function MockNote({ children }: { children?: React.ReactNode }) {
  return (
    <p className="note small" role="note">
      <strong>Dữ liệu mẫu</strong> · {children ?? "Màn này chưa kết nối API; thay đổi chỉ lưu tạm trong trình duyệt và mất khi tải lại trang."}
    </p>
  );
}
