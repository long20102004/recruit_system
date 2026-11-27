import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  accountApi,
  type Gender,
  type NotificationPrefDto,
  type NotificationType,
  type ProfileDto,
} from "../api/client";
import { SiteHeader } from "../components/common";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { initials } from "../utils/format";

/** Màn C14 · Hồ sơ & mật khẩu (design canvas Profile.dc.html), specs/006-account-settings. */

const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,100}$/;
const PASSWORD_HINT = "Mật khẩu cần 8–100 ký tự, gồm cả chữ và số";

const ROLE_LABEL: Record<string, string> = {
  CANDIDATE: "Ứng viên",
  RECRUITER: "Nhà tuyển dụng",
  ADMIN: "Quản trị viên",
};

const NOTIF_LABEL: Record<NotificationType, string> = {
  APPLICATION_STATUS: "Trạng thái đơn ứng tuyển thay đổi",
  INTERVIEW_INVITE: "Lời mời phỏng vấn",
  JOB_ALERT: "Job alert",
  COMPANY_INVITE: "Lời mời tham gia công ty",
  CV_PROCESSED: "AI xử lý CV xong",
  COMPANY_STATUS: "Trạng thái duyệt công ty",
  JOB_MODERATION: "Tin tuyển dụng bị kiểm duyệt / khoá",
};

const SECTIONS = [
  { id: "info", label: "Thông tin cá nhân" },
  { id: "pw", label: "Đổi mật khẩu" },
  { id: "notif", label: "Cài đặt thông báo" },
] as const;

const errMsg = (e: unknown, fallback: string) => (e instanceof Error && e.message ? e.message : fallback);

interface InfoForm {
  fullName: string;
  phone: string;
  dateOfBirth: string;
  gender: Gender | "";
}

function toForm(p: ProfileDto): InfoForm {
  return {
    fullName: p.fullName ?? "",
    phone: p.phone ?? "",
    dateOfBirth: p.dateOfBirth ?? "",
    gender: p.gender ?? "",
  };
}

const today = () => new Date().toISOString().slice(0, 10);

export function AccountSettingsPage() {
  const { logout, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<ProfileDto | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [active, setActive] = useState<string>("info");

  useEffect(() => {
    accountApi.profile().then(setProfile).catch((e) => setLoadError(errMsg(e, "Không tải được hồ sơ")));
  }, []);

  function go(id: string) {
    setActive(id);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function onLogout() {
    logout();
    navigate("/");
  }

  return (
    <>
      <SiteHeader active="profile" mode="candidate" />
      <div className="wrap" style={{ paddingTop: 32, paddingBottom: 64, display: "flex", gap: 28, flexWrap: "wrap",
        alignItems: "flex-start", maxWidth: 1080 }}>
        <nav aria-label="Cài đặt tài khoản" className="card" style={{ flex: "1 1 200px", maxWidth: 240, padding: 8,
          display: "flex", flexDirection: "column", gap: 2, position: "sticky", top: 88 }}>
          {SECTIONS.map((s) => (
            <a key={s.id} href={`#${s.id}`} aria-current={active === s.id ? "true" : undefined}
              onClick={(e) => { e.preventDefault(); go(s.id); }}
              style={{ minHeight: 42, display: "flex", alignItems: "center", padding: "0 10px", fontWeight: 600,
                fontSize: 14, textDecoration: "none",
                background: active === s.id ? "var(--brand-soft)" : undefined,
                color: active === s.id ? "var(--brand-deep)" : "var(--ink-soft)" }}>
              {s.label}
            </a>
          ))}
          <button type="button" onClick={onLogout}
            style={{ minHeight: 42, textAlign: "left", padding: "0 10px", font: "600 14px var(--font-body)",
              color: "var(--danger)", background: "none", border: 0, borderTop: "1px solid var(--line)",
              marginTop: 6, cursor: "pointer" }}>
            Đăng xuất
          </button>
        </nav>

        <main style={{ flex: "999 1 520px", minWidth: 0, display: "flex", flexDirection: "column", gap: 20 }}>
          {loadError ? <p className="note note-warn">{loadError}</p> : null}
          {!profile && !loadError ? <p className="muted">Đang tải…</p> : null}
          {profile ? (
            <>
              <InfoSection profile={profile} onSaved={(p) => { setProfile(p); void refreshUser(); }} />
              <PasswordSection profile={profile} onChanged={() => setProfile({ ...profile, passwordSet: true })} />
            </>
          ) : null}
          <NotificationSection />
        </main>
      </div>
    </>
  );
}

function InfoSection({ profile, onSaved }: { profile: ProfileDto; onSaved: (p: ProfileDto) => void }) {
  const { toast } = useToast();
  const [form, setForm] = useState<InfoForm>(() => toForm(profile));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initial = toForm(profile);
  const dirty = (Object.keys(form) as (keyof InfoForm)[]).some((k) => form[k] !== initial[k]);
  const nameMissing = !form.fullName.trim();
  const set = (patch: Partial<InfoForm>) => setForm((f) => ({ ...f, ...patch }));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (nameMissing || !dirty) return;
    setSaving(true);
    setError(null);
    try {
      const saved = await accountApi.updateProfile({
        fullName: form.fullName.trim(),
        phone: form.phone.trim() || null,
        dateOfBirth: form.dateOfBirth || null,
        gender: form.gender || null,
      });
      setForm(toForm(saved));
      onSaved(saved);
      toast("Đã lưu thông tin cá nhân");
    } catch (err) {
      setError(errMsg(err, "Không lưu được thông tin"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form id="info" className="card stack" style={{ gap: 16, padding: 28, scrollMarginTop: 88 }} onSubmit={onSubmit}>
      <h2 style={{ fontSize: 22 }}>Thông tin cá nhân</h2>
      <div className="row" style={{ gap: 16 }}>
        <span className="avatar" aria-hidden="true" style={{ width: 72, height: 72, fontSize: 22 }}>
          {initials(form.fullName || profile.fullName)}
        </span>
        <div className="stack" style={{ gap: 4 }}>
          <strong>{profile.fullName}</strong>
          <span className="help">{profile.googleLinked ? "Đã liên kết tài khoản Google" : profile.email}</span>
        </div>
      </div>
      <div className="form-grid">
        <div className="field">
          <label htmlFor="acc-name">Họ và tên</label>
          <input id="acc-name" className="input" value={form.fullName} maxLength={100} required
            aria-invalid={nameMissing || undefined} onChange={(e) => set({ fullName: e.target.value })} />
          {nameMissing ? <span className="help" style={{ color: "var(--danger)" }}>Vui lòng nhập họ tên.</span> : null}
        </div>
        <div className="field">
          <label htmlFor="acc-email">Email</label>
          <input id="acc-email" className="input" value={profile.email} disabled
            style={{ background: "var(--bg)", color: "var(--muted)" }} />
          <span className="help">Email đăng nhập, không thể đổi.</span>
        </div>
        <div className="field">
          <label htmlFor="acc-phone">Số điện thoại</label>
          <input id="acc-phone" className="input" type="tel" value={form.phone} maxLength={20}
            placeholder="0912 345 678" onChange={(e) => set({ phone: e.target.value })} />
        </div>
        <div className="field">
          <label htmlFor="acc-dob">Ngày sinh</label>
          <input id="acc-dob" className="input" type="date" value={form.dateOfBirth} max={today()}
            onChange={(e) => set({ dateOfBirth: e.target.value })} />
        </div>
        <div className="field">
          <label htmlFor="acc-gender">Giới tính</label>
          <select id="acc-gender" className="input" value={form.gender}
            onChange={(e) => set({ gender: e.target.value as Gender | "" })}>
            <option value="">Chưa chọn</option>
            <option value="MALE">Nam</option>
            <option value="FEMALE">Nữ</option>
            <option value="OTHER">Khác</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="acc-role">Vai trò</label>
          <input id="acc-role" className="input" value={ROLE_LABEL[profile.role] ?? profile.role} disabled
            style={{ background: "var(--bg)", color: "var(--muted)" }} />
        </div>
      </div>
      {error ? <p className="note note-warn" role="alert">{error}</p> : null}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button type="submit" className="btn btn-p" disabled={!dirty || nameMissing || saving}>
          {saving ? "Đang lưu…" : "Lưu thay đổi"}
        </button>
      </div>
    </form>
  );
}

function PasswordSection({ profile, onChanged }: { profile: ProfileDto; onChanged: () => void }) {
  const { applySession } = useAuth();
  const { toast } = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needCurrent = profile.passwordSet;
  const weak = next.length > 0 && !PASSWORD_RE.test(next);
  const mismatch = confirm.length > 0 && confirm !== next;
  const ready = (!needCurrent || current.length > 0) && PASSWORD_RE.test(next) && confirm === next;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!ready) return;
    setSaving(true);
    setError(null);
    try {
      const res = await accountApi.changePassword(needCurrent ? current : null, next);
      applySession(res);
      setCurrent("");
      setNext("");
      setConfirm("");
      onChanged();
      toast(needCurrent ? "Đã đổi mật khẩu. Các thiết bị khác đã bị đăng xuất." : "Đã đặt mật khẩu cho tài khoản");
    } catch (err) {
      setError(errMsg(err, "Không đổi được mật khẩu"));
    } finally {
      setSaving(false);
    }
  }

  const danger = { color: "var(--danger)" };
  return (
    <form id="pw" className="card stack" style={{ gap: 16, padding: 28, scrollMarginTop: 88 }} onSubmit={onSubmit}>
      <h2 style={{ fontSize: 22 }}>{needCurrent ? "Đổi mật khẩu" : "Đặt mật khẩu"}</h2>
      {!needCurrent ? (
        <p className="note">Tài khoản được tạo bằng Google nên chưa có mật khẩu. Đặt mật khẩu để có thể đăng nhập bằng email.</p>
      ) : null}
      <input type="text" name="username" autoComplete="username" value={profile.email} readOnly hidden />
      <div className="form-grid">
        {needCurrent ? (
          <div className="field span2">
            <label htmlFor="pw-current">Mật khẩu hiện tại</label>
            <input id="pw-current" className="input" type="password" autoComplete="current-password"
              value={current} onChange={(e) => setCurrent(e.target.value)} />
          </div>
        ) : null}
        <div className="field">
          <label htmlFor="pw-new">Mật khẩu mới</label>
          <input id="pw-new" className="input" type="password" autoComplete="new-password" maxLength={100}
            value={next} aria-invalid={weak || undefined} onChange={(e) => setNext(e.target.value)} />
          <span className="help" style={weak ? danger : undefined}>{PASSWORD_HINT}.</span>
        </div>
        <div className="field">
          <label htmlFor="pw-confirm">Nhập lại mật khẩu mới</label>
          <input id="pw-confirm" className="input" type="password" autoComplete="new-password" maxLength={100}
            value={confirm} aria-invalid={mismatch || undefined} onChange={(e) => setConfirm(e.target.value)} />
          {mismatch ? <span className="help" style={danger}>Mật khẩu nhập lại không khớp.</span> : null}
        </div>
      </div>
      {error ? <p className="note note-warn" role="alert">{error}</p> : null}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button type="submit" className="btn btn-p" disabled={!ready || saving}>
          {saving ? "Đang lưu…" : needCurrent ? "Đổi mật khẩu" : "Đặt mật khẩu"}
        </button>
      </div>
    </form>
  );
}

function NotificationSection() {
  const { toast } = useToast();
  const [items, setItems] = useState<NotificationPrefDto[] | null>(null);
  const [saved, setSaved] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    accountApi.notifications()
      .then((r) => { setItems(r.items); setSaved(JSON.stringify(r.items)); })
      .catch((e) => setError(errMsg(e, "Không tải được cài đặt thông báo")));
  }, []);

  const dirty = items !== null && JSON.stringify(items) !== saved;
  const toggle = (type: NotificationType, key: "inApp" | "email") =>
    setItems((xs) => xs?.map((x) => (x.type === type ? { ...x, [key]: !x[key] } : x)) ?? xs);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!items || !dirty) return;
    setSaving(true);
    setError(null);
    try {
      const r = await accountApi.updateNotifications(items);
      setItems(r.items);
      setSaved(JSON.stringify(r.items));
      toast("Đã lưu cài đặt thông báo");
    } catch (err) {
      setError(errMsg(err, "Không lưu được cài đặt"));
    } finally {
      setSaving(false);
    }
  }

  const box = { width: 18, height: 18, accentColor: "var(--brand)" };
  return (
    <form id="notif" className="card stack" style={{ gap: 12, padding: 28, scrollMarginTop: 88 }} onSubmit={onSubmit}>
      <h2 style={{ fontSize: 22 }}>Cài đặt thông báo</h2>
      {items ? (
        <div className="tbl-box" style={{ border: 0 }}>
          <table className="tbl" style={{ minWidth: 480 }}>
            <thead><tr><th>Loại thông báo</th><th>Trong ứng dụng</th><th>Email</th></tr></thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.type}>
                  <td>{NOTIF_LABEL[p.type] ?? p.type}</td>
                  <td><input type="checkbox" style={box} checked={p.inApp}
                    aria-label={`${NOTIF_LABEL[p.type]}: trong ứng dụng`} onChange={() => toggle(p.type, "inApp")} /></td>
                  <td><input type="checkbox" style={box} checked={p.email}
                    aria-label={`${NOTIF_LABEL[p.type]}: email`} onChange={() => toggle(p.type, "email")} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : !error ? <p className="muted">Đang tải…</p> : null}
      {error ? <p className="note note-warn" role="alert">{error}</p> : null}
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button type="submit" className="btn btn-p" disabled={!dirty || saving}>
          {saving ? "Đang lưu…" : "Lưu cài đặt"}
        </button>
      </div>
    </form>
  );
}
