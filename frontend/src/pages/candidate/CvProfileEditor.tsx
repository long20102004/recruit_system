import { useState, type KeyboardEvent, type ReactNode } from "react";
import type { CandidateProfileDto } from "../../api/client";
import { CURRENT_JOB, emptyProfile, type CvSection } from "./cvProfile";

/**
 * Form sửa hồ sơ theo cấu trúc CandidateProfile (response của POST /api/cvs, giống /analyze-pdf).
 * Component thuần điều khiển: nhận profile, trả profile mới qua onChange.
 */

type Profile = CandidateProfileDto;
type Education = NonNullable<Profile["education"]>[number];
type Experience = NonNullable<Profile["experience"]>[number];
type Project = NonNullable<Profile["personal_projects"]>[number];
type Language = NonNullable<Profile["languages"]>[number];

const isCurrent = (v: string | null | undefined) => (v ?? "").trim().toLowerCase() === CURRENT_JOB.toLowerCase();

function toInt(v: string): number | null {
  const n = parseInt(v, 10);
  return Number.isFinite(n) ? n : null;
}

function Text({
  id, label, value, onChange, type = "text", span2 = false, placeholder, disabled = false,
}: {
  id: string; label: string; value: string | number | null | undefined;
  onChange: (v: string) => void; type?: string; span2?: boolean; placeholder?: string; disabled?: boolean;
}) {
  return (
    <div className={span2 ? "cvu-field cvu-span2" : "cvu-field"}>
      <label htmlFor={id}>{label}</label>
      <input id={id} className="cvu-input" type={type} value={value ?? ""} placeholder={placeholder}
        disabled={disabled} onChange={(e) => onChange(e.target.value)} />
    </div>
  );
}

/** Danh sách dòng (mô tả, chứng chỉ…): mỗi dòng một mục. */
function Lines({
  id, label, value, onChange, rows = 3, span2 = true,
}: {
  id: string; label: string; value: string[] | null | undefined;
  onChange: (v: string[]) => void; rows?: number; span2?: boolean;
}) {
  return (
    <div className={span2 ? "cvu-field cvu-span2" : "cvu-field"}>
      <label htmlFor={id}>{label}</label>
      <textarea id={id} className="cvu-input" rows={rows} value={(value ?? []).join("\n")}
        onChange={(e) => onChange(e.target.value.split("\n"))} />
      <span className="cvu-help">Mỗi dòng một mục.</span>
    </div>
  );
}

export function Tags({
  items, onChange, addLabel, inferred = false,
}: {
  items: string[]; onChange: (next: string[]) => void; addLabel: string; inferred?: boolean;
}) {
  const [draft, setDraft] = useState("");
  function add() {
    const next = [...items];
    for (const item of draft.split(",").map((x) => x.trim()).filter(Boolean)) {
      if (!next.some((x) => x.toLowerCase() === item.toLowerCase())) next.push(item);
    }
    onChange(next);
    setDraft("");
  }
  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      add();
    }
  }
  return (
    <div className="cvu-tags">
      {items.map((t) => (
        <span key={t} className={inferred ? "cvu-tag" : "cvu-tag cvu-tag-on"}>
          {t}
          <button type="button" aria-label={`Xoá ${t}`} onClick={() => onChange(items.filter((x) => x !== t))}>×</button>
        </span>
      ))}
      <span className="cvu-tag-add">
        <input className="cvu-input" value={draft} placeholder={addLabel} aria-label={addLabel}
          onChange={(e) => setDraft(e.target.value)} onKeyDown={onKey} />
        <button type="button" className="cvu-btn cvu-btn-g cvu-btn-sm" onClick={add} disabled={!draft.trim()}>
          Thêm
        </button>
      </span>
    </div>
  );
}

/** Khung một nhóm có nhiều mục (học vấn, kinh nghiệm…), mỗi mục có nút xoá. */
function Repeat<T>({
  title, items, empty, render, onChange, blank,
}: {
  title: string; items: T[]; empty: string; blank: () => T;
  render: (item: T, update: (patch: Partial<T>) => void, index: number) => ReactNode;
  onChange: (next: T[]) => void;
}) {
  return (
    <section className="cvu-card cvu-stack">
      <div className="cvu-between">
        <h3>{title}{items.length ? <span className="cvu-tiny cvu-muted"> · {items.length}</span> : null}</h3>
        <button type="button" className="cvu-btn cvu-btn-link" onClick={() => onChange([...items, blank()])}>
          + Thêm
        </button>
      </div>
      {items.length === 0 ? <p className="cvu-help">{empty}</p> : items.map((item, i) => (
        <div key={i} className="cvx-entry">
          <div className="cvu-grid">
            {render(item, (patch) => onChange(items.map((x, j) => (j === i ? { ...x, ...patch } : x))), i)}
          </div>
          <div className="cvx-entry-actions">
            {i > 0 ? (
              <button type="button" className="cvu-btn cvu-btn-link"
                aria-label={`Đưa mục ${i + 1} lên trên`}
                onClick={() => {
                  const next = [...items];
                  [next[i - 1], next[i]] = [next[i], next[i - 1]];
                  onChange(next);
                }}>
                ↑ Lên trên
              </button>
            ) : null}
            <button type="button" className="cvu-btn cvu-btn-link cvx-remove"
              onClick={() => onChange(items.filter((_, j) => j !== i))}>
              Xoá mục này
            </button>
          </div>
        </div>
      ))}
    </section>
  );
}

export function CvProfileEditor({
  profile, onChange, inferred, onInferredChange, section,
}: {
  profile: Profile;
  onChange: (next: Profile) => void;
  /** Chỉ hiện một mục (C04); không truyền = hiện tất cả (C03). */
  section?: CvSection;
  /** "Kỹ năng suy ra" từ đồ thị kỹ năng (không thuộc CandidateProfile); null = không cấu hình field này. */
  inferred: string[] | null;
  onInferredChange: (next: string[]) => void;
}) {
  const info = profile.personal_info ?? emptyProfile().personal_info!;
  const set = (patch: Partial<Profile>) => onChange({ ...profile, ...patch });
  const setInfo = (patch: Partial<typeof info>) => set({ personal_info: { ...info, ...patch } });
  const show = (key: CvSection) => section == null || section === key;

  return (
    <>
      {show("info") ? <section className="cvu-card cvu-stack">
        <h3>Thông tin cá nhân</h3>
        <div className="cvu-grid">
          <Text id="cv-name" label="Họ và tên" value={info.full_name} onChange={(v) => setInfo({ full_name: v })} />
          <Text id="cv-email" label="Email" type="email" value={info.email} onChange={(v) => setInfo({ email: v })} />
          <Text id="cv-phone" label="Số điện thoại" value={info.phone} onChange={(v) => setInfo({ phone: v })} />
          <Text id="cv-github" label="GitHub" value={info.github_url} onChange={(v) => setInfo({ github_url: v })} />
          <div className="cvu-field cvu-span2">
            <label htmlFor="cv-objective">Giới thiệu</label>
            <textarea id="cv-objective" className="cvu-input" rows={4} value={profile.objective ?? ""}
              onChange={(e) => set({ objective: e.target.value })} />
          </div>
        </div>
      </section> : null}

      {show("skills") ? <section className="cvu-card cvu-stack">
        <h3>Kỹ năng</h3>
        <Tags items={profile.skills ?? []} onChange={(skills) => set({ skills })} addLabel="Thêm kỹ năng" />
        {inferred ? (
          <div className="cvu-stack cvu-inferred">
            <h4>Kỹ năng suy ra</h4>
            <p className="cvu-help">Không ghi trên CV, hệ thống suy ra từ đồ thị kỹ năng. Xoá nếu không đúng với bạn.</p>
            <Tags items={inferred} onChange={onInferredChange} addLabel="Thêm kỹ năng suy ra" inferred />
          </div>
        ) : null}
      </section> : null}

      {show("education") ? <Repeat<Education>
        title="Học vấn" items={profile.education ?? []} onChange={(education) => set({ education })}
        empty="AI không tìm thấy học vấn trong CV. Bấm “+ Thêm” nếu cần bổ sung."
        blank={() => ({ school: null, major: null, location: null, start_year: null, end_year: null, gpa: null })}
        render={(e, up, i) => (
          <>
            <Text id={`edu-school-${i}`} label="Trường" value={e.school} onChange={(v) => up({ school: v })} span2 />
            <Text id={`edu-major-${i}`} label="Chuyên ngành" value={e.major} onChange={(v) => up({ major: v })} />
            <Text id={`edu-gpa-${i}`} label="GPA" value={e.gpa} onChange={(v) => up({ gpa: v })} />
            <Text id={`edu-loc-${i}`} label="Địa điểm" placeholder="TP.HCM / Hà Nội" value={e.location}
              onChange={(v) => up({ location: v })} span2 />
            <Text id={`edu-start-${i}`} label="Từ" type="number" value={e.start_year}
              onChange={(v) => up({ start_year: toInt(v) })} />
            <Text id={`edu-end-${i}`} label="Đến" type="number" value={e.end_year}
              onChange={(v) => up({ end_year: toInt(v) })} />
          </>
        )}
      /> : null}

      {show("experience") ? <Repeat<Experience>
        title="Kinh nghiệm làm việc" items={profile.experience ?? []} onChange={(experience) => set({ experience })}
        empty="AI không tìm thấy kinh nghiệm làm việc trong CV."
        blank={() => ({ company: null, job_title: null, location: null, start_date: null, end_date: null, description: [] })}
        render={(e, up, i) => (
          <>
            <Text id={`exp-title-${i}`} label="Chức danh" value={e.job_title} onChange={(v) => up({ job_title: v })} />
            <Text id={`exp-company-${i}`} label="Công ty" value={e.company} onChange={(v) => up({ company: v })} />
            <Text id={`exp-loc-${i}`} label="Địa điểm" placeholder="TP.HCM / Hà Nội" value={e.location}
              onChange={(v) => up({ location: v })} span2 />
            <Text id={`exp-start-${i}`} label="Từ tháng" placeholder="MM/YYYY" value={e.start_date}
              onChange={(v) => up({ start_date: v })} />
            <Text id={`exp-end-${i}`} label="Đến tháng" placeholder="MM/YYYY" value={isCurrent(e.end_date) ? "" : e.end_date}
              disabled={isCurrent(e.end_date)} onChange={(v) => up({ end_date: v })} />
            <label className="cvx-check cvu-span2">
              <input type="checkbox" checked={isCurrent(e.end_date)}
                onChange={(ev) => up({ end_date: ev.target.checked ? CURRENT_JOB : null })} />
              Tôi đang làm ở đây
            </label>
            <Lines id={`exp-desc-${i}`} label="Mô tả công việc, thành tựu" value={e.description}
              onChange={(v) => up({ description: v })} />
          </>
        )}
      /> : null}

      {show("projects") ? <Repeat<Project>
        title="Dự án cá nhân" items={profile.personal_projects ?? []}
        onChange={(personal_projects) => set({ personal_projects })}
        empty="AI không tìm thấy dự án trong CV."
        blank={() => ({ name: null, role: null, team_size: null, start_date: null, end_date: null,
          github_url: null, description: [], tech_stack: [] })}
        render={(x, up, i) => (
          <>
            <Text id={`prj-name-${i}`} label="Tên dự án" value={x.name} onChange={(v) => up({ name: v })} span2 />
            <Text id={`prj-role-${i}`} label="Vai trò" value={x.role} onChange={(v) => up({ role: v })} />
            <Text id={`prj-team-${i}`} label="Số người" type="number" value={x.team_size}
              onChange={(v) => up({ team_size: toInt(v) })} />
            <Text id={`prj-start-${i}`} label="Bắt đầu" value={x.start_date} onChange={(v) => up({ start_date: v })} />
            <Text id={`prj-end-${i}`} label="Kết thúc" value={x.end_date} onChange={(v) => up({ end_date: v })} />
            <Text id={`prj-gh-${i}`} label="GitHub" value={x.github_url} onChange={(v) => up({ github_url: v })} span2 />
            <div className="cvu-field cvu-span2">
              <label>Công nghệ sử dụng</label>
              <Tags items={x.tech_stack ?? []} onChange={(v) => up({ tech_stack: v })} addLabel="Thêm công nghệ" />
            </div>
            <Lines id={`prj-desc-${i}`} label="Mô tả" value={x.description} onChange={(v) => up({ description: v })} />
          </>
        )}
      /> : null}

      {section == null ? (
        <section className="cvu-card cvu-stack">
          <h3>Chứng chỉ, giải thưởng</h3>
          <div className="cvu-grid">
            <Lines id="cv-certs" label="Chứng chỉ" value={profile.certificates}
              onChange={(certificates) => set({ certificates })} span2={false} />
            <Lines id="cv-honours" label="Giải thưởng" value={profile.honours}
              onChange={(honours) => set({ honours })} span2={false} />
          </div>
        </section>
      ) : section === "certificates" || section === "honours" ? (
        <section className="cvu-card cvu-stack">
          <h3>{section === "certificates" ? "Chứng chỉ" : "Giải thưởng & hoạt động"}</h3>
          {section === "certificates" ? (
            <Lines id="cv-certs" label="Chứng chỉ (tên, đơn vị cấp, năm)" value={profile.certificates} rows={5}
              onChange={(certificates) => set({ certificates })} />
          ) : (
            <Lines id="cv-honours" label="Giải thưởng, hoạt động" value={profile.honours} rows={5}
              onChange={(honours) => set({ honours })} />
          )}
        </section>
      ) : null}

      {show("languages") ? <Repeat<Language>
        title="Ngoại ngữ" items={profile.languages ?? []} onChange={(languages) => set({ languages })}
        empty="AI không tìm thấy ngoại ngữ trong CV."
        blank={() => ({ language: null, note: null })}
        render={(l, up, i) => (
          <>
            <Text id={`lang-${i}`} label="Ngôn ngữ" value={l.language} onChange={(v) => up({ language: v })} />
            <Text id={`lang-note-${i}`} label="Ghi chú (chứng chỉ, mức độ)" value={l.note}
              onChange={(v) => up({ note: v })} />
          </>
        )}
      /> : null}
    </>
  );
}
