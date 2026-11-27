import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { CvTemplateThumb } from "../../components/CvTemplateThumb";
import { SiteHeader } from "../../components/common";
import {
  cvTemplatesApi,
  cvsApi,
  type CandidateCvTemplateDto,
  type CandidateProfileDto,
  type CvFormDto,
} from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { CvProfileEditor } from "./CvProfileEditor";
import { CV_SECTIONS, cleanProfile, normalizeProfile, sectionFilled, type CvSection } from "./cvProfile";

/**
 * C04 · Tạo / sửa CV (Figma: CvEditor). Sửa nội dung theo từng mục, không cần tải file.
 * ?cvId=X: sửa CV X; ?new=1&templateId=Y: tạo CV từ đầu theo mẫu Y (chỉ tạo CV khi bấm Lưu).
 * "Đang tìm việc", tự lưu nháp chưa có backend: hiện "Sắp có".
 */

/** Field "Kỹ năng suy ra" không thuộc CandidateProfile nên lưu qua fields (giống C03). */
const INFERRED_FIELD = "Kỹ năng suy ra";
const MAX_TITLE = 120;

function cleanLines(lines: string[] | null | undefined): string[] {
  return (lines ?? []).flatMap((l) => l.split(/\r?\n/)).map((l) => l.trim()).filter(Boolean);
}

function snapshot(title: string, profile: CandidateProfileDto, inferred: string[] | null) {
  return JSON.stringify([title.trim(), cleanProfile(profile), inferred ? cleanLines(inferred) : null]);
}

function Soon() {
  return <span className="cvu-badge cve-soon">Sắp có</span>;
}

export function CandidateCvEditorPage() {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const paramId = Number(params.get("cvId")) || null;
  const paramTemplateId = Number(params.get("templateId")) || null;
  const isNew = params.get("new") === "1" && paramId == null;

  const [loaded, setLoaded] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [cvId, setCvId] = useState<number | null>(paramId);
  const [title, setTitle] = useState("");
  const [isMain, setIsMain] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [profile, setProfile] = useState<CandidateProfileDto>(() => normalizeProfile(null));
  const [inferred, setInferred] = useState<string[] | null>(null);
  const [saved, setSaved] = useState("");
  const [section, setSection] = useState<CvSection>("info");
  const [saving, setSaving] = useState(false);

  const [templates, setTemplates] = useState<CandidateCvTemplateDto[]>([]);
  const [templatesLoaded, setTemplatesLoaded] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(
    isNew ? paramTemplateId : null
  );
  const [switchingTemplate, setSwitchingTemplate] = useState(false);

  const [previewHtml, setPreviewHtml] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [docxPreviewUrl, setDocxPreviewUrl] = useState<string | null>(null);
  const [docxPreviewLoading, setDocxPreviewLoading] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);

  function applyForm(form: CvFormDto) {
    const p = normalizeProfile(form.profile);
    const inf = form.fields.find((f) => f.field === INFERRED_FIELD);
    const i = inf ? cleanLines(inf.values) : null;
    const t = form.title ?? "";
    setCvId(form.cvId);
    setTitle(t);
    setIsMain(form.main);
    setFileName(form.fileName);
    setProfile(p);
    setInferred(i);
    if (form.templateId != null) {
      setSelectedTemplateId(form.templateId);
    }
    setSaved(snapshot(t, p, i));
  }

  useEffect(() => {
    let alive = true;
    cvTemplatesApi
      .listActive()
      .then((list) => {
        if (!alive) return;
        setTemplates(list);
        const def = list.find((t) => t.isDefault) ?? list[0] ?? null;
        if (def) {
          setSelectedTemplateId((prev) => prev ?? def.id);
        }
      })
      .catch((e) => {
        if (alive) toast(e instanceof Error ? e.message : "Không tải được danh sách mẫu CV");
      })
      .finally(() => {
        if (alive) setTemplatesLoaded(true);
      });
    return () => {
      alive = false;
    };
  }, [toast]);

  useEffect(() => {
    let alive = true;
    setLoaded(false);
    setLoadError(null);
    setSection("info");
    setDocxPreviewUrl(null);
    setPreviewHtml("");
    setPreviewError(null);
    if (isNew) {
      const p = normalizeProfile(null);
      setCvId(null);
      setTitle("");
      setIsMain(false);
      setFileName(null);
      setProfile(p);
      setInferred(null);
      setSelectedTemplateId(paramTemplateId);
      setSaved(snapshot("", p, null));
      setLoaded(true);
      return;
    }
    cvsApi
      .mine(paramId)
      .then((form) => {
        if (!alive) return;
        if (form.cvId == null) {
          // Chưa có CV nào: chuyển sang tạo từ đầu.
          navigate("/candidate/cv/edit?new=1", { replace: true });
          return;
        }
        applyForm(form);
      })
      .catch((e) => alive && setLoadError(e instanceof Error ? e.message : "Không tải được CV"))
      .finally(() => alive && setLoaded(true));
    return () => {
      alive = false;
    };
  }, [paramId, paramTemplateId, isNew, navigate]);

  const selectedTemplate = useMemo(
    () => templates.find((t) => t.id === selectedTemplateId) ?? null,
    [templates, selectedTemplateId]
  );

  const dirty = useMemo(() => snapshot(title, profile, inferred) !== saved, [title, profile, inferred, saved]);
  const titleError = title.trim().length > MAX_TITLE ? `Tên CV tối đa ${MAX_TITLE} ký tự` : null;
  const index = CV_SECTIONS.findIndex((s) => s.key === section);
  const prev = index > 0 ? CV_SECTIONS[index - 1] : null;
  const next = index < CV_SECTIONS.length - 1 ? CV_SECTIONS[index + 1] : null;
  const displayTitle = title.trim() || (isNew ? "CV mới" : "CV chưa đặt tên");

  // Xem trước HTML tự động cho mẫu CONFIG (debounce 600ms, huỷ request cũ)
  useEffect(() => {
    if (!loaded || loadError || !templatesLoaded || !selectedTemplate || selectedTemplate.type !== "CONFIG") {
      return;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setPreviewLoading(true);
      setPreviewError(null);
      cvsApi
        .previewHtml(
          {
            templateId: selectedTemplate.id,
            title: displayTitle,
            profile: cleanProfile(profile),
          },
          controller.signal
        )
        .then((html) => {
          if (!controller.signal.aborted) setPreviewHtml(html);
        })
        .catch((e: unknown) => {
          if (controller.signal.aborted) return;
          setPreviewError(e instanceof Error ? e.message : "Không tải được bản xem trước.");
        })
        .finally(() => {
          if (!controller.signal.aborted) setPreviewLoading(false);
        });
    }, 600);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [loaded, loadError, templatesLoaded, selectedTemplate, displayTitle, profile]);

  async function onSelectTemplate(nextId: number) {
    if (nextId === selectedTemplateId || switchingTemplate) return;
    const prevId = selectedTemplateId;
    setSelectedTemplateId(nextId);
    setDocxPreviewUrl(null);
    setPreviewError(null);

    if (cvId != null) {
      setSwitchingTemplate(true);
      try {
        await cvsApi.setTemplate(cvId, nextId);
        toast("Đã đổi mẫu CV.");
      } catch (e) {
        setSelectedTemplateId(prevId);
        toast(e instanceof Error ? e.message : "Không đổi được mẫu CV");
      } finally {
        setSwitchingTemplate(false);
      }
    }
  }

  async function onPreviewDocx() {
    if (selectedTemplateId == null) return;
    setDocxPreviewLoading(true);
    setPreviewError(null);
    try {
      const link = await cvsApi.previewDocx({
        templateId: selectedTemplateId,
        title: displayTitle,
        profile: cleanProfile(profile),
      });
      setDocxPreviewUrl(link.url);
    } catch (e) {
      setPreviewError(e instanceof Error ? e.message : "Không tạo được bản xem trước PDF.");
    } finally {
      setDocxPreviewLoading(false);
    }
  }

  async function onExportPdf() {
    if (cvId == null) {
      toast("Vui lòng bấm “Lưu CV” trước khi xuất PDF.");
      return;
    }
    if (dirty) {
      toast("Đang tạo PDF theo dữ liệu đã lưu gần nhất (bạn có thay đổi chưa lưu).");
    }
    setPdfBusy(true);
    try {
      const link = await cvsApi.generatePdf(cvId);
      const win = window.open(link.url, "_blank", "noopener,noreferrer");
      if (!win) {
        toast("Trình duyệt đã chặn mở tab mới. Vui lòng cho phép popup để xem PDF.");
      }
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không tạo được file PDF");
    } finally {
      setPdfBusy(false);
    }
  }

  async function onSave() {
    if (titleError) {
      toast(titleError);
      return;
    }
    setSaving(true);
    try {
      let id = cvId;
      const wantedTitle = title.trim();
      if (id == null) {
        id = (await cvsApi.createBlank(wantedTitle || undefined, selectedTemplateId)).id;
        setCvId(id);
      } else if (wantedTitle && JSON.parse(saved)[0] !== wantedTitle) {
        await cvsApi.rename(id, wantedTitle);
      }
      const form = await cvsApi.confirm({
        profile: cleanProfile(profile),
        fields: inferred ? [{ field: INFERRED_FIELD, values: cleanLines(inferred) }] : undefined,
      }, id);
      applyForm({ ...form, title: wantedTitle || form.title });
      if (form.pdfError) {
        toast(`Đã lưu nội dung CV, nhưng chưa sinh được PDF: ${form.pdfError}`);
        return;
      }
      toast("Đã lưu CV");
      navigate("/candidate/cvs");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Lưu CV thất bại");
    } finally {
      setSaving(false);
    }
  }

  const isDocxTemplate = selectedTemplate?.type === "DOCX";
  const isHiddenBoundTemplate =
    templatesLoaded && selectedTemplateId != null && selectedTemplate == null;

  return (
    <>
      <SiteHeader active="cv" mode="candidate" />
      <main className="cvu">
        <div className="cvu-wrap cve-wrap">
          <div className="cvu-between">
            <div className="cvu-stack" style={{ gap: 8 }}>
              <nav className="cvu-tiny cvu-muted" aria-label="Breadcrumb">
                <Link to="/candidate/cvs">CV của tôi</Link> / <span>{displayTitle}</span>
              </nav>
              <div className="cve-title-row">
                <input
                  className="cve-title"
                  aria-label="Tên CV"
                  value={title}
                  placeholder={isNew ? "Đặt tên CV, vd Backend Java – 2026" : "Tên CV"}
                  maxLength={MAX_TITLE + 10}
                  onChange={(e) => setTitle(e.target.value)}
                />
                {isMain ? <span className="cvu-badge b-brand">CV chính</span> : null}
                {fileName ? (
                  <span className="cvu-badge">Từ file {fileName}</span>
                ) : (
                  <span className="cvu-badge">Tạo từ form</span>
                )}
              </div>
              {titleError ? (
                <span className="cvu-help" style={{ color: "var(--danger-c)" }}>
                  {titleError}
                </span>
              ) : null}
            </div>
            <div className="cve-head-actions">
              <span className="cvu-tiny cvu-muted" aria-live="polite">
                {dirty ? "Có thay đổi chưa lưu" : cvId ? "Đã lưu" : "Chưa lưu"} · Tự lưu nháp{" "}
                <Soon />
              </span>
              {fileName && cvId ? (
                <Link to={`/candidate/cv?cvId=${cvId}`} className="cvu-btn cvu-btn-g">
                  Tải file khác
                </Link>
              ) : null}
              <button
                type="button"
                className="cvu-btn cvu-btn-g"
                disabled={pdfBusy || !loaded || !!loadError}
                onClick={() => void onExportPdf()}
              >
                {pdfBusy ? "Đang xuất PDF…" : "Xem trước PDF"}
              </button>
              <button
                type="button"
                className="cvu-btn cvu-btn-p"
                onClick={() => void onSave()}
                disabled={saving || !loaded || !!loadError || (!dirty && cvId != null)}
              >
                {saving ? "Đang lưu…" : "Lưu CV"}
              </button>
            </div>
          </div>

          {!loaded ? (
            <p className="cvu-muted">Đang tải CV…</p>
          ) : loadError ? (
            <div className="cvu-card cvu-stack">
              <p>{loadError}</p>
              <Link to="/candidate/cvs" className="cvu-btn cvu-btn-g" style={{ alignSelf: "flex-start" }}>
                Về danh sách CV
              </Link>
            </div>
          ) : (
            <div className="cve-layout">
              <nav aria-label="Mục CV" className="cvu-card cve-nav">
                {CV_SECTIONS.map((s) => {
                  const active = s.key === section;
                  const filled = sectionFilled(profile, s.key);
                  return (
                    <button
                      key={s.key}
                      type="button"
                      className={active ? "cve-nav-item is-active" : "cve-nav-item"}
                      aria-current={active ? "step" : undefined}
                      onClick={() => setSection(s.key)}
                    >
                      <span>{s.label}</span>
                      <span className={filled ? "cvu-tiny cvu-muted" : "cvu-tiny cve-empty"}>
                        {active ? "Đang sửa" : filled ? "Đủ" : "Trống"}
                      </span>
                    </button>
                  );
                })}
                <div className="cve-nav-foot">
                  <label className="cvx-check cvu-tiny">
                    <input type="checkbox" disabled />
                    Đang tìm việc <Soon />
                  </label>
                  <p className="cvu-help">Cho phép nhà tuyển dụng tìm thấy CV này.</p>
                </div>
              </nav>

              <form
                className="cvu-stack cve-form"
                style={{ gap: 16 }}
                onSubmit={(e) => {
                  e.preventDefault();
                  void onSave();
                }}
              >
                <CvProfileEditor
                  section={section}
                  profile={profile}
                  onChange={setProfile}
                  inferred={inferred}
                  onInferredChange={setInferred}
                />
                <div className="cvu-between">
                  {prev ? (
                    <button type="button" className="cvu-btn cvu-btn-g" onClick={() => setSection(prev.key)}>
                      ← {prev.label}
                    </button>
                  ) : (
                    <span />
                  )}
                  {next ? (
                    <button type="button" className="cvu-btn cvu-btn-p" onClick={() => setSection(next.key)}>
                      Tiếp: {next.label} →
                    </button>
                  ) : (
                    <button type="submit" className="cvu-btn cvu-btn-p" disabled={saving}>
                      {saving ? "Đang lưu…" : "Lưu CV"}
                    </button>
                  )}
                </div>
              </form>

              <aside className="cvu-stack cve-aside" style={{ gap: 14 }}>
                <section className="cvu-card cvu-stack" style={{ gap: 10 }}>
                  <div className="cvu-between">
                    <h4>Mẫu CV</h4>
                    {switchingTemplate ? <span className="cvu-tiny cvu-muted">Đang đổi…</span> : null}
                  </div>
                  {!templatesLoaded ? (
                    <p className="cvu-tiny cvu-muted">Đang tải danh sách mẫu…</p>
                  ) : templates.length === 0 ? (
                    <p className="cvu-help">Chưa có mẫu CV khả dụng.</p>
                  ) : (
                    <div className="cve-templates">
                      {templates.map((t) => {
                        const active = t.id === selectedTemplateId;
                        return (
                          <button
                            key={t.id}
                            type="button"
                            disabled={switchingTemplate}
                            aria-pressed={active}
                            className={active ? "cve-tpl is-on" : "cve-tpl"}
                            onClick={() => void onSelectTemplate(t.id)}
                          >
                            <span>
                              <CvTemplateThumb
                                name={t.name}
                                type={t.type}
                                config={t.config}
                                thumbnailUrl={t.thumbnailUrl}
                                height={64}
                              />
                            </span>
                            <span className="cvu-tiny" style={{ fontWeight: 600 }}>
                              {t.name}
                            </span>
                            <span className="cvu-tiny cvu-muted">
                              {t.type === "CONFIG" ? "Cấu hình" : "Word"}
                              {t.isDefault ? " · Mặc định" : ""}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                  {isHiddenBoundTemplate ? (
                    <p className="cvu-note cvu-note-warn cvu-tiny">
                      CV này đang dùng một mẫu đã ẩn (#{selectedTemplateId}). Bạn vẫn có thể giữ
                      nguyên hoặc chọn một mẫu đang hiện ở trên.
                    </p>
                  ) : null}
                  <p className="cvu-help">Mẫu chỉ ảnh hưởng file PDF xuất ra, không ảnh hưởng matching.</p>
                </section>

                <section className="cvu-card cve-preview-card cvu-stack" style={{ gap: 10 }}>
                  <div className="cvu-between">
                    <span className="cvu-tiny cvu-muted" style={{ fontWeight: 600 }}>
                      Xem trước trực tiếp
                    </span>
                    {isDocxTemplate ? (
                      <button
                        type="button"
                        className="cvu-btn cvu-btn-g cvu-btn-sm"
                        disabled={docxPreviewLoading || selectedTemplateId == null}
                        onClick={() => void onPreviewDocx()}
                      >
                        {docxPreviewLoading ? "Đang tạo…" : "Cập nhật xem trước"}
                      </button>
                    ) : previewLoading ? (
                      <span className="cvu-tiny cvu-muted">Đang cập nhật…</span>
                    ) : null}
                  </div>

                  {previewError ? (
                    <p className="cvu-note cvu-note-warn cvu-tiny">{previewError}</p>
                  ) : null}

                  {selectedTemplateId == null ? (
                    <p className="cvu-help">Chọn một mẫu CV để xem trước.</p>
                  ) : isHiddenBoundTemplate ? (
                    <div className="cve-preview">
                      <p className="cvu-muted">
                        Mẫu đang dùng (#{selectedTemplateId}) hiện đang ẩn. Bạn vẫn có thể bấm{" "}
                        <strong>“Xem trước PDF”</strong> ở thanh trên hoặc chọn mẫu khác để xem trước trực tiếp.
                      </p>
                    </div>
                  ) : isDocxTemplate ? (
                    docxPreviewUrl ? (
                      <div className="cvu-stack" style={{ gap: 8 }}>
                        <iframe
                          title="Xem trước PDF mẫu Word"
                          src={docxPreviewUrl}
                          className="cve-preview-iframe"
                        />
                        <a
                          href={docxPreviewUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="cvu-btn cvu-btn-link"
                          style={{ minHeight: "auto" }}
                        >
                          Mở bản xem trước ở tab mới
                        </a>
                      </div>
                    ) : (
                      <div className="cve-preview">
                        <p className="cvu-muted">
                          Mẫu Word cần chuyển đổi sang PDF (1–3 giây). Bấm{" "}
                          <strong>“Cập nhật xem trước”</strong> để xem bản trình bày hiện tại.
                        </p>
                      </div>
                    )
                  ) : (
                    <iframe
                      title="Xem trước CV"
                      sandbox=""
                      srcDoc={previewHtml}
                      className="cve-preview-iframe"
                    />
                  )}
                </section>
              </aside>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
