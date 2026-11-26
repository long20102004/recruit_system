import type { PageDto } from "../../api/client";

/** Nút trang trước / sau cho API phân trang; ẩn khi chỉ có một trang. */
export function Pager({ data, onPage }: { data: PageDto<unknown> | null; onPage: (page: number) => void }) {
  if (!data || data.totalPages <= 1) return null;
  const page = data.pageNumber;
  return (
    <nav className="row" aria-label="Phân trang" style={{ justifyContent: "center", gap: 12 }}>
      <button type="button" className="btn btn-g btn-sm" disabled={page === 0} onClick={() => onPage(page - 1)}>
        ‹ Trước
      </button>
      <span className="small muted">Trang {page + 1} / {data.totalPages}</span>
      <button type="button" className="btn btn-g btn-sm" disabled={data.last} onClick={() => onPage(page + 1)}>
        Sau ›
      </button>
    </nav>
  );
}
