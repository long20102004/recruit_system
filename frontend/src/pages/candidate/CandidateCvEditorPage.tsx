import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { SiteHeader } from "../../components/common";
import { cvsApi, type CandidateProfileDto, type CvFormDto } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { CvProfileEditor } from "./CvProfileEditor";
import { CV_SECTIONS, CURRENT_JOB, cleanProfile, normalizeProfile, sectionFilled, type CvSection } from "./cvProfile";

/**
 * C04 · Tạo / sửa CV (Figma: CvEditor). Sửa nội dung theo từng mục, không cần tải file.
 * ?cvId=X: sửa CV X; ?new=1: tạo CV từ đầu (chỉ tạo CV khi bấm Lưu).
 * Mẫu CV, xuất PDF, "Đang tìm việc", tự lưu nháp chưa có backend: hiện "Sắp có".
 */

/** Field "Kỹ năng suy ra" không thuộc CandidateProfile nên lưu qua fields (giống C03). */
const INFERRED_FIELD = "Kỹ năng suy ra";
const MAX_TITLE = 120;
const TEMPLATES = [
  { name: "Cổ điển", bg: "#efe8dc" },
  { name: "Hiện đại", bg: "#e7ecf8" },
  { name: "Tối giản", bg: "#f4efe7" },
];

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
    setSaved(snapshot(t, p, i));
  }

  useEffect(() => {
    let alive = true;
    setLoaded(false);
    setLoadError(null);
    setSection("info");
    if (isNew) {
      const p = normalizeProfile(null);
      setCvId(null);
      setTitle("");
      setIsMain(false);
      setFileName(null);
      setProfile(p);
      setInferred(null);
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
  }, [paramId, isNew, navigate]);

  const dirty = useMemo(() => snapshot(title, profile, inferred) !== saved, [title, profile, inferred, saved]);
  const titleError = title.trim().length > MAX_TITLE ? `Tên CV tối đa ${MAX_TITLE} ký tự` : null;
  const index = CV_SECTIONS.findIndex((s) => s.key === section);
  const prev = index > 0 ? CV_SECTIONS[index - 1] : null;
  const next = index < CV_SECTIONS.length - 1 ? CV_SECTIONS[index + 1] : null;
  const displayTitle = title.trim() || (isNew ? "CV mới" : "CV chưa đặt tên");

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
        id = (await cvsApi.createBlank(wantedTitle || undefined)).id;
        setCvId(id);
      } else if (wantedTitle && JSON.parse(saved)[0] !== wantedTitle) {
        await cvsApi.rename(id, wantedTitle);
      }
      const form = await cvsApi.confirm({
        profile: cleanProfile(profile),
        fields: inferred ? [{ field: INFERRED_FIELD, values: cleanLines(inferred) }] : undefined,
      }, id);
      applyForm({ ...form, title: wantedTitle || form.title });
      toast("Đã lưu CV");
      navigate("/candidate/cvs");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Lưu CV thất bại");
    } finally {
      setSaving(false);
    }
  }

  const info = profile.personal_info;
  const experience = profile.experience ?? [];
  const skills = cleanLines(profile.skills);

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
                <input className="cve-title" aria-label="Tên CV" value={title} placeholder={isNew ? "Đặt tên CV, vd Backend Java – 2026" : "Tên CV"}
                  maxLength={MAX_TITLE + 10} onChange={(e) => setTitle(e.target.value)} />
                {isMain ? <span className="cvu-badge b-brand">CV chính</span> : null}
                {fileName ? <span className="cvu-badge">Từ file {fileName}</span> : <span className="cvu-badge">Tạo từ form</span>}
              </div>
              {titleError ? <span className="cvu-help" style={{ color: "var(--danger-c)" }}>{titleError}</span> : null}
            </div>
            <div className="cve-head-actions">
              <span className="cvu-tiny cvu-muted" aria-live="polite">
                {dirty ? "Có thay đổi chưa lưu" : cvId ? "Đã lưu" : "Chưa lưu"} · Tự lưu nháp <Soon />
              </span>
              {fileName && cvId ? (
                <Link to={`/candidate/cv?cvId=${cvId}`} className="cvu-btn cvu-btn-g">Tải file khác</Link>
              ) : null}
              <button type="button" className="cvu-btn cvu-btn-g" disabled title="Sắp có">
                Xem trước PDF <Soon />
              </button>
              <button type="button" className="cvu-btn cvu-btn-p" onClick={() => void onSave()}
                disabled={saving || !loaded || !!loadError || (!dirty && cvId != null)}>
                {saving ? "Đang lưu…" : "Lưu CV"}
              </button>
            </div>
          </div>

          {!loaded ? (
            <p className="cvu-muted">Đang tải CV…</p>
          ) : loadError ? (
            <div className="cvu-card cvu-stack">
              <p>{loadError}</p>
              <Link to="/candidate/cvs" className="cvu-btn cvu-btn-g" style={{ alignSelf: "flex-start" }}>Về danh sách CV</Link>
            </div>
          ) : (
            <div className="cve-layout">
              <nav aria-label="Mục CV" className="cvu-card cve-nav">
                {CV_SECTIONS.map((s) => {
                  const active = s.key === section;
                  const filled = sectionFilled(profile, s.key);
                  return (
                    <button key={s.key} type="button" className={active ? "cve-nav-item is-active" : "cve-nav-item"}
                      aria-current={active ? "step" : undefined} onClick={() => setSection(s.key)}>
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

              <form className="cvu-stack cve-form" style={{ gap: 16 }}
                onSubmit={(e) => { e.preventDefault(); void onSave(); }}>
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
                  ) : <span />}
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
                  <div className="cvu-between"><h4>Mẫu CV</h4><Soon /></div>
                  <div className="cve-templates">
                    {TEMPLATES.map((t, i) => (
                      <button key={t.name} type="button" disabled className={i === 0 ? "cve-tpl is-on" : "cve-tpl"}
                        aria-label={`Mẫu ${t.name} (sắp có)`}>
                        <span style={{ background: t.bg }} />
                        <span className="cvu-tiny">{t.name}</span>
                      </button>
                    ))}
                  </div>
                  <p className="cvu-help">Mẫu chỉ ảnh hưởng file PDF xuất ra, không ảnh hưởng matching.</p>
                </section>

                <section className="cvu-card cve-preview-card">
                  <p className="cvu-tiny cvu-muted" style={{ marginBottom: 8 }}>Xem trước</p>
                  <div className="cve-preview">
                    <p className="cve-preview-name">{info?.full_name?.trim() || "Họ và tên"}</p>
                    {experience[0]?.job_title ? <p className="cve-preview-role">{experience[0].job_title}</p> : null}
                    {[info?.email, info?.phone, info?.github_url].filter((x) => x && x.trim()).length ? (
                      <p className="cvu-muted">{[info?.email, info?.phone, info?.github_url].filter((x) => x && x.trim()).join(" · ")}</p>
                    ) : null}
                    <div className="cve-preview-sep" />
                    {experience.length ? (
                      <>
                        <p className="cve-preview-h">KINH NGHIỆM</p>
                        {experience.map((e, i) => (
                          <div key={i}>
                            <p><strong>{e.job_title || "Chức danh"}</strong>{e.company ? ` · ${e.company}` : ""}</p>
                            <p className="cvu-muted">
                              {[e.start_date, e.end_date === CURRENT_JOB ? "nay" : e.end_date].filter(Boolean).join(" – ")}
                            </p>
                          </div>
                        ))}
                      </>
                    ) : null}
                    {(profile.education ?? []).length ? (
                      <>
                        <p className="cve-preview-h">HỌC VẤN</p>
                        {(profile.education ?? []).map((e, i) => (
                          <p key={i}><strong>{e.school || "Trường"}</strong>{e.major ? ` · ${e.major}` : ""}</p>
                        ))}
                      </>
                    ) : null}
                    {skills.length ? (
                      <>
                        <p className="cve-preview-h">KỸ NĂNG</p>
                        <p>{skills.join(" · ")}</p>
                      </>
                    ) : null}
                    {!experience.length && !skills.length && !(profile.education ?? []).length ? (
                      <p className="cvu-muted">Điền các mục bên trái để xem trước CV.</p>
                    ) : null}
                  </div>
                </section>
              </aside>
            </div>
          )}
        </div>
      </main>
    </>
  );
}
