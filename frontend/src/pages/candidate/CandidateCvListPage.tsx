import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { SiteHeader } from "../../components/common";
import { MAX_CANDIDATE_CVS, cvsApi, type CvDocumentDto } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { shortDate } from "../../utils/format";

type CandidateCvItem = CvDocumentDto;

/** Màn C02 · Danh sách CV của tôi (design canvas CvList.dc.html). */

export function CandidateCvListPage() {
  const { toast } = useToast();
  const [cvs, setCvs] = useState<CandidateCvItem[] | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<CandidateCvItem | null>(null);

  useEffect(() => {
    cvsApi
      .documents()
      .then(setCvs)
      .catch((e) => {
        setCvs([]);
        toast(e instanceof Error ? e.message : "Không tải được danh sách CV");
      });
  }, [toast]);

  useEffect(() => {
    if (!confirmDelete) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setConfirmDelete(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [confirmDelete]);

  async function onSetMain(cv: CandidateCvItem) {
    setBusyId(cv.id);
    try {
      const updated = await cvsApi.setMain(cv.id);
      setCvs(updated);
      toast(`Đã đặt “${cv.title}” làm CV chính.`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không thể cập nhật CV chính");
    } finally {
      setBusyId(null);
    }
  }

  async function onConfirmRemove() {
    if (!confirmDelete) return;
    const target = confirmDelete;
    setBusyId(target.id);
    try {
      await cvsApi.remove(target.id);
      const updated = await cvsApi.documents();
      setCvs(updated);
      setConfirmDelete(null);
      toast(`Đã xóa CV “${target.title}”.`);
    } catch (e) {
      setConfirmDelete(null);
      toast(e instanceof Error ? e.message : "Không thể xóa CV");
    } finally {
      setBusyId(null);
    }
  }

  async function onDownload(cv: CandidateCvItem) {
    try {
      await cvsApi.download(cv.id);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không tải được tệp CV");
    }
  }

  async function onRename(cv: CandidateCvItem) {
    const title = window.prompt("Tên CV", cv.title)?.trim();
    if (!title || title === cv.title) return;
    setBusyId(cv.id);
    try {
      const updated = await cvsApi.rename(cv.id, title);
      setCvs((list) => (list ?? []).map((item) => (item.id === updated.id ? updated : item)));
      toast("Đã đổi tên CV.");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không đổi được tên CV");
    } finally {
      setBusyId(null);
    }
  }

  const count = cvs?.length ?? 0;
  const remaining = Math.max(0, MAX_CANDIDATE_CVS - count);

  return (
    <>
      <SiteHeader active="cv" mode="candidate" />
      <div
        className="wrap"
        style={{
          paddingTop: 32,
          paddingBottom: 64,
          display: "flex",
          flexDirection: "column",
          gap: 24,
        }}
      >
        <div className="page-head" style={{ marginBottom: 0 }}>
          <div>
            <h1 style={{ fontSize: 34 }}>CV của tôi</h1>
            <p className="muted">
              {count} / {MAX_CANDIDATE_CVS} CV · CV chính được dùng cho matching và gợi ý việc làm.
            </p>
          </div>
          <div className="row">
            {remaining > 0 ? (
              <Link to="/candidate/cv?new=1" className="btn btn-p">
                Tải CV lên
              </Link>
            ) : (
              <button type="button" className="btn btn-p" disabled title="Đã đủ số CV tối đa">
                Tải CV lên
              </button>
            )}
            {remaining > 0 ? (
              <Link to="/candidate/cv/edit?new=1" className="btn btn-g">
                Tạo CV từ đầu
              </Link>
            ) : (
              <button type="button" className="btn btn-g" disabled title="Đã đủ số CV tối đa">
                Tạo CV từ đầu
              </button>
            )}
          </div>
        </div>

        {cvs === null ? (
          <p className="muted">Đang tải…</p>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 340px), 1fr))",
              gap: 18,
            }}
          >
            {cvs.map((c) => (
              <article
                key={c.id}
                className="card"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                  border: c.main ? "2px solid var(--brand)" : undefined,
                }}
              >
                <div
                  aria-hidden="true"
                  style={{
                    height: 170,
                    background: "var(--sky)",
                    border: "1px solid var(--line)",
                    padding: 18,
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                  }}
                >
                  <div style={{ height: 12, width: "55%", background: "var(--line-strong)" }} />
                  <div style={{ height: 8, width: "35%", background: "var(--line)" }} />
                  <div style={{ height: 1, background: "var(--line-strong)", margin: "6px 0" }} />
                  <div style={{ height: 7, width: "90%", background: "var(--line)" }} />
                  <div style={{ height: 7, width: "80%", background: "var(--line)" }} />
                  <div style={{ height: 7, width: "85%", background: "var(--line)" }} />
                  <div style={{ height: 7, width: "60%", background: "var(--line)" }} />
                </div>

                <div className="between">
                  <h3 style={{ fontSize: 18 }}>{c.title}</h3>
                  {c.main ? <span className="badge b-brand">CV chính</span> : null}
                </div>

                <p className="small muted">
                  {c.fileName ? `Tải lên ${c.fileName}` : "Tạo từ form"} · Cập nhật {shortDate(c.updatedAt)}
                </p>

                <div className="row" style={{ gap: 6 }}>
                  {c.skills.slice(0, 8).map((s) => (
                    <span key={s} className="tag">
                      {s}
                    </span>
                  ))}
                </div>

                <div
                  className="row"
                  style={{
                    gap: 8,
                    borderTop: "1px solid var(--line)",
                    paddingTop: 14,
                    marginTop: "auto",
                  }}
                >
                  <Link to={`/candidate/cv/edit?cvId=${c.id}`} className="btn btn-g btn-sm">
                    Sửa
                  </Link>
                  <button
                    type="button"
                    className="btn btn-g btn-sm"
                    disabled={busyId === c.id}
                    onClick={() => onRename(c)}
                  >
                    Đổi tên
                  </button>
                  <button
                    type="button"
                    className="btn btn-g btn-sm"
                    disabled={!c.fileName}
                    onClick={() => onDownload(c)}
                  >
                    Tải file
                  </button>
                  {!c.main ? (
                    <button
                      type="button"
                      className="btn btn-g btn-sm"
                      disabled={busyId === c.id}
                      onClick={() => onSetMain(c)}
                    >
                      Đặt làm CV chính
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="btn btn-d btn-sm"
                    style={{ marginLeft: "auto" }}
                    disabled={busyId === c.id || c.inActiveApplication}
                    title={c.inActiveApplication ? "CV đang đính kèm trong đơn ứng tuyển chưa kết thúc" : undefined}
                    onClick={() => setConfirmDelete(c)}
                  >
                    Xóa
                  </button>
                </div>
              </article>
            ))}

            {remaining > 0 ? (
              <Link
                to="/candidate/cv?new=1"
                className="card"
                style={{
                  borderStyle: "dashed",
                  borderColor: "var(--line-strong)",
                  background: "transparent",
                  display: "grid",
                  placeItems: "center",
                  minHeight: 360,
                  textAlign: "center",
                }}
              >
                <div className="stack" style={{ alignItems: "center", gap: 8 }}>
                  <span className="disp" style={{ fontSize: 40, color: "var(--brand)" }}>
                    +
                  </span>
                  <p style={{ fontWeight: 650 }}>Thêm CV</p>
                  <p className="small muted">Còn {remaining} chỗ trống</p>
                </div>
              </Link>
            ) : null}
          </div>
        )}

        <div className="note note-warn small">
          Không thể xóa CV đang đính kèm trong đơn ứng tuyển chưa kết thúc.
        </div>
      </div>

      {confirmDelete ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="cv-del-title"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 50,
            display: "grid",
            placeItems: "center",
            padding: 16,
          }}
        >
          <div className="scrim" onClick={() => setConfirmDelete(null)} />
          <div className="modal stack" style={{ gap: 16 }}>
            <h2 id="cv-del-title" style={{ fontSize: 22 }}>
              Xác nhận xóa CV
            </h2>
            <p className="small" style={{ color: "var(--ink-soft)" }}>
              Bạn có chắc muốn xóa <strong>{confirmDelete.title}</strong>
              {confirmDelete.fileName ? ` (${confirmDelete.fileName})` : ""}?
              Thao tác này không thể hoàn tác.
            </p>
            {confirmDelete.inActiveApplication ? (
              <p className="note note-warn small">
                CV này đang đính kèm trong một đơn ứng tuyển chưa kết thúc.
              </p>
            ) : null}
            <div className="row" style={{ justifyContent: "flex-end", gap: 10 }}>
              <button
                type="button"
                className="btn btn-g btn-sm"
                disabled={busyId === confirmDelete.id}
                onClick={() => setConfirmDelete(null)}
              >
                Hủy
              </button>
              <button
                type="button"
                className="btn btn-d btn-sm"
                disabled={busyId === confirmDelete.id}
                onClick={onConfirmRemove}
              >
                {busyId === confirmDelete.id ? "Đang xóa…" : "Xóa CV"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
