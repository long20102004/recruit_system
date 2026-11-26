import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  CV_ACCENT_OPTIONS,
  CV_TEMPLATE_SECTIONS,
  CV_TONE_OPTIONS,
  createCvTemplate,
  deleteCvTemplate,
  listCvTemplates,
  updateCvTemplate,
  type CvPreviewTone,
  type CvTemplateDto,
  type CvTemplateLayout,
  type CvTemplatePayload,
  type CvTemplateStatus,
} from "../../api/mock/adminMock";
import { EmptyNote, MockNote, RecruiterLayout } from "../../components/common";
import { useToast } from "../../context/ToastContext";

const TONE_BG: Record<CvPreviewTone, string> = {
  sky: "var(--sky)",
  brand: "var(--brand-soft)",
  paper: "var(--paper)",
  ok: "var(--ok-soft)",
};

const EMPTY_FORM: CvTemplatePayload = {
  name: "",
  status: "ACTIVE",
  accentToken: "var(--brand)",
  layout: "TWO_COLUMN",
  sections: ["Cá nhân", "Kinh nghiệm", "Học vấn", "Kỹ năng"],
  previewTone: "brand",
};

/** Màn AD06 · Quản lý mẫu CV (design canvas CvTemplates.dc.html). */
export function AdminCvTemplatesPage() {
  const { toast } = useToast();
  const [templates, setTemplates] = useState<CvTemplateDto[] | null>(null);
  const [previewing, setPreviewing] = useState<CvTemplateDto | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<CvTemplatePayload>(EMPTY_FORM);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const list = await listCvTemplates();
      setTemplates(list);
    } catch (e: unknown) {
      setTemplates([]);
      toast(e instanceof Error ? e.message : "Không tải được danh sách mẫu CV.");
    }
  }, [toast]);

  useEffect(() => {
    void load();
  }, [load]);

  function openCreate() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setFormOpen(true);
  }

  function openEdit(tpl: CvTemplateDto) {
    setEditingId(tpl.id);
    setForm({
      name: tpl.name,
      status: tpl.status,
      accentToken: tpl.accentToken,
      layout: tpl.layout,
      sections: [...tpl.sections],
      previewTone: tpl.previewTone,
    });
    setFormOpen(true);
  }

  function toggleSection(section: string) {
    setForm((prev) => {
      const exists = prev.sections.includes(section);
      return {
        ...prev,
        sections: exists
          ? prev.sections.filter((s) => s !== section)
          : [...prev.sections, section],
      };
    });
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) {
      toast("Vui lòng nhập tên mẫu CV.");
      return;
    }
    if (form.sections.length === 0) {
      toast("Vui lòng chọn ít nhất một mục hiển thị.");
      return;
    }

    setBusy(true);
    try {
      if (editingId === null) {
        const created = await createCvTemplate(form);
        toast(`Đã tạo mẫu “${created.name}”`);
      } else {
        const updated = await updateCvTemplate(editingId, form);
        if (previewing?.id === updated.id) setPreviewing(updated);
        toast(`Đã lưu mẫu “${updated.name}”`);
      }
      setFormOpen(false);
      setEditingId(null);
      await load();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Không lưu được mẫu CV.");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(tpl: CvTemplateDto) {
    setBusy(true);
    try {
      await deleteCvTemplate(tpl.id);
      if (editingId === tpl.id) {
        setFormOpen(false);
        setEditingId(null);
      }
      if (previewing?.id === tpl.id) {
        setPreviewing(null);
      }
      toast(`Đã xoá mẫu “${tpl.name}”`);
      await load();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Không xoá được mẫu CV.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RecruiterLayout active="templates">
      <MockNote />

      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1 style={{ fontSize: 32 }}>Mẫu CV</h1>
          <p className="muted">Mẫu dùng khi ứng viên xuất CV ra PDF. Không ảnh hưởng matching.</p>
        </div>
        <button type="button" className="btn btn-p" onClick={openCreate}>
          + Thêm mẫu
        </button>
      </div>

      {templates === null ? (
        <p className="muted">Đang tải danh sách mẫu CV…</p>
      ) : templates.length === 0 ? (
        <EmptyNote>Chưa có mẫu CV nào. Nhấn “+ Thêm mẫu” để tạo mới.</EmptyNote>
      ) : (
        <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 260px), 1fr))", gap: 16 }}>
          {templates.map((tpl) => (
            <article key={tpl.id} className="card" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div
                style={{
                  height: 180,
                  padding: 18,
                  display: "flex",
                  flexDirection: "column",
                  gap: 7,
                  border: "1px solid var(--line)",
                  background: TONE_BG[tpl.previewTone],
                }}
              >
                <div style={{ height: 12, width: "55%", background: tpl.accentToken, opacity: 0.75 }} />
                <div style={{ height: 7, width: "35%", background: "var(--ink-soft)", opacity: 0.35 }} />
                <div style={{ height: 1, background: "var(--line-strong)", margin: "8px 0" }} />
                {tpl.layout === "TWO_COLUMN" ? (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: 10, flex: 1 }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      <div style={{ height: 6, width: "85%", background: "var(--ink-soft)", opacity: 0.25 }} />
                      <div style={{ height: 6, width: "70%", background: "var(--ink-soft)", opacity: 0.2 }} />
                      <div style={{ height: 6, width: "90%", background: "var(--ink-soft)", opacity: 0.2 }} />
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      <div style={{ height: 6, width: "95%", background: "var(--ink-soft)", opacity: 0.25 }} />
                      <div style={{ height: 6, width: "85%", background: "var(--ink-soft)", opacity: 0.2 }} />
                      <div style={{ height: 6, width: "90%", background: "var(--ink-soft)", opacity: 0.2 }} />
                    </div>
                  </div>
                ) : (
                  <>
                    <div style={{ height: 6, width: "90%", background: "var(--ink-soft)", opacity: 0.22 }} />
                    <div style={{ height: 6, width: "80%", background: "var(--ink-soft)", opacity: 0.22 }} />
                    <div style={{ height: 6, width: "85%", background: "var(--ink-soft)", opacity: 0.22 }} />
                  </>
                )}
              </div>

              <div className="between">
                <h3 style={{ fontSize: 17 }}>{tpl.name}</h3>
                <span className={tpl.status === "ACTIVE" ? "badge b-ok" : "badge b-plain"}>
                  {tpl.status === "ACTIVE" ? "Đang dùng" : "Ẩn"}
                </span>
              </div>

              <p className="tiny muted">
                {tpl.usedCount.toLocaleString("vi-VN")} CV đang dùng · sửa {tpl.updatedAt}
              </p>

              <div className="row" style={{ gap: 8, borderTop: "1px solid var(--line)", paddingTop: 12 }}>
                <button type="button" className="btn btn-g btn-sm" onClick={() => setPreviewing(tpl)}>
                  Xem trước
                </button>
                <button type="button" className="btn btn-g btn-sm" onClick={() => openEdit(tpl)}>
                  Sửa
                </button>
                <button
                  type="button"
                  className="btn btn-d btn-sm"
                  style={{ marginLeft: "auto" }}
                  disabled={busy}
                  onClick={() => void onDelete(tpl)}
                >
                  Xoá
                </button>
              </div>
            </article>
          ))}
        </section>
      )}

      {previewing ? (
        <section className="card stack" style={{ gap: 14, maxWidth: 760 }}>
          <div className="between">
            <h3 style={{ fontSize: 18 }}>Xem trước mẫu “{previewing.name}”</h3>
            <button type="button" className="btn btn-g btn-sm" onClick={() => setPreviewing(null)}>
              Đóng
            </button>
          </div>
          <div
            style={{
              padding: 24,
              border: "1px solid var(--line)",
              background: TONE_BG[previewing.previewTone],
              display: "flex",
              flexDirection: "column",
              gap: 14,
            }}
          >
            <div style={{ borderLeft: `4px solid ${previewing.accentToken}`, paddingLeft: 12 }}>
              <p className="disp" style={{ fontSize: 20 }}>Nguyễn Văn An</p>
              <p className="small muted">Senior Backend Developer · {previewing.layout === "TWO_COLUMN" ? "Bố cục hai cột" : "Bố cục một cột"}</p>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: previewing.layout === "TWO_COLUMN" ? "1fr 1.6fr" : "1fr",
                gap: 12,
              }}
            >
              {previewing.sections.map((sec) => (
                <div
                  key={sec}
                  style={{
                    background: "var(--paper)",
                    border: "1px solid var(--line)",
                    padding: "10px 12px",
                  }}
                >
                  <p className="small" style={{ fontWeight: 700, color: previewing.accentToken }}>{sec}</p>
                  <p className="tiny muted" style={{ marginTop: 4 }}>Nội dung mẫu hiển thị cho mục {sec.toLowerCase()}.</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      {formOpen ? (
        <form className="card stack" style={{ gap: 14, maxWidth: 760 }} onSubmit={(e) => void onSave(e)}>
          <h3 style={{ fontSize: 18 }}>
            {editingId === null ? "Thêm mẫu CV mới" : `Sửa mẫu “${form.name || "Chưa đặt tên"}”`}
          </h3>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="tpl-name">Tên mẫu</label>
              <input
                id="tpl-name"
                className="input"
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                placeholder="Ví dụ: Hiện đại"
              />
            </div>
            <div className="field">
              <label htmlFor="tpl-status">Trạng thái</label>
              <select
                id="tpl-status"
                className="input"
                value={form.status}
                onChange={(e) => setForm((p) => ({ ...p, status: e.target.value as CvTemplateStatus }))}
              >
                <option value="ACTIVE">Đang dùng</option>
                <option value="HIDDEN">Ẩn</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="tpl-accent">Màu nhấn</label>
              <select
                id="tpl-accent"
                className="input"
                value={form.accentToken}
                onChange={(e) => setForm((p) => ({ ...p, accentToken: e.target.value }))}
              >
                {CV_ACCENT_OPTIONS.map((opt) => (
                  <option key={opt.token} value={opt.token}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="tpl-layout">Bố cục</label>
              <select
                id="tpl-layout"
                className="input"
                value={form.layout}
                onChange={(e) => setForm((p) => ({ ...p, layout: e.target.value as CvTemplateLayout }))}
              >
                <option value="TWO_COLUMN">Hai cột</option>
                <option value="ONE_COLUMN">Một cột</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="tpl-tone">Nền xem trước</label>
              <select
                id="tpl-tone"
                className="input"
                value={form.previewTone}
                onChange={(e) => setForm((p) => ({ ...p, previewTone: e.target.value as CvPreviewTone }))}
              >
                {CV_TONE_OPTIONS.map((opt) => (
                  <option key={opt.tone} value={opt.tone}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div className="field span2">
              <span className="lbl">Các mục hiển thị</span>
              <div className="row" style={{ gap: 6 }}>
                {CV_TEMPLATE_SECTIONS.map((sec) => {
                  const selected = form.sections.includes(sec);
                  return (
                    <button
                      key={sec}
                      type="button"
                      aria-pressed={selected}
                      className={selected ? "tag tag-on" : "tag"}
                      onClick={() => toggleSection(sec)}
                    >
                      {sec}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button
              type="button"
              className="btn btn-g"
              onClick={() => {
                setFormOpen(false);
                setEditingId(null);
              }}
            >
              Huỷ
            </button>
            <button type="submit" className="btn btn-p" disabled={busy}>
              Lưu mẫu
            </button>
          </div>
        </form>
      ) : null}
    </RecruiterLayout>
  );
}
