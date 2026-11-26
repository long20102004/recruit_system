import { useEffect, useState, type FormEvent } from "react";
import { EmptyNote, MockNote, SiteHeader } from "../../components/common";
import {
  MAX_JOB_ALERTS,
  jobAlertsMock,
  type JobAlertFrequency,
  type JobAlertItem,
} from "../../api/mock/candidateMock";
import { useToast } from "../../context/ToastContext";

/** Màn C09 · Job alert (design canvas JobAlerts.dc.html). */

const CITIES = ["Hà Nội", "TP. Hồ Chí Minh", "Đà Nẵng", "Remote", "Tất cả thành phố"] as const;
const LEVELS = ["Intern", "Junior", "Middle", "Senior", "Lead", "Mọi cấp bậc"] as const;

interface AlertFormState {
  name: string;
  keywordsText: string;
  city: string;
  level: string;
  minSalaryText: string;
  inApp: boolean;
  email: boolean;
  frequency: JobAlertFrequency;
}

const DEFAULT_FORM: AlertFormState = {
  name: "Java Middle Hà Nội",
  keywordsText: "Java, Spring Boot",
  city: "Hà Nội",
  level: "Middle",
  minSalaryText: "25",
  inApp: true,
  email: true,
  frequency: "instant",
};

function parseKeywords(raw: string): string[] {
  return raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function formatFrequencySummary(alert: JobAlertItem): string {
  const ch: string[] = [];
  if (alert.channels.inApp) ch.push("Thông báo");
  if (alert.channels.email) ch.push("Email");
  const channelLabel = ch.join(" + ");

  if (alert.frequency === "daily") {
    return channelLabel
      ? `Email mỗi ngày lúc 08:00 · ${channelLabel}`
      : "Gom một email mỗi ngày";
  }
  return channelLabel ? `Ngay khi có tin · ${channelLabel}` : "Ngay khi có tin";
}

function alertTags(alert: JobAlertItem): string[] {
  const tags = [...alert.keywords];
  if (alert.city) tags.push(alert.city);
  if (alert.level) tags.push(alert.level);
  if (alert.minSalary != null && alert.minSalary > 0) {
    tags.push(`Từ ${alert.minSalary} triệu`);
  }
  return tags;
}

export function CandidateJobAlertsPage() {
  const { toast } = useToast();
  const [alerts, setAlerts] = useState<JobAlertItem[] | null>(null);
  const [form, setForm] = useState<AlertFormState>(DEFAULT_FORM);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    jobAlertsMock
      .list()
      .then(setAlerts)
      .catch((e) => {
        setAlerts([]);
        toast(e instanceof Error ? e.message : "Không tải được danh sách job alert");
      });
  }, [toast]);

  function resetForm() {
    setEditingId(null);
    setForm(DEFAULT_FORM);
    setFormError(null);
  }

  function onStartEdit(alert: JobAlertItem) {
    setEditingId(alert.id);
    setFormError(null);
    setForm({
      name: alert.name,
      keywordsText: alert.keywords.join(", "),
      city: alert.city,
      level: alert.level,
      minSalaryText: alert.minSalary != null ? String(alert.minSalary) : "",
      inApp: alert.channels.inApp,
      email: alert.channels.email,
      frequency: alert.frequency,
    });
  }

  async function onToggle(alert: JobAlertItem) {
    setBusyId(alert.id);
    try {
      const updated = await jobAlertsMock.toggle(alert.id, !alert.enabled);
      setAlerts((prev) =>
        prev ? prev.map((a) => (a.id === updated.id ? updated : a)) : prev
      );
      toast(updated.enabled ? `Đã bật “${updated.name}”.` : `Đã tạm tắt “${updated.name}”.`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không thể cập nhật trạng thái");
    } finally {
      setBusyId(null);
    }
  }

  async function onDelete(alert: JobAlertItem) {
    setBusyId(alert.id);
    try {
      await jobAlertsMock.remove(alert.id);
      setAlerts((prev) => (prev ? prev.filter((a) => a.id !== alert.id) : prev));
      if (editingId === alert.id) resetForm();
      toast(`Đã xoá job alert “${alert.name}”.`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không thể xoá job alert");
    } finally {
      setBusyId(null);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    const trimmedSalary = form.minSalaryText.trim();
    const minSalary = trimmedSalary === "" ? null : Number(trimmedSalary);
    const payload = {
      name: form.name,
      keywords: parseKeywords(form.keywordsText),
      city: form.city,
      level: form.level,
      minSalary,
      channels: { inApp: form.inApp, email: form.email },
      frequency: form.frequency,
    };

    setSubmitting(true);
    try {
      if (editingId != null) {
        const updated = await jobAlertsMock.update(editingId, payload);
        setAlerts((prev) =>
          prev ? prev.map((a) => (a.id === updated.id ? updated : a)) : prev
        );
        toast(`Đã cập nhật “${updated.name}”.`);
        resetForm();
      } else {
        const created = await jobAlertsMock.create(payload);
        setAlerts((prev) => (prev ? [created, ...prev] : [created]));
        toast(`Đã tạo job alert “${created.name}”.`);
        setForm({
          name: "",
          keywordsText: "",
          city: "Hà Nội",
          level: "Middle",
          minSalaryText: "",
          inApp: true,
          email: true,
          frequency: "instant",
        });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Không thể lưu job alert";
      setFormError(message);
      toast(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <SiteHeader active="home" mode="candidate" />
      <div
        className="wrap"
        style={{
          paddingTop: 32,
          paddingBottom: 64,
          display: "flex",
          flexDirection: "column",
          gap: 18,
        }}
      >
        <MockNote />

        <div
          style={{
            display: "flex",
            gap: 24,
            flexWrap: "wrap",
            alignItems: "flex-start",
          }}
        >
          <main
            style={{
              flex: "999 1 520px",
              minWidth: 0,
              display: "flex",
              flexDirection: "column",
              gap: 16,
            }}
          >
            <div>
              <h1 style={{ fontSize: 34 }}>Job alert</h1>
              <p className="muted" style={{ marginTop: 6 }}>
                Nhận thông báo khi có tin mới khớp tiêu chí. Tối đa {MAX_JOB_ALERTS} job alert (
                {alerts?.length ?? 0}/{MAX_JOB_ALERTS}).
              </p>
            </div>

            {alerts === null ? (
              <p className="muted">Đang tải…</p>
            ) : alerts.length === 0 ? (
              <EmptyNote>
                Bạn chưa có job alert nào. Tạo alert ở biểu mẫu bên cạnh để nhận thông báo việc mới.
              </EmptyNote>
            ) : (
              alerts.map((a) => (
                <article
                  key={a.id}
                  className="card"
                  style={{
                    display: "flex",
                    gap: 16,
                    flexWrap: "wrap",
                    alignItems: "center",
                    borderColor: editingId === a.id ? "var(--brand)" : undefined,
                  }}
                >
                  <div
                    style={{
                      flex: "1 1 320px",
                      minWidth: 0,
                      display: "flex",
                      flexDirection: "column",
                      gap: 8,
                    }}
                  >
                    <div className="row" style={{ gap: 8 }}>
                      <h3 style={{ fontSize: 18 }}>{a.name}</h3>
                      <span className={a.enabled ? "badge b-ok" : "badge"}>
                        {a.enabled ? "Đang bật" : "Tạm tắt"}
                      </span>
                    </div>
                    <div className="row" style={{ gap: 6 }}>
                      {alertTags(a).map((t, idx) => (
                        <span key={`${t}-${idx}`} className="tag">
                          {t}
                        </span>
                      ))}
                    </div>
                    <p className="small muted">
                      {formatFrequencySummary(a)} ·{" "}
                      {a.matchedCount > 0
                        ? `${a.matchedCount} tin khớp tuần này`
                        : "Chưa có tin khớp"}
                    </p>
                  </div>

                  <div className="row" style={{ gap: 8 }}>
                    <label className="check small">
                      <input
                        type="checkbox"
                        checked={a.enabled}
                        disabled={busyId === a.id}
                        onChange={() => onToggle(a)}
                      />
                      Bật
                    </label>
                    <button
                      type="button"
                      className="btn btn-g btn-sm"
                      disabled={busyId === a.id}
                      onClick={() => onStartEdit(a)}
                    >
                      Sửa
                    </button>
                    <button
                      type="button"
                      className="btn btn-d btn-sm"
                      disabled={busyId === a.id}
                      onClick={() => onDelete(a)}
                    >
                      Xoá
                    </button>
                  </div>
                </article>
              ))
            )}
          </main>

          <aside
            className="card"
            style={{
              flex: "1 1 340px",
              maxWidth: 420,
              display: "flex",
              flexDirection: "column",
              gap: 14,
            }}
          >
            <form onSubmit={onSubmit} className="stack" style={{ gap: 14 }}>
              <div className="between">
                <h3 style={{ fontSize: 20 }}>
                  {editingId != null ? "Cập nhật job alert" : "Tạo job alert mới"}
                </h3>
                {editingId != null ? (
                  <button type="button" className="btn btn-link small" onClick={resetForm}>
                    Hủy sửa
                  </button>
                ) : null}
              </div>

              {formError ? (
                <p className="note note-warn small" role="alert">
                  {formError}
                </p>
              ) : null}

              <div className="field">
                <label htmlFor="alert-name">Tên alert</label>
                <input
                  id="alert-name"
                  className="input"
                  value={form.name}
                  placeholder="Ví dụ: Java Middle Hà Nội"
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                />
              </div>

              <div className="field">
                <label htmlFor="alert-keywords">Từ khoá / kỹ năng</label>
                <input
                  id="alert-keywords"
                  className="input"
                  value={form.keywordsText}
                  placeholder="Java, Spring Boot"
                  onChange={(e) => setForm((f) => ({ ...f, keywordsText: e.target.value }))}
                />
              </div>

              <div className="form-grid">
                <div className="field">
                  <label htmlFor="alert-city">Thành phố</label>
                  <select
                    id="alert-city"
                    className="input"
                    value={form.city}
                    onChange={(e) => setForm((f) => ({ ...f, city: e.target.value }))}
                  >
                    {CITIES.map((city) => (
                      <option key={city} value={city}>
                        {city}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="field">
                  <label htmlFor="alert-level">Cấp bậc</label>
                  <select
                    id="alert-level"
                    className="input"
                    value={form.level}
                    onChange={(e) => setForm((f) => ({ ...f, level: e.target.value }))}
                  >
                    {LEVELS.map((level) => (
                      <option key={level} value={level}>
                        {level}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="field">
                <label htmlFor="alert-salary">Lương tối thiểu (triệu/tháng)</label>
                <input
                  id="alert-salary"
                  type="number"
                  min={0}
                  className="input"
                  value={form.minSalaryText}
                  placeholder="Ví dụ: 25"
                  onChange={(e) => setForm((f) => ({ ...f, minSalaryText: e.target.value }))}
                />
              </div>

              <fieldset
                style={{
                  border: 0,
                  padding: 0,
                  margin: 0,
                  display: "flex",
                  flexDirection: "column",
                  gap: 4,
                }}
              >
                <legend className="lbl" style={{ marginBottom: 6 }}>
                  Gửi qua
                </legend>
                <label className="check small">
                  <input
                    type="checkbox"
                    checked={form.inApp}
                    onChange={(e) => setForm((f) => ({ ...f, inApp: e.target.checked }))}
                  />
                  Thông báo trong ứng dụng
                </label>
                <label className="check small">
                  <input
                    type="checkbox"
                    checked={form.email}
                    onChange={(e) => setForm((f) => ({ ...f, email: e.target.checked }))}
                  />
                  Email
                </label>
              </fieldset>

              <fieldset
                style={{
                  border: 0,
                  padding: 0,
                  margin: 0,
                  display: "flex",
                  flexDirection: "column",
                  gap: 4,
                }}
              >
                <legend className="lbl" style={{ marginBottom: 6 }}>
                  Tần suất
                </legend>
                <label className="check small">
                  <input
                    type="radio"
                    name="alert-frequency"
                    checked={form.frequency === "instant"}
                    onChange={() => setForm((f) => ({ ...f, frequency: "instant" }))}
                  />
                  Ngay khi có tin mới
                </label>
                <label className="check small">
                  <input
                    type="radio"
                    name="alert-frequency"
                    checked={form.frequency === "daily"}
                    onChange={() => setForm((f) => ({ ...f, frequency: "daily" }))}
                  />
                  Gom một email mỗi ngày
                </label>
              </fieldset>

              <button type="submit" className="btn btn-p" disabled={submitting}>
                {submitting
                  ? "Đang lưu…"
                  : editingId != null
                    ? "Lưu thay đổi"
                    : "Tạo job alert"}
              </button>
            </form>
          </aside>
        </div>
      </div>
    </>
  );
}
