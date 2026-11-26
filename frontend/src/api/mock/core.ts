/**
 * Lớp API giả cho các màn chưa có backend (design canvas). Mỗi file *Mock.ts export các hàm cùng chữ ký
 * như API thật sẽ có (trả Promise). Khi backend sẵn sàng: thay thân hàm bằng api()/apiData() trong
 * src/api/client.ts, giữ nguyên chữ ký để trang không phải sửa. Dữ liệu sửa đổi chỉ nằm trong bộ nhớ,
 * mất khi tải lại trang.
 */

export const MOCK_DELAY_MS = 250;

/** Trả bản sao sâu sau một độ trễ nhỏ, giống gọi mạng; trang không sửa nhầm kho dữ liệu mẫu. */
export function mockResolve<T>(value: T, ms = MOCK_DELAY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(structuredClone(value)), ms));
}

/** Lỗi giả có message tiếng Việt, dùng như ApiError ở trang. */
export function mockReject(message: string, ms = MOCK_DELAY_MS): Promise<never> {
  return new Promise((_, reject) => setTimeout(() => reject(new Error(message)), ms));
}

export function nextId(list: { id: number }[]): number {
  return list.reduce((max, x) => Math.max(max, x.id), 0) + 1;
}
