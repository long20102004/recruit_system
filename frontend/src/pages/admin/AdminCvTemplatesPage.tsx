import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  ApiError,
  cvTemplatesApi,
  type AdminCvTemplateDto,
  type CvTemplateConfig,
  type CvTemplateOptionsDto,
  type CvTemplateType,
} from "../../api/client";
import { CvTemplateThumb } from "../../components/CvTemplateThumb";
import { EmptyNote, RecruiterLayout } from "../../components/common";
import { useToast } from "../../context/ToastContext";
import { shortDate } from "../../utils/format";

const MAX_DOCX_BYTES = 2 * 1024 * 1024;

type ModalMode = "CREATE" | "EDIT_CONFIG" | "REPLACE_DOCX" | null;

function defaultConfig(opts: CvTemplateOptionsDto | null): CvTemplateConfig {
  return {
    layout: opts?.layouts[0]?.value ?? "ONE_COLUMN",
    font: opts?.fonts[0]?.value ?? "Tinos",
    accent: opts?.accents[0]?.value ?? "#1f1d1a",
    background: opts?.backgrounds[0]?.value ?? "#ffffff",
    header: opts?.headers[0]?.value ?? "LEFT",
    heading: opts?.headings[0]?.value ?? "UPPERCASE_RULE",
    dates: opts?.dates[0]?.value ?? "RIGHT_INLINE",
    density: opts?.densities[0]?.value ?? "NORMAL",
    margin: opts?.margins[1]?.value ?? opts?.margins[0]?.value ?? "NORMAL",
    sections:
      opts?.sections.map((s) => s.value) ?? [
        "info",
        "objective",
        "education",
        "experience",
        "projects",
        "skills",
        "certificates",
        "languages",
        "honours",
      ],
  };
}

function extractErrorDetails(err: unknown): { message: string; details: string[] } {
  if (err instanceof ApiError) {
    const details: string[] = [];
    if (err.data) {
      for (const value of Object.values(err.data)) {
        if (Array.isArray(value)) {
          for (const item of value) {
            if (typeof item === "string" && item.trim()) details.push(item);
            else if (item != null && typeof item === "object") details.push(JSON.stringify(item));
          }
        } else if (typeof value === "string" && value.trim() && value !== err.message) {
          details.push(value);
        }
      }
    }
    return { message: err.message, details };
  }
  return {
    message: err instanceof Error ? err.message : "Thao tác thất bại.",
    details: [],
  };
}

/** Màn AD06 · Quản lý mẫu CV (specs/011-cv-templates). */
export function AdminCvTemplatesPage() {
  const { toast } = useToast();
  const [templates, setTemplates] = useState<AdminCvTemplateDto[] | null>(null);
  const [options, setOptions] = useState<CvTemplateOptionsDto | null>(null);
  const [busy, setBusy] = useState(false);

  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [tplType, setTplType] = useState<CvTemplateType>("CONFIG");
  const [editingTpl, setEditingTpl] = useState<AdminCvTemplateDto | null>(null);
  const [name, setName] = useState("");
  const [config, setConfig] = useState<CvTemplateConfig>(() => defaultConfig(null));

  const [previewHtml, setPreviewHtml] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const [docxFile, setDocxFile] = useState<File | null>(null);
  const [docxError, setDocxError] = useState<string | null>(null);
  const [docxErrorDetails, setDocxErrorDetails] = useState<string[]>([]);

  const [pdfPreview, setPdfPreview] = useState<{ name: string; url: string } | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<AdminCvTemplateDto | null>(null);

  const load = useCallback(async () => {
    try {
      const [list, opts] = await Promise.all([
        cvTemplatesApi.adminList(),
        options ? Promise.resolve(options) : cvTemplatesApi.adminOptions(),
      ]);
      setTemplates(list);
      if (!options) setOptions(opts);
    } catch (e: unknown) {
      setTemplates([]);
      toast(e instanceof Error ? e.message : "Không tải được danh sách mẫu CV.");
    }
  }, [options, toast]);

  useEffect(() => {
    let alive = true;
    Promise.all([cvTemplatesApi.adminList(), cvTemplatesApi.adminOptions()])
      .then(([list, opts]) => {
        if (!alive) return;
        setTemplates(list);
        setOptions(opts);
      })
      .catch((e: unknown) => {
        if (!alive) return;
        setTemplates([]);
        toast(e instanceof Error ? e.message : "Không tải được danh sách mẫu CV.");
      });
    return () => {
      alive = false;
    };
  }, [toast]);

  const isConfigForm =
    modalMode === "EDIT_CONFIG" || (modalMode === "CREATE" && tplType === "CONFIG");

  // Debounce ~400ms cập nhật iframe xem trước cấu hình
  useEffect(() => {
    if (!isConfigForm) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setPreviewLoading(true);
      setPreviewError(null);
      cvTemplatesApi
        .adminPreviewConfig(config, controller.signal)
        .then((html) => {
          if (!controller.signal.aborted) {
            setPreviewHtml(html);
          }
        })
        .catch((err: unknown) => {
          if (controller.signal.aborted) return;
          setPreviewError(
            err instanceof ApiError && err.status === 404
              ? "Không gọi được API xem trước (404). Kiểm tra api-gateway đã khởi động lại với route /api/admin/cv-templates."
              : err instanceof Error ? err.message : "Không tải được xem trước."
          );
        })
        .finally(() => {
          if (!controller.signal.aborted) setPreviewLoading(false);
        });
    }, 400);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [isConfigForm, config]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (pdfPreview) setPdfPreview(null);
      else if (confirmDelete) setConfirmDelete(null);
      else if (modalMode) setModalMode(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pdfPreview, confirmDelete, modalMode]);

  const sectionLabelMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const s of options?.sections ?? []) map.set(s.value, s.label);
    return map;
  }, [options]);

  const inactiveSections = useMemo(() => {
    const active = new Set(config.sections);
    return (options?.sections ?? []).filter((s) => !active.has(s.value));
  }, [options, config.sections]);

  function openCreate() {
    setModalMode("CREATE");
    setEditingTpl(null);
    setTplType("CONFIG");
    setName("");
    setConfig(defaultConfig(options));
    setPreviewHtml("");
    setPreviewError(null);
    setDocxFile(null);
    setDocxError(null);
    setDocxErrorDetails([]);
  }

  function openEditConfig(tpl: AdminCvTemplateDto) {
    const base = defaultConfig(options);
    setModalMode("EDIT_CONFIG");
    setEditingTpl(tpl);
    setTplType("CONFIG");
    setName(tpl.name);
    setConfig({
      ...base,
      ...(tpl.config ?? {}),
      sections: tpl.config?.sections?.length ? [...tpl.config.sections] : base.sections,
    });
    setPreviewHtml("");
    setPreviewError(null);
  }

  function openReplaceDocx(tpl: AdminCvTemplateDto) {
    setModalMode("REPLACE_DOCX");
    setEditingTpl(tpl);
    setTplType("DOCX");
    setName(tpl.name);
    setDocxFile(null);
    setDocxError(null);
    setDocxErrorDetails([]);
  }

  function toggleSection(sectionKey: string) {
    setConfig((prev) => {
      const exists = prev.sections.includes(sectionKey);
      if (exists && prev.sections.length <= 1) {
        toast("Cần giữ ít nhất một mục hiển thị.");
        return prev;
      }
      return {
        ...prev,
        sections: exists
          ? prev.sections.filter((s) => s !== sectionKey)
          : [...prev.sections, sectionKey],
      };
    });
  }

  function moveSection(index: number, delta: -1 | 1) {
    setConfig((prev) => {
      const target = index + delta;
      if (target < 0 || target >= prev.sections.length) return prev;
      const next = [...prev.sections];
      [next[index], next[target]] = [next[target], next[index]];
      return { ...prev, sections: next };
    });
  }

  async function openPdfPreview(tpl: { id: number; name: string }) {
    setBusy(true);
    try {
      const link = await cvTemplatesApi.adminPreviewPdf(tpl.id);
      setPdfPreview({ name: tpl.name, url: link.url });
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : "Không tải được bản xem trước PDF.");
    } finally {
      setBusy(false);
    }
  }

  async function onDownloadSample() {
    try {
      await cvTemplatesApi.downloadDocxSample();
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : "Không tải được file mẫu Word.");
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();

    if (isConfigForm) {
      const trimmed = name.trim();
      if (!trimmed) {
        toast("Vui lòng nhập tên mẫu CV.");
        return;
      }
      if (config.sections.length === 0) {
        toast("Chọn ít nhất một mục hiển thị.");
        return;
      }
      setBusy(true);
      try {
        if (modalMode === "CREATE") {
          const created = await cvTemplatesApi.adminCreateConfig({ name: trimmed, config });
          toast(`Đã tạo mẫu “${created.name}”`);
        } else if (editingTpl) {
          const updated = await cvTemplatesApi.adminUpdateConfig(editingTpl.id, {
            name: trimmed,
            config,
          });
          toast(`Đã cập nhật mẫu “${updated.name}”`);
        }
        setModalMode(null);
        setEditingTpl(null);
        await load();
      } catch (err: unknown) {
        toast(err instanceof Error ? err.message : "Không lưu được mẫu CV.");
      } finally {
        setBusy(false);
      }
      return;
    }

    // Nhánh DOCX
    setDocxError(null);
    setDocxErrorDetails([]);

    if (modalMode === "CREATE" && !name.trim()) {
      setDocxError("Vui lòng nhập tên mẫu CV.");
      return;
    }
    if (!docxFile) {
      setDocxError("Vui lòng chọn file Word (.docx).");
      return;
    }
    if (!docxFile.name.toLowerCase().endsWith(".docx")) {
      setDocxError("Chỉ hỗ trợ tệp định dạng .docx (không hỗ trợ .doc hoặc .docm).");
      return;
    }
    if (docxFile.size > MAX_DOCX_BYTES) {
      setDocxError("Dung lượng tệp tối đa 2MB.");
      return;
    }

    setBusy(true);
    try {
      const saved =
        modalMode === "REPLACE_DOCX" && editingTpl
          ? await cvTemplatesApi.adminReplaceDocx(editingTpl.id, docxFile)
          : await cvTemplatesApi.adminUploadDocx(name.trim(), docxFile);
      toast(
        modalMode === "REPLACE_DOCX"
          ? `Đã thay file Word cho mẫu “${saved.name}”`
          : `Đã tải lên mẫu Word “${saved.name}”`
      );
      setModalMode(null);
      setEditingTpl(null);
      await load();
      // Mở xem trước PDF điền thử ngay sau khi upload thành công
      try {
        const link = await cvTemplatesApi.adminPreviewPdf(saved.id);
        setPdfPreview({ name: saved.name, url: link.url });
      } catch {
        // Nếu lấy link PDF lỗi, danh sách đã cập nhật và có nút Xem trước PDF
      }
    } catch (err: unknown) {
      const { message, details } = extractErrorDetails(err);
      setDocxError(message);
      setDocxErrorDetails(details);
    } finally {
      setBusy(false);
    }
  }

  async function onToggleStatus(tpl: AdminCvTemplateDto) {
    if (tpl.isDefault) return;
    const nextStatus = tpl.status === "ACTIVE" ? "HIDDEN" : "ACTIVE";
    setBusy(true);
    try {
      await cvTemplatesApi.adminSetStatus(tpl.id, nextStatus);
      toast(nextStatus === "ACTIVE" ? `Đã hiện mẫu “${tpl.name}”` : `Đã ẩn mẫu “${tpl.name}”`);
      await load();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Không cập nhật được trạng thái mẫu.");
    } finally {
      setBusy(false);
    }
  }

  async function onSetDefault(tpl: AdminCvTemplateDto) {
    if (tpl.isDefault) return;
    setBusy(true);
    try {
      await cvTemplatesApi.adminSetDefault(tpl.id);
      toast(`Đã đặt “${tpl.name}” làm mẫu mặc định.`);
      await load();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : "Không đặt được mẫu mặc định.");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirmDelete() {
    if (!confirmDelete) return;
    const target = confirmDelete;
    setBusy(true);
    try {
      await cvTemplatesApi.adminDelete(target.id);
      setConfirmDelete(null);
      toast(`Đã xoá mẫu “${target.name}”`);
      await load();
    } catch (err: unknown) {
      setConfirmDelete(null);
      toast(err instanceof Error ? err.message : "Không xoá được mẫu CV.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RecruiterLayout active="templates">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1 style={{ fontSize: 32 }}>Mẫu CV</h1>
          <p className="muted">
            Quản lý mẫu cấu hình và mẫu Word (.docx) dùng khi ứng viên xuất CV PDF. Không ảnh hưởng matching.
          </p>
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
        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 280px), 1fr))",
            gap: 16,
          }}
        >
          {templates.map((tpl) => {
            const deleteTitle = tpl.isDefault
              ? "Không thể xoá mẫu mặc định"
              : tpl.usedCount > 0
                ? `Đang có ${tpl.usedCount} CV dùng, chỉ có thể ẩn`
                : undefined;

            return (
              <article
                key={tpl.id}
                className="card"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                  border: tpl.isDefault ? "2px solid var(--brand)" : undefined,
                }}
              >
                <CvTemplateThumb
                  name={tpl.name}
                  type={tpl.type}
                  config={tpl.config}
                  thumbnailUrl={tpl.thumbnailUrl}
                  height={190}
                />

                <div className="stack" style={{ gap: 6 }}>
                  <div className="between" style={{ gap: 8 }}>
                    <h3 style={{ fontSize: 17 }}>{tpl.name}</h3>
                    <span className={tpl.status === "ACTIVE" ? "badge b-ok" : "badge b-plain"}>
                      {tpl.status === "ACTIVE" ? "Đang hiện" : "Đang ẩn"}
                    </span>
                  </div>
                  <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
                    <span className="badge b-plain">
                      {tpl.type === "CONFIG" ? "Cấu hình" : "Word"}
                    </span>
                    {tpl.isDefault ? <span className="badge b-brand">Mặc định</span> : null}
                  </div>
                </div>

                <p className="tiny muted">
                  {tpl.usedCount.toLocaleString("vi-VN")} CV đang dùng · cập nhật{" "}
                  {shortDate(tpl.updatedAt)}
                </p>

                <div
                  className="row"
                  style={{
                    gap: 6,
                    flexWrap: "wrap",
                    borderTop: "1px solid var(--line)",
                    paddingTop: 12,
                    marginTop: "auto",
                  }}
                >
                  {tpl.type === "CONFIG" ? (
                    <button
                      type="button"
                      className="btn btn-g btn-sm"
                      disabled={busy}
                      onClick={() => openEditConfig(tpl)}
                    >
                      Sửa
                    </button>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="btn btn-g btn-sm"
                        disabled={busy}
                        onClick={() => openReplaceDocx(tpl)}
                      >
                        Thay file Word
                      </button>
                      <button
                        type="button"
                        className="btn btn-g btn-sm"
                        disabled={busy}
                        onClick={() => void openPdfPreview(tpl)}
                      >
                        Xem trước PDF
                      </button>
                    </>
                  )}

                  {!tpl.isDefault ? (
                    <button
                      type="button"
                      className="btn btn-g btn-sm"
                      disabled={busy}
                      onClick={() => void onSetDefault(tpl)}
                    >
                      Đặt mặc định
                    </button>
                  ) : null}

                  <button
                    type="button"
                    className="btn btn-g btn-sm"
                    disabled={busy || tpl.isDefault}
                    title={tpl.isDefault ? "Không thể ẩn mẫu mặc định" : undefined}
                    onClick={() => void onToggleStatus(tpl)}
                  >
                    {tpl.status === "ACTIVE" ? "Ẩn" : "Hiện"}
                  </button>

                  <button
                    type="button"
                    className="btn btn-d btn-sm"
                    style={{ marginLeft: "auto" }}
                    disabled={busy || tpl.isDefault || tpl.usedCount > 0}
                    title={deleteTitle}
                    onClick={() => setConfirmDelete(tpl)}
                  >
                    Xoá
                  </button>
                </div>
              </article>
            );
          })}
        </section>
      )}

      {modalMode ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="cvt-modal-title"
          className="cvt-dialog"
        >
          <div className="scrim" onClick={() => !busy && setModalMode(null)} />
          <form
            className={`modal stack ${isConfigForm ? "cvt-modal-wide" : "cvt-modal-md"}`}
            style={{ gap: 16 }}
            onSubmit={(e) => void onSubmit(e)}
          >
            <div className="between">
              <h2 id="cvt-modal-title" style={{ fontSize: 22 }}>
                {modalMode === "CREATE"
                  ? "Thêm mẫu CV mới"
                  : modalMode === "EDIT_CONFIG"
                    ? `Sửa mẫu cấu hình “${editingTpl?.name ?? ""}”`
                    : `Thay file Word cho “${editingTpl?.name ?? ""}”`}
              </h2>
              <button
                type="button"
                className="btn btn-g btn-sm"
                disabled={busy}
                onClick={() => setModalMode(null)}
              >
                Đóng
              </button>
            </div>

            {modalMode === "CREATE" ? (
              <div className="row" style={{ gap: 8 }}>
                <button
                  type="button"
                  className={tplType === "CONFIG" ? "btn btn-p btn-sm" : "btn btn-g btn-sm"}
                  onClick={() => setTplType("CONFIG")}
                >
                  Mẫu cấu hình
                </button>
                <button
                  type="button"
                  className={tplType === "DOCX" ? "btn btn-p btn-sm" : "btn btn-g btn-sm"}
                  onClick={() => setTplType("DOCX")}
                >
                  Mẫu Word (.docx)
                </button>
              </div>
            ) : null}

            {isConfigForm ? (
              <div className="cvt-config-grid">
                <div className="stack" style={{ gap: 14 }}>
                  <div className="field">
                    <label htmlFor="cvt-name">Tên mẫu</label>
                    <input
                      id="cvt-name"
                      className="input"
                      maxLength={80}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Ví dụ: Harvard Cổ điển"
                    />
                  </div>

                  <div className="form-grid">
                    <div className="field">
                      <label htmlFor="cvt-layout">Bố cục</label>
                      <select
                        id="cvt-layout"
                        className="input"
                        value={config.layout}
                        onChange={(e) => setConfig((c) => ({ ...c, layout: e.target.value }))}
                      >
                        {(options?.layouts ?? []).map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="field">
                      <label htmlFor="cvt-font">Phông chữ</label>
                      <select
                        id="cvt-font"
                        className="input"
                        value={config.font}
                        onChange={(e) => setConfig((c) => ({ ...c, font: e.target.value }))}
                      >
                        {(options?.fonts ?? []).map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="field">
                      <label htmlFor="cvt-header">Căn phần đầu</label>
                      <select
                        id="cvt-header"
                        className="input"
                        value={config.header}
                        onChange={(e) => setConfig((c) => ({ ...c, header: e.target.value }))}
                      >
                        {(options?.headers ?? []).map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="field">
                      <label htmlFor="cvt-heading">Kiểu tiêu đề mục</label>
                      <select
                        id="cvt-heading"
                        className="input"
                        value={config.heading}
                        onChange={(e) => setConfig((c) => ({ ...c, heading: e.target.value }))}
                      >
                        {(options?.headings ?? []).map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="field">
                      <label htmlFor="cvt-dates">Vị trí thời gian</label>
                      <select
                        id="cvt-dates"
                        className="input"
                        value={config.dates}
                        onChange={(e) => setConfig((c) => ({ ...c, dates: e.target.value }))}
                      >
                        {(options?.dates ?? []).map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="field">
                      <label htmlFor="cvt-density">Độ dày</label>
                      <select
                        id="cvt-density"
                        className="input"
                        value={config.density}
                        onChange={(e) => setConfig((c) => ({ ...c, density: e.target.value }))}
                      >
                        {(options?.densities ?? []).map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="field">
                      <label htmlFor="cvt-margin">Lề trang</label>
                      <select
                        id="cvt-margin"
                        className="input"
                        value={config.margin}
                        onChange={(e) => setConfig((c) => ({ ...c, margin: e.target.value }))}
                      >
                        {(options?.margins ?? []).map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="field">
                      <label htmlFor="cvt-bg">Nền trang</label>
                      <select
                        id="cvt-bg"
                        className="input"
                        value={config.background}
                        onChange={(e) => setConfig((c) => ({ ...c, background: e.target.value }))}
                      >
                        {(options?.backgrounds ?? []).map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="field">
                    <span className="lbl">Màu nhấn</span>
                    <div className="cvt-swatches">
                      {(options?.accents ?? []).map((opt) => {
                        const active = config.accent === opt.value;
                        return (
                          <button
                            key={opt.value}
                            type="button"
                            aria-pressed={active}
                            className={active ? "cvt-swatch is-on" : "cvt-swatch"}
                            onClick={() => setConfig((c) => ({ ...c, accent: opt.value }))}
                          >
                            <span
                              className="cvt-swatch-dot"
                              style={{ background: opt.value }}
                            />
                            <span>{opt.label}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  <div className="field">
                    <span className="lbl">Các mục hiển thị &amp; thứ tự</span>
                    <div className="stack" style={{ gap: 6 }}>
                      {config.sections.map((sec, idx) => (
                        <div key={sec} className="cvt-section-row">
                          <label className="cvx-check" style={{ gap: 8 }}>
                            <input
                              type="checkbox"
                              checked
                              onChange={() => toggleSection(sec)}
                            />
                            <span>{sectionLabelMap.get(sec) ?? sec}</span>
                          </label>
                          <div className="row" style={{ gap: 4 }}>
                            <button
                              type="button"
                              className="btn btn-g btn-sm"
                              aria-label={`Đưa mục ${sectionLabelMap.get(sec) ?? sec} lên`}
                              disabled={idx === 0}
                              onClick={() => moveSection(idx, -1)}
                            >
                              ↑
                            </button>
                            <button
                              type="button"
                              className="btn btn-g btn-sm"
                              aria-label={`Đưa mục ${sectionLabelMap.get(sec) ?? sec} xuống`}
                              disabled={idx === config.sections.length - 1}
                              onClick={() => moveSection(idx, 1)}
                            >
                              ↓
                            </button>
                          </div>
                        </div>
                      ))}

                      {inactiveSections.map((sec) => (
                        <div
                          key={sec.value}
                          className="cvt-section-row"
                          style={{ opacity: 0.72 }}
                        >
                          <label className="cvx-check" style={{ gap: 8 }}>
                            <input
                              type="checkbox"
                              checked={false}
                              onChange={() => toggleSection(sec.value)}
                            />
                            <span>{sec.label}</span>
                          </label>
                          <span className="tiny muted">Đang ẩn</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="stack cvt-preview-col" style={{ gap: 8 }}>
                  <div className="between">
                    <span className="lbl">Xem trước trực tiếp</span>
                    {previewLoading ? <span className="tiny muted">Đang cập nhật…</span> : null}
                  </div>
                  {previewError ? (
                    <p className="note note-warn small">{previewError}</p>
                  ) : null}
                  <iframe
                    title="Xem trước mẫu CV"
                    sandbox=""
                    srcDoc={previewHtml}
                    className="cvt-preview-iframe"
                  />
                </div>
              </div>
            ) : (
              <div className="stack" style={{ gap: 14 }}>
                {modalMode === "CREATE" ? (
                  <div className="field">
                    <label htmlFor="cvt-docx-name">Tên mẫu</label>
                    <input
                      id="cvt-docx-name"
                      className="input"
                      maxLength={80}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Ví dụ: Harvard Word"
                    />
                  </div>
                ) : null}

                <div className="note small stack" style={{ gap: 8 }}>
                  <div className="between" style={{ gap: 12, flexWrap: "wrap" }}>
                    <span>
                      Thiết kế bằng Word (.docx, ≤ 2MB, không macro). Nên dùng font có sẵn trên hệ
                      thống (Tinos, Liberation Serif/Sans, Noto).
                    </span>
                    <button
                      type="button"
                      className="btn btn-g btn-sm"
                      onClick={() => void onDownloadSample()}
                    >
                      Tải file mẫu Word Harvard
                    </button>
                  </div>
                </div>

                {options?.docxPlaceholders?.length ? (
                  <div className="stack" style={{ gap: 6 }}>
                    <span className="lbl">Danh sách ký hiệu điền chỗ được hỗ trợ</span>
                    <div
                      style={{
                        maxHeight: 220,
                        overflowY: "auto",
                        border: "1px solid var(--line)",
                        background: "var(--paper)",
                      }}
                    >
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                        <thead>
                          <tr style={{ borderBottom: "1px solid var(--line)", textAlign: "left" }}>
                            <th style={{ padding: "8px 10px" }}>Ký hiệu</th>
                            <th style={{ padding: "8px 10px" }}>Mô tả</th>
                            <th style={{ padding: "8px 10px" }}>Phạm vi</th>
                          </tr>
                        </thead>
                        <tbody>
                          {options.docxPlaceholders.map((p) => (
                            <tr key={p.tag} style={{ borderBottom: "1px solid var(--line)" }}>
                              <td style={{ padding: "6px 10px", fontFamily: "monospace", fontSize: 12 }}>
                                {p.tag}
                              </td>
                              <td style={{ padding: "6px 10px" }}>{p.description}</td>
                              <td style={{ padding: "6px 10px" }} className="muted">
                                {p.scope}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : null}

                <div className="field">
                  <label htmlFor="cvt-docx-file">Chọn tệp Word (.docx)</label>
                  <input
                    id="cvt-docx-file"
                    type="file"
                    accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    onChange={(e) => {
                      const f = e.target.files?.[0] ?? null;
                      setDocxFile(f);
                      setDocxError(null);
                      setDocxErrorDetails([]);
                    }}
                  />
                  {docxFile ? (
                    <span className="tiny muted">
                      Đã chọn: {docxFile.name} ({Math.ceil(docxFile.size / 1024)} KB)
                    </span>
                  ) : null}
                </div>

                {docxError ? (
                  <div className="note note-warn small stack" style={{ gap: 6 }}>
                    <p style={{ fontWeight: 600 }}>{docxError}</p>
                    {docxErrorDetails.length > 0 ? (
                      <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {docxErrorDetails.map((d, idx) => (
                          <li key={idx}>{d}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                ) : null}
              </div>
            )}

            <div className="row" style={{ justifyContent: "flex-end", gap: 10 }}>
              <button
                type="button"
                className="btn btn-g"
                disabled={busy}
                onClick={() => setModalMode(null)}
              >
                Huỷ
              </button>
              <button type="submit" className="btn btn-p" disabled={busy}>
                {busy
                  ? "Đang xử lý…"
                  : isConfigForm
                    ? "Lưu mẫu"
                    : "Upload & kiểm tra"}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {pdfPreview ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="cvt-pdf-title"
          className="cvt-dialog"
        >
          <div className="scrim" onClick={() => setPdfPreview(null)} />
          <div className="modal stack cvt-modal-wide" style={{ gap: 14 }}>
            <div className="between">
              <h2 id="cvt-pdf-title" style={{ fontSize: 20 }}>
                Xem trước PDF · {pdfPreview.name}
              </h2>
              <div className="row" style={{ gap: 8 }}>
                <a
                  href={pdfPreview.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-g btn-sm"
                >
                  Mở tab mới
                </a>
                <button
                  type="button"
                  className="btn btn-p btn-sm"
                  onClick={() => setPdfPreview(null)}
                >
                  Đóng
                </button>
              </div>
            </div>
            <iframe
              title={`Xem trước PDF ${pdfPreview.name}`}
              src={pdfPreview.url}
              className="cvt-preview-iframe"
            />
          </div>
        </div>
      ) : null}

      {confirmDelete ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="cvt-del-title"
          className="cvt-dialog"
        >
          <div className="scrim" onClick={() => !busy && setConfirmDelete(null)} />
          <div className="modal stack" style={{ gap: 16 }}>
            <h2 id="cvt-del-title" style={{ fontSize: 22 }}>
              Xác nhận xoá mẫu CV
            </h2>
            <p className="small" style={{ color: "var(--ink-soft)" }}>
              Bạn có chắc muốn xoá mẫu <strong>{confirmDelete.name}</strong>? Thao tác này không thể
              hoàn tác.
            </p>
            <div className="row" style={{ justifyContent: "flex-end", gap: 10 }}>
              <button
                type="button"
                className="btn btn-g btn-sm"
                disabled={busy}
                onClick={() => setConfirmDelete(null)}
              >
                Huỷ
              </button>
              <button
                type="button"
                className="btn btn-d btn-sm"
                disabled={busy}
                onClick={() => void onConfirmDelete()}
              >
                {busy ? "Đang xoá…" : "Xoá mẫu"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </RecruiterLayout>
  );
}
