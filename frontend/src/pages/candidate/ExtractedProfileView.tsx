import type { ReactNode } from "react";
import type { CandidateProfileDto } from "../../api/client";

/** Kết quả AI trích xuất (POST /api/cvs), hiển thị đủ các trường của CandidateProfile; chỉ để xem. */

function text(value: string | number | null | undefined): string {
  return value == null ? "" : String(value).trim();
}

function list<T>(items: T[] | null | undefined): T[] {
  return (items ?? []).filter((x) => x != null);
}

function range(start: string | number | null | undefined, end: string | number | null | undefined) {
  const a = text(start);
  const b = text(end);
  if (!a && !b) return "";
  return `${a || "?"} – ${b || "nay"}`;
}

function Empty() {
  return <p className="cvu-help">AI không tìm thấy trong CV.</p>;
}

function Section({ title, count, children }: { title: string; count?: number; children: ReactNode }) {
  return (
    <div className="cvu-stack cvx-section">
      <h4>
        {title}
        {count != null ? <span className="cvu-tiny cvu-muted"> · {count}</span> : null}
      </h4>
      {children}
    </div>
  );
}

function Pair({ label, value, href }: { label: string; value: string; href?: boolean }) {
  return (
    <div className="cvu-field">
      <span className="cvx-label">{label}</span>
      {!value ? (
        <span className="cvu-help">—</span>
      ) : href ? (
        <a href={value} target="_blank" rel="noreferrer">{value}</a>
      ) : (
        <span>{value}</span>
      )}
    </div>
  );
}

function Tags({ items }: { items: string[] }) {
  return items.length === 0 ? (
    <Empty />
  ) : (
    <div className="cvu-tags">
      {items.map((t, i) => (
        <span key={`${t}-${i}`} className="cvu-tag cvx-tag">{t}</span>
      ))}
    </div>
  );
}

function Bullets({ items }: { items: string[] | null | undefined }) {
  const lines = list(items).map((s) => s.trim()).filter(Boolean);
  return lines.length ? (
    <ul className="cvx-bullets">
      {lines.map((l, i) => <li key={i}>{l}</li>)}
    </ul>
  ) : null;
}

export function ExtractedProfileView({ profile }: { profile: CandidateProfileDto }) {
  const info = profile.personal_info;
  const education = list(profile.education);
  const experience = list(profile.experience);
  const projects = list(profile.personal_projects);
  const languages = list(profile.languages);

  return (
    <details className="cvu-card cvx" open>
      <summary className="cvu-between">
        <h3>Kết quả AI trích xuất</h3>
        <span className="cvu-badge b-brand">Chỉ xem</span>
      </summary>
      <p className="cvu-help">
        Dữ liệu AI đọc từ file vừa tải lên. Sửa ở form bên dưới rồi bấm “Lưu CV”.
      </p>

      <Section title="Thông tin cá nhân">
        <div className="cvu-grid">
          <Pair label="Họ tên" value={text(info?.full_name)} />
          <Pair label="Email" value={text(info?.email)} />
          <Pair label="Điện thoại" value={text(info?.phone)} />
          <Pair label="GitHub" value={text(info?.github_url)} href />
        </div>
      </Section>

      <Section title="Mục tiêu nghề nghiệp">
        {text(profile.objective) ? <p className="cvx-pre">{text(profile.objective)}</p> : <Empty />}
      </Section>

      <Section title="Học vấn" count={education.length}>
        {education.length === 0 ? <Empty /> : education.map((e, i) => (
          <div key={i} className="cvx-entry">
            <div className="cvu-between">
              <strong>{text(e.school) || "Không rõ trường"}</strong>
              <span className="cvu-tiny cvu-muted">{range(e.start_year, e.end_year)}</span>
            </div>
            <p className="cvu-small">
              {[text(e.major), text(e.gpa) ? `GPA ${text(e.gpa)}` : ""].filter(Boolean).join(" · ") || "—"}
            </p>
          </div>
        ))}
      </Section>

      <Section title="Kinh nghiệm" count={experience.length}>
        {experience.length === 0 ? <Empty /> : experience.map((e, i) => (
          <div key={i} className="cvx-entry">
            <div className="cvu-between">
              <strong>
                {text(e.job_title) || "Không rõ vị trí"}
                {text(e.company) ? ` · ${text(e.company)}` : ""}
              </strong>
              <span className="cvu-tiny cvu-muted">{range(e.start_date, e.end_date)}</span>
            </div>
            <Bullets items={e.description} />
          </div>
        ))}
      </Section>

      <Section title="Dự án cá nhân" count={projects.length}>
        {projects.length === 0 ? <Empty /> : projects.map((p, i) => (
          <div key={i} className="cvx-entry">
            <div className="cvu-between">
              <strong>{text(p.name) || "Dự án không tên"}</strong>
              <span className="cvu-tiny cvu-muted">{range(p.start_date, p.end_date)}</span>
            </div>
            <p className="cvu-small">
              {[text(p.role), p.team_size != null ? `Nhóm ${p.team_size} người` : ""].filter(Boolean).join(" · ")}
            </p>
            {text(p.github_url) ? (
              <a className="cvu-small" href={text(p.github_url)} target="_blank" rel="noreferrer">{text(p.github_url)}</a>
            ) : null}
            {list(p.tech_stack).length ? <Tags items={list(p.tech_stack)} /> : null}
            <Bullets items={p.description} />
          </div>
        ))}
      </Section>

      <Section title="Kỹ năng" count={list(profile.skills).length}>
        <Tags items={list(profile.skills)} />
      </Section>

      <Section title="Chứng chỉ" count={list(profile.certificates).length}>
        {list(profile.certificates).length ? <Bullets items={profile.certificates} /> : <Empty />}
      </Section>

      <Section title="Giải thưởng" count={list(profile.honours).length}>
        {list(profile.honours).length ? <Bullets items={profile.honours} /> : <Empty />}
      </Section>

      <Section title="Ngoại ngữ" count={languages.length}>
        {languages.length === 0 ? <Empty /> : (
          <ul className="cvx-bullets">
            {languages.map((l, i) => (
              <li key={i}>{text(l.language)}{text(l.note) ? ` — ${text(l.note)}` : ""}</li>
            ))}
          </ul>
        )}
      </Section>
    </details>
  );
}
