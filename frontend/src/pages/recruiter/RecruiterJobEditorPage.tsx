import { useState, type KeyboardEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Button,
  Field,
  Hint,
  RecruiterLayout,
  TextInput,
  TextSelect,
  TextTextarea,
} from "../../components/common";
import { jobsApi } from "../../api/client";
import { useToast } from "../../context/ToastContext";

const LEVELS = [
  "Intern",
  "Fresher",
  "Junior",
  "Middle",
  "Senior",
  "Lead",
  "Manager",
] as const;

const WORK_TYPES = [
  { value: "Hybrid", label: "Hybrid" },
  { value: "Tại văn phòng", label: "Onsite (Tại văn phòng)" },
  { value: "Remote", label: "Remote" },
] as const;

const CITIES = [
  "TP. Hồ Chí Minh",
  "Hà Nội",
  "Đà Nẵng",
  "Remote",
] as const;

export function RecruiterJobEditorPage() {
  const { toast } = useToast();
  const navigate = useNavigate();

  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState("");
  const [level, setLevel] = useState<string>("Junior");
  const [minYears, setMinYears] = useState(0);
  const [workType, setWorkType] = useState<string>("Hybrid");
  const [city, setCity] = useState<string>("TP. Hồ Chí Minh");
  const [location, setLocation] = useState("");

  const [salaryInput, setSalaryInput] = useState("");
  const [negotiable, setNegotiable] = useState(false);

  const [description, setDescription] = useState("");
  const [requirements, setRequirements] = useState("");
  const [responsibilities, setResponsibilities] = useState("");

  const [requiredSkills, setRequiredSkills] = useState<string[]>([]);
  const [requiredSkillDraft, setRequiredSkillDraft] = useState("");
  const [preferredSkills, setPreferredSkills] = useState<string[]>([]);
  const [preferredSkillDraft, setPreferredSkillDraft] = useState("");

  const salaryText = negotiable ? "Thoả thuận" : salaryInput;

  const hasRequiredFields = Boolean(
    title.trim() &&
      level &&
      workType &&
      city &&
      description.trim() &&
      requirements.trim() &&
      requiredSkills.length > 0
  );
  const hasThreeSkills = requiredSkills.length >= 3;
  const hasDetailedDescription = description.trim().length > 300;

  function addTag(
    raw: string,
    list: string[],
    setList: (next: string[]) => void,
    setDraft: (next: string) => void
  ) {
    const clean = raw.trim();
    if (!clean) return;
    if (!list.some((s) => s.toLowerCase() === clean.toLowerCase())) {
      setList([...list, clean]);
    }
    setDraft("");
  }

  function handleTagKeyDown(
    e: KeyboardEvent<HTMLInputElement>,
    draft: string,
    list: string[],
    setList: (next: string[]) => void,
    setDraft: (next: string) => void
  ) {
    if (e.key === "Enter") {
      e.preventDefault();
      addTag(draft, list, setList, setDraft);
    }
  }

  async function submit(status: "DRAFT" | "PUBLISHED") {
    const cleanTitle = title.trim();
    if (!cleanTitle) {
      toast("Vui lòng nhập tiêu đề tin tuyển dụng.");
      return;
    }
    if (status === "PUBLISHED" && !hasRequiredFields) {
      toast(
        "Vui lòng điền đủ tiêu đề, mô tả, yêu cầu và ít nhất 1 kỹ năng bắt buộc."
      );
      return;
    }

    setBusy(true);
    try {
      await jobsApi.create({
        title: cleanTitle,
        description: description.trim() || cleanTitle,
        location: location.trim(),
        city,
        workType,
        level,
        minYears,
        salaryText: salaryText.trim(),
        status,
        requiredSkills,
        preferredSkills,
        requirements: requirements.trim(),
        responsibilities: responsibilities.trim(),
      });
      toast(
        status === "DRAFT"
          ? "Đã lưu tin nháp"
          : "Đã đăng tin tuyển dụng"
      );
      navigate("/recruiter/jobs");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Lưu tin thất bại");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RecruiterLayout active="jobs">
      <div className="page-head">
        <div>
          <nav
            className="small muted row"
            style={{ gap: 6 }}
            aria-label="Breadcrumb"
          >
            <Link to="/recruiter/jobs">Tin tuyển dụng</Link>
            <span aria-hidden="true">/</span>
            <span style={{ color: "var(--ink)" }}>Đăng tin mới</span>
          </nav>
          <div className="row" style={{ marginTop: 6 }}>
            <h1 style={{ fontSize: 30 }}>
              {title.trim() || "Đăng tin mới"}
            </h1>
          </div>
        </div>
        <div className="row">
          <Button
            variant="ghost"
            disabled={busy}
            onClick={() => void submit("DRAFT")}
          >
            {busy ? "Đang lưu…" : "Lưu nháp"}
          </Button>
          <Button
            variant="primary"
            disabled={busy}
            onClick={() => void submit("PUBLISHED")}
          >
            {busy ? "Đang đăng…" : "Đăng tin"}
          </Button>
        </div>
      </div>

      <div
        style={{
          display: "flex",
          gap: 24,
          flexWrap: "wrap",
          alignItems: "flex-start",
        }}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void submit("PUBLISHED");
          }}
          style={{
            flex: "999 1 560px",
            minWidth: 0,
            display: "flex",
            flexDirection: "column",
            gap: 18,
          }}
        >
          <section className="card stack" style={{ gap: 16, padding: 26 }}>
            <h3 style={{ fontSize: 18 }}>Thông tin chung</h3>
            <div className="form-grid">
              <Field
                label="Tiêu đề tin *"
                htmlFor="job-title"
                className="span2"
              >
                <TextInput
                  id="job-title"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Ví dụ: Senior Java Backend Engineer (Spring Boot)"
                />
              </Field>

              <Field label="Cấp bậc *" htmlFor="job-level">
                <TextSelect
                  id="job-level"
                  value={level}
                  onChange={(e) => setLevel(e.target.value)}
                >
                  {LEVELS.map((lv) => (
                    <option key={lv} value={lv}>
                      {lv}
                    </option>
                  ))}
                </TextSelect>
              </Field>

              <Field label="Kinh nghiệm tối thiểu" htmlFor="job-min-years">
                <TextSelect id="job-min-years" value={String(minYears)} onChange={(e) => setMinYears(Number(e.target.value))}>
                  <option value="0">Không yêu cầu</option>
                  {[1, 2, 3, 4, 5].map((y) => <option key={y} value={y}>{y} năm</option>)}
                </TextSelect>
              </Field>

              <Field label="Hình thức làm việc *" htmlFor="job-work-type">
                <TextSelect
                  id="job-work-type"
                  value={workType}
                  onChange={(e) => setWorkType(e.target.value)}
                >
                  {WORK_TYPES.map((w) => (
                    <option key={w.value} value={w.value}>
                      {w.label}
                    </option>
                  ))}
                </TextSelect>
              </Field>

              <Field label="Thành phố *" htmlFor="job-city">
                <TextSelect
                  id="job-city"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                >
                  {CITIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </TextSelect>
              </Field>

              <Field label="Địa chỉ làm việc" htmlFor="job-location">
                <TextInput
                  id="job-location"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  placeholder="Số nhà, đường, quận"
                />
              </Field>
            </div>
          </section>

          <section className="card stack" style={{ gap: 16, padding: 26 }}>
            <h3 style={{ fontSize: 18 }}>Mức lương</h3>
            <div className="form-grid">
              <Field
                label="Mức lương"
                htmlFor="job-salary"
                className="span2"
              >
                <TextInput
                  id="job-salary"
                  value={salaryText}
                  disabled={negotiable}
                  onChange={(e) => setSalaryInput(e.target.value)}
                  placeholder="Ví dụ: 25 – 40 triệu VND"
                />
              </Field>
              <label className="check span2">
                <input
                  type="checkbox"
                  checked={negotiable}
                  onChange={(e) => setNegotiable(e.target.checked)}
                />
                Thoả thuận
              </label>
            </div>
          </section>

          <section className="card stack" style={{ gap: 16, padding: 26 }}>
            <h3 style={{ fontSize: 18 }}>Nội dung</h3>

            <Field label="Mô tả công việc *" htmlFor="job-description">
              <TextTextarea
                id="job-description"
                required
                style={{ minHeight: 140 }}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Giới thiệu vị trí, bối cảnh đội ngũ và sản phẩm đang phát triển"
              />
            </Field>

            <Field label="Yêu cầu *" htmlFor="job-requirements">
              <TextTextarea
                id="job-requirements"
                required
                style={{ minHeight: 120 }}
                value={requirements}
                onChange={(e) => setRequirements(e.target.value)}
                placeholder={"Ít nhất 2 năm kinh nghiệm Java\nHiểu biết về Docker, SQL"}
              />
              <Hint>Mỗi dòng một ý giúp ghép hồ sơ chính xác hơn.</Hint>
            </Field>

            <Field label="Trách nhiệm" htmlFor="job-responsibilities">
              <TextTextarea
                id="job-responsibilities"
                style={{ minHeight: 110 }}
                value={responsibilities}
                onChange={(e) => setResponsibilities(e.target.value)}
                placeholder={"Thiết kế và phát triển REST API\nReview code cùng đội ngũ"}
              />
              <Hint>Mỗi dòng một trách nhiệm.</Hint>
            </Field>

            <Field label="Kỹ năng bắt buộc *" htmlFor="job-req-skill">
              <div className="row" style={{ gap: 6 }}>
                {requiredSkills.map((skill) => (
                  <span key={skill} className="tag tag-on">
                    {skill}
                    <button
                      type="button"
                      aria-label={`Xoá kỹ năng bắt buộc ${skill}`}
                      onClick={() =>
                        setRequiredSkills(
                          requiredSkills.filter((s) => s !== skill)
                        )
                      }
                      style={{
                        background: "none",
                        border: 0,
                        padding: "0 0 0 6px",
                        cursor: "pointer",
                        color: "inherit",
                        fontWeight: 700,
                        lineHeight: 1,
                      }}
                    >
                      ×
                    </button>
                  </span>
                ))}
                <input
                  id="job-req-skill"
                  className="input"
                  value={requiredSkillDraft}
                  onChange={(e) => setRequiredSkillDraft(e.target.value)}
                  onKeyDown={(e) =>
                    handleTagKeyDown(
                      e,
                      requiredSkillDraft,
                      requiredSkills,
                      setRequiredSkills,
                      setRequiredSkillDraft
                    )
                  }
                  placeholder="Thêm kỹ năng rồi nhấn Enter…"
                  style={{ width: 220, height: 32 }}
                />
              </div>
              <Hint>
                Nhấn Enter để thêm kỹ năng. Dùng cho matching và chọn câu hỏi
                phỏng vấn.
              </Hint>
            </Field>

            <Field label="Kỹ năng ưu tiên" htmlFor="job-pref-skill">
              <div className="row" style={{ gap: 6 }}>
                {preferredSkills.map((skill) => (
                  <span key={skill} className="tag">
                    {skill}
                    <button
                      type="button"
                      aria-label={`Xoá kỹ năng ưu tiên ${skill}`}
                      onClick={() =>
                        setPreferredSkills(
                          preferredSkills.filter((s) => s !== skill)
                        )
                      }
                      style={{
                        background: "none",
                        border: 0,
                        padding: "0 0 0 6px",
                        cursor: "pointer",
                        color: "inherit",
                        fontWeight: 700,
                        lineHeight: 1,
                      }}
                    >
                      ×
                    </button>
                  </span>
                ))}
                <input
                  id="job-pref-skill"
                  className="input"
                  value={preferredSkillDraft}
                  onChange={(e) => setPreferredSkillDraft(e.target.value)}
                  onKeyDown={(e) =>
                    handleTagKeyDown(
                      e,
                      preferredSkillDraft,
                      preferredSkills,
                      setPreferredSkills,
                      setPreferredSkillDraft
                    )
                  }
                  placeholder="Thêm kỹ năng ưu tiên rồi nhấn Enter…"
                  style={{ width: 240, height: 32 }}
                />
              </div>
            </Field>
          </section>
        </form>

        <aside
          style={{
            flex: "1 1 300px",
            maxWidth: 360,
            display: "flex",
            flexDirection: "column",
            gap: 16,
          }}
        >
          <section className="card stack" style={{ gap: 8 }}>
            <h4>Kiểm tra trước khi đăng</h4>
            <p
              className="small"
              style={{
                color: hasRequiredFields ? "var(--ok)" : "var(--warn)",
              }}
            >
              {hasRequiredFields ? "✓" : "!"} Đủ trường bắt buộc
            </p>
            <p
              className="small"
              style={{
                color: hasThreeSkills ? "var(--ok)" : "var(--warn)",
              }}
            >
              {hasThreeSkills ? "✓" : "!"} Có ít nhất 3 kỹ năng bắt buộc (
              {requiredSkills.length}/3)
            </p>
            <p
              className="small"
              style={{
                color: hasDetailedDescription ? "var(--ok)" : "var(--warn)",
              }}
            >
              {hasDetailedDescription
                ? "✓ Mô tả chi tiết (> 300 ký tự)"
                : `! Mô tả ngắn, nên trên 300 ký tự (${description.trim().length}/300)`}
            </p>
          </section>
        </aside>
      </div>
    </RecruiterLayout>
  );
}
