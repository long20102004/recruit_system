import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import { SiteHeader, UploadZone } from "../../components/common";
import { cvsApi, type CandidateProfileDto, type CvFormDto } from "../../api/client";
import { ExtractedProfileView } from "./ExtractedProfileView";
import { useToast } from "../../context/ToastContext";

type Values = Record<string, string[]>;

const PERSONAL_FIELDS = ["Họ tên", "Email", "Điện thoại"];
const SUMMARY_FIELD = "Tóm tắt";
const SKILL_FIELD = "Kỹ năng";
const INFERRED_FIELD = "Kỹ năng suy ra";
const GROUPED = new Set([...PERSONAL_FIELDS, SUMMARY_FIELD, SKILL_FIELD, INFERRED_FIELD]);

const ITEM_LABEL: Record<string, string> = {
  "Kinh nghiệm": "kinh nghiệm",
  "Học vấn": "học vấn",
  "Chứng chỉ": "chứng chỉ",
};

function cleanLines(lines: string[] | undefined): string[] {
  return (lines ?? [])
    .flatMap((line) => line.split(/\r?\n/))
    .map((line) => line.trim())
    .filter(Boolean);
}

function valuesFrom(form: CvFormDto): Values {
  return Object.fromEntries(form.fields.map((f) => [f.field, cleanLines(f.values)]));
}

function sameValues(a: Values, b: Values, fields: string[]) {
  return fields.every(
    (f) => JSON.stringify(cleanLines(a[f])) === JSON.stringify(cleanLines(b[f]))
  );
}

function UploadIcon() {
  return (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.6" aria-hidden="true">
      <path d="M12 16V4M7 9l5-5 5 5" />
      <path d="M4 16v4h16v-4" />
    </svg>
  );
}

function SkillTags({
  skills,
  onChange,
  addLabel,
  inferred = false,
}: {
  skills: string[];
  onChange: (next: string[]) => void;
  addLabel: string;
  inferred?: boolean;
}) {
  const [draft, setDraft] = useState("");

  function add() {
    const items = draft.split(",").map((s) => s.trim()).filter(Boolean);
    const next = [...skills];
    for (const item of items) {
      if (!next.some((s) => s.toLowerCase() === item.toLowerCase())) next.push(item);
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
      {skills.map((skill) => (
        <span key={skill} className={inferred ? "cvu-tag" : "cvu-tag cvu-tag-on"}>
          {skill}
          <button type="button" aria-label={`Xoá kỹ năng ${skill}`}
            onClick={() => onChange(skills.filter((s) => s !== skill))}>
            ×
          </button>
        </span>
      ))}
      <span className="cvu-tag-add">
        <input
          className="cvu-input"
          value={draft}
          placeholder={addLabel}
          aria-label={addLabel}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKey}
        />
        <button type="button" className="cvu-btn cvu-btn-g cvu-btn-sm" onClick={add}
          disabled={!draft.trim()}>
          Thêm
        </button>
      </span>
    </div>
  );
}

function ItemList({
  field,
  items,
  onChange,
}: {
  field: string;
  items: string[];
  onChange: (next: string[]) => void;
}) {
  const label = ITEM_LABEL[field] ?? field.toLowerCase();
  return (
    <section className="cvu-card cvu-stack">
      <div className="cvu-between">
        <h3>{field}</h3>
        <button type="button" className="cvu-btn cvu-btn-link"
          onClick={() => onChange([...items, ""])}>
          + Thêm
        </button>
      </div>
      {items.length === 0 ? (
        <p className="cvu-help">AI không tìm thấy mục {label} nào trong CV. Bấm “+ Thêm” nếu cần bổ sung.</p>
      ) : (
        items.map((item, index) => (
          <div key={index} className="cvu-item">
            <label className="cvu-sr" htmlFor={`${field}-${index}`}>
              {field} {index + 1}
            </label>
            <textarea
              id={`${field}-${index}`}
              className="cvu-input"
              rows={item.length > 120 ? 4 : 2}
              value={item}
              onChange={(e) =>
                onChange(items.map((v, i) => (i === index ? e.target.value : v)))
              }
            />
            <button type="button" className="cvu-icon-btn" aria-label={`Xoá ${label} ${index + 1}`}
              onClick={() => onChange(items.filter((_, i) => i !== index))}>
              ×
            </button>
          </div>
        ))
      )}
    </section>
  );
}

export function CandidateCvPage() {
  const { toast } = useToast();
  const [loaded, setLoaded] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileSize, setFileSize] = useState<number | null>(null);
  const [parsingStatus, setParsingStatus] = useState<string | null>(null);
  const [analyzed, setAnalyzed] = useState(false);
  const [fields, setFields] = useState<string[]>([]);
  const [values, setValues] = useState<Values>({});
  const [saved, setSaved] = useState<Values>({});
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  /** Profile AI trả về ở lần upload gần nhất trong phiên (POST /api/cvs). */
  const [extracted, setExtracted] = useState<CandidateProfileDto | null>(null);
  const previewRef = useRef<string | null>(null);

  function applyForm(form: CvFormDto) {
    const v = valuesFrom(form);
    setFields(form.fields.map((f) => f.field));
    setValues(v);
    setSaved(v);
    setFileName(form.fileName);
    setParsingStatus(form.parsingStatus);
    setAnalyzed(form.analyzed);
  }

  useEffect(() => {
    cvsApi
      .mine()
      .then(applyForm)
      .catch(() => undefined)
      .finally(() => setLoaded(true));
    return () => {
      if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    };
  }, []);

  function setPreview(file: File | null) {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = file ? URL.createObjectURL(file) : null;
    setPreviewUrl(previewRef.current);
  }

  async function onUpload(file: File) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      toast("Chỉ nhận file PDF");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast("File vượt quá 10 MB");
      return;
    }
    setUploadError(null);
    setUploading(true);
    setFileName(file.name);
    setFileSize(file.size);
    setPreview(file);
    setExtracted(null);
    try {
      const res = await cvsApi.upload(file);
      setExtracted(res.data ?? null);
      // Form chỉnh sửa vẫn theo dạng field đã lưu (GET /api/cvs)
      applyForm(await cvsApi.mine());
      setAnalyzed(false);
      toast("AI đã điền các mục hồ sơ. Hãy kiểm tra trước khi lưu.");
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Upload thất bại");
    } finally {
      setUploading(false);
    }
  }

  const dirty = useMemo(() => !sameValues(values, saved, fields), [values, saved, fields]);
  const hasProfile = fields.length > 0 && parsingStatus === "COMPLETED";
  const failed = parsingStatus === "FAILED" || uploadError != null;
  const isSaved = analyzed && !dirty;

  async function onSave() {
    setSaving(true);
    try {
      const form = await cvsApi.confirm(
        fields.map((field) => ({ field, values: cleanLines(values[field]) }))
      );
      applyForm(form);
      toast("Đã lưu hồ sơ CV");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Lưu thất bại");
    } finally {
      setSaving(false);
    }
  }

  function setField(field: string, lines: string[]) {
    setValues((cur) => ({ ...cur, [field]: lines }));
  }

  const stepDone = [
    !!fileName && !uploading,
    hasProfile && !uploading,
    isSaved && !uploading,
  ];
  const activeStep = stepDone.findIndex((d) => !d);
  const steps = ["Tải file PDF", "AI trích xuất", "Kiểm tra & lưu"];

  const personal = PERSONAL_FIELDS.filter((f) => fields.includes(f));
  const listFields = fields.filter((f) => !GROUPED.has(f));

  return (
    <>
      <SiteHeader active="cv" mode="candidate" />
      <main className="cvu">
        <div className="cvu-wrap">
          <h1>Tải CV lên và kiểm tra thông tin AI trích xuất</h1>

          <ol className="cvu-steps" aria-label="Các bước">
            {steps.map((label, i) => {
              const state = stepDone[i] ? "done" : i === activeStep ? "active" : "idle";
              return (
                <li key={label} className={`cvu-step is-${state}`}
                  aria-current={state === "active" ? "step" : undefined}>
                  <span className="cvu-step-n">{i + 1}</span>
                  {label}
                </li>
              );
            })}
          </ol>

          {!loaded ? (
            <p className="cvu-muted">Đang tải hồ sơ…</p>
          ) : (
            <>
              <section className="cvu-top">
                <UploadZone
                  className="cvu-drop"
                  onFile={onUpload}
                  disabled={uploading}
                  title={
                    <>
                      <UploadIcon />
                      <span>{fileName ? "Kéo thả file PDF khác vào đây" : "Kéo thả file PDF vào đây"}</span>
                    </>
                  }
                  hint="PDF, tối đa 10 MB"
                >
                  <span className="cvu-btn cvu-btn-g cvu-btn-sm" aria-hidden="true">
                    Chọn file
                  </span>
                  {fileName ? (
                    <p className="cvu-picked">
                      {uploading ? "Đang tải" : "Đã chọn"}: {fileName}
                      {fileSize != null ? ` · ${Math.max(1, Math.round(fileSize / 1024))} KB` : ""}
                    </p>
                  ) : null}
                </UploadZone>

                <div className="cvu-card cvu-status" aria-live="polite">
                  {uploading ? (
                    <>
                      <div className="cvu-between">
                        <h4>AI đang đọc CV…</h4>
                        <span className="cvu-badge b-brand">Đang xử lý</span>
                      </div>
                      <div className="cvu-meter is-busy"><span /></div>
                      <p className="cvu-small cvu-muted">
                        Thường mất 10–60 giây với CV 1–2 trang. Giữ trang này mở cho đến khi xong.
                      </p>
                    </>
                  ) : failed ? (
                    <>
                      <div className="cvu-between">
                        <h4>Không đọc được CV</h4>
                        <span className="cvu-badge b-danger">Lỗi</span>
                      </div>
                      <div className="cvu-note cvu-note-warn">
                        {uploadError ??
                          "File bị mã hoá hoặc là ảnh scan nên AI không đọc được chữ."}{" "}
                        Thử lại sau ít phút hoặc chọn file PDF khác.
                      </div>
                    </>
                  ) : hasProfile ? (
                    <>
                      <div className="cvu-between">
                        <h4>{isSaved ? "Hồ sơ đã lưu" : "AI đã trích xuất xong"}</h4>
                        <span className={`cvu-badge ${isSaved ? "b-ok" : "b-brand"}`}>
                          {isSaved ? "Đã lưu" : dirty ? "Có thay đổi chưa lưu" : "Chờ kiểm tra"}
                        </span>
                      </div>
                      <div className="cvu-meter"><span style={{ width: "100%" }} /></div>
                      <p className="cvu-small cvu-muted">
                        {isSaved
                          ? "Hồ sơ này đang được dùng để xếp hạng việc làm phù hợp."
                          : "Kiểm tra từng mục bên dưới rồi bấm “Lưu CV”."}
                      </p>
                      {isSaved ? (
                        <Link to="/candidate/matching" className="cvu-btn cvu-btn-link">
                          Xem việc phù hợp →
                        </Link>
                      ) : null}
                    </>
                  ) : (
                    <>
                      <h4>Chưa có CV</h4>
                      <p className="cvu-small cvu-muted">
                        Tải CV dạng PDF, AI sẽ điền sẵn thông tin cá nhân, kỹ năng, kinh nghiệm và học vấn để bạn kiểm tra.
                      </p>
                    </>
                  )}
                </div>
              </section>

              {hasProfile && !uploading ? (
                <section className="cvu-review">
                  <aside className="cvu-card cvu-file" aria-label="File gốc">
                    <div className="cvu-between">
                      <h4>File gốc</h4>
                      {fileName ? <span className="cvu-tiny cvu-muted">{fileName}</span> : null}
                    </div>
                    {previewUrl ? (
                      <iframe className="cvu-pdf" src={previewUrl} title={`Xem trước ${fileName ?? "CV"}`} />
                    ) : (
                      <div className="cvu-paper">
                        <div className="cvu-line" style={{ height: 16, width: "50%", background: "#cfc6ba" }} />
                        <div className="cvu-line" style={{ height: 9, width: "70%" }} />
                        <div className="cvu-rule" />
                        {[92, 88, 95, 70, 0, 85, 90, 78, 93, 60, 0, 88, 82, 76].map((w, i) =>
                          w ? <div key={i} className="cvu-line" style={{ width: `${w}%` }} /> : <div key={i} style={{ height: 10 }} />
                        )}
                        <p className="cvu-help" style={{ marginTop: "auto" }}>
                          Bản xem trước chỉ hiện ngay sau khi bạn tải file lên trong phiên này.
                        </p>
                      </div>
                    )}
                  </aside>

                  <form className="cvu-form" onSubmit={(e) => { e.preventDefault(); void onSave(); }}>
                    {extracted ? <ExtractedProfileView profile={extracted} /> : null}

                    <div className="cvu-note cvu-small">
                      AI có thể đọc sai, nhất là số điện thoại, ngày tháng và tên trường. Hãy xem lại từng mục trước khi lưu.
                    </div>

                    {personal.length || fields.includes(SUMMARY_FIELD) ? (
                      <section className="cvu-card cvu-stack">
                        <h3>Thông tin cá nhân</h3>
                        <div className="cvu-grid">
                          {personal.map((f) => (
                            <div key={f} className="cvu-field">
                              <label htmlFor={`cv-${f}`}>{f}</label>
                              <input
                                id={`cv-${f}`}
                                className="cvu-input"
                                value={(values[f] ?? []).join(", ")}
                                onChange={(e) => setField(f, e.target.value.split(/\s*,\s*/))}
                              />
                            </div>
                          ))}
                          {fields.includes(SUMMARY_FIELD) ? (
                            <div className="cvu-field cvu-span2">
                              <label htmlFor="cv-summary">Giới thiệu</label>
                              <textarea
                                id="cv-summary"
                                className="cvu-input"
                                rows={4}
                                value={(values[SUMMARY_FIELD] ?? []).join("\n")}
                                onChange={(e) => setField(SUMMARY_FIELD, e.target.value.split("\n"))}
                              />
                            </div>
                          ) : null}
                        </div>
                      </section>
                    ) : null}

                    {fields.includes(SKILL_FIELD) ? (
                      <section className="cvu-card cvu-stack">
                        <h3>Kỹ năng</h3>
                        <SkillTags
                          skills={cleanLines(values[SKILL_FIELD])}
                          onChange={(next) => setField(SKILL_FIELD, next)}
                          addLabel="Thêm kỹ năng"
                        />
                        <p className="cvu-help">
                          Kỹ năng được chuẩn hoá theo từ điển kỹ năng (ví dụ “SpringBoot” → “Spring Boot”).
                        </p>
                        {fields.includes(INFERRED_FIELD) ? (
                          <div className="cvu-stack cvu-inferred">
                            <h4>Kỹ năng suy ra</h4>
                            <p className="cvu-help">
                              Không ghi trên CV, hệ thống suy ra từ đồ thị kỹ năng. Xoá nếu không đúng với bạn.
                            </p>
                            <SkillTags
                              skills={cleanLines(values[INFERRED_FIELD])}
                              onChange={(next) => setField(INFERRED_FIELD, next)}
                              addLabel="Thêm kỹ năng suy ra"
                              inferred
                            />
                          </div>
                        ) : null}
                      </section>
                    ) : null}

                    {listFields.map((f) => (
                      <ItemList key={f} field={f} items={values[f] ?? []}
                        onChange={(next) => setField(f, next)} />
                    ))}

                    <div className="cvu-actions">
                      <button type="button" className="cvu-btn cvu-btn-g"
                        disabled={!dirty || saving} onClick={() => setValues(saved)}>
                        Huỷ thay đổi
                      </button>
                      <button type="submit" className="cvu-btn cvu-btn-p"
                        disabled={saving || isSaved}>
                        {saving ? "Đang lưu…" : isSaved ? "Đã lưu" : "Lưu CV"}
                      </button>
                    </div>
                  </form>
                </section>
              ) : null}
            </>
          )}
        </div>
      </main>
    </>
  );
}
