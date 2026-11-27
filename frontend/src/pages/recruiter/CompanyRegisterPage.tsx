import { useEffect, useState, type ChangeEvent, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { RecruiterLayout } from "../../components/common";
import {
  getCompanyProfile,
  saveCompanyDraft,
  submitCompanyRegistration,
  uploadCompanyFile,
  type CompanyProfile,
  type CompanyRegistrationInput,
} from "../../api/mock/recruiterMock";
import { useToast } from "../../context/ToastContext";
import { initials } from "../../utils/format";

const INDUSTRIES = [
  "Fintech",
  "Thương mại điện tử",
  "Outsourcing",
  "Phần mềm doanh nghiệp",
  "Ngân hàng số",
];

const COMPANY_SIZES = [
  "Dưới 50",
  "50 – 100",
  "100 – 300",
  "300 – 500 nhân viên",
  "Trên 500 nhân viên",
];

const COMPANY_TYPES = ["Product", "Outsourcing", "Agency"];

function formatFileSize(bytes: number): string {
  if (bytes >= 1024 * 1024) {
    return `${(bytes / (1024 * 1024)).toFixed(1).replace(".", ",")} MB`;
  }
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function toFormInput(p: CompanyProfile): CompanyRegistrationInput {
  return {
    name: p.name,
    taxCode: p.taxCode,
    industry: p.industry,
    size: p.size,
    companyType: p.companyType,
    website: p.website,
    foundedYear: p.foundedYear,
    headquarters: p.headquarters,
    contactEmail: p.contactEmail,
    contactPhone: p.contactPhone,
    shortBio: p.shortBio,
    logoFileName: p.logoFileName,
    licenseFileName: p.licenseFileName,
    licenseFileMeta: p.licenseFileMeta,
    confirmed: p.confirmed,
  };
}

export function CompanyRegisterPage() {
  const { toast } = useToast();
  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [form, setForm] = useState<CompanyRegistrationInput | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getCompanyProfile()
      .then((data) => {
        setCompany(data);
        setForm(toFormInput(data));
      })
      .catch((e) => toast(e instanceof Error ? e.message : "Không tải được hồ sơ công ty"));
  }, [toast]);

  /** Tải thẳng lên R2 khi chọn (logo: bucket public, giấy phép: bucket private). */
  async function uploadFile(kind: "logo" | "license", e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !form) return;
    try {
      const updated = await uploadCompanyFile(kind, file);
      setCompany(updated);
      setForm((f) =>
        f
          ? {
              ...f,
              logoFileName: updated.logoFileName,
              licenseFileName: updated.licenseFileName,
              licenseFileMeta: updated.licenseFileMeta || formatFileSize(file.size),
            }
          : f
      );
      toast(kind === "logo" ? "Đã tải logo lên." : "Đã tải giấy phép lên.");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Không tải được tệp.");
    }
  }

  const handleLogoChange = (e: ChangeEvent<HTMLInputElement>) => void uploadFile("logo", e);
  const handleLicenseChange = (e: ChangeEvent<HTMLInputElement>) => void uploadFile("license", e);

  async function handleSaveDraft() {
    if (!form) return;
    setBusy(true);
    try {
      const updated = await saveCompanyDraft(form);
      setCompany(updated);
      toast("Đã lưu bản nháp hồ sơ công ty.");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Lưu nháp thất bại");
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!form) return;
    setBusy(true);
    try {
      const updated = await submitCompanyRegistration(form);
      setCompany(updated);
      toast("Đã gửi hồ sơ đăng ký công ty (trạng thái: PENDING).");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Gửi đăng ký thất bại");
    } finally {
      setBusy(false);
    }
  }

  return (
    <RecruiterLayout active="company">
      {!company || !form ? (
        <p className="muted">Đang tải thông tin đăng ký công ty…</p>
      ) : (
        <div style={{ display: "flex", gap: 28, flexWrap: "wrap", alignItems: "flex-start" }}>
          <form
            onSubmit={(e) => void handleSubmit(e)}
            style={{ flex: "999 1 560px", minWidth: 0, display: "flex", flexDirection: "column", gap: 18 }}
          >
            <div>
              <p className="kicker">Bước 1 · Đăng ký công ty</p>
              <h1 style={{ fontSize: 34, marginTop: 6 }}>Đăng ký công ty để bắt đầu tuyển dụng</h1>
              <p className="muted" style={{ marginTop: 6 }}>
                Quản trị viên sẽ duyệt hồ sơ trong 1–2 ngày làm việc. Bạn sẽ là Owner của công ty.
              </p>
            </div>

            <section className="card stack" style={{ gap: 16, padding: 28 }}>
              <h3 style={{ fontSize: 18 }}>Thông tin công ty</h3>
              <div className="form-grid">
                <div className="field span2">
                  <label htmlFor="cr-name">Tên công ty *</label>
                  <input
                    id="cr-name"
                    className="input"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="cr-tax">Mã số thuế *</label>
                  <input
                    id="cr-tax"
                    className="input"
                    value={form.taxCode}
                    onChange={(e) => setForm({ ...form, taxCode: e.target.value })}
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="cr-industry">Lĩnh vực *</label>
                  <select
                    id="cr-industry"
                    className="input"
                    value={form.industry}
                    onChange={(e) => setForm({ ...form, industry: e.target.value })}
                  >
                    {INDUSTRIES.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="cr-size">Quy mô *</label>
                  <select
                    id="cr-size"
                    className="input"
                    value={form.size}
                    onChange={(e) => setForm({ ...form, size: e.target.value })}
                  >
                    {COMPANY_SIZES.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="cr-type">Loại công ty</label>
                  <select
                    id="cr-type"
                    className="input"
                    value={form.companyType}
                    onChange={(e) => setForm({ ...form, companyType: e.target.value })}
                  >
                    {COMPANY_TYPES.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="cr-website">Website</label>
                  <input
                    id="cr-website"
                    className="input"
                    type="url"
                    value={form.website}
                    onChange={(e) => setForm({ ...form, website: e.target.value })}
                  />
                </div>
                <div className="field">
                  <label htmlFor="cr-year">Năm thành lập</label>
                  <input
                    id="cr-year"
                    className="input"
                    value={form.foundedYear}
                    onChange={(e) => setForm({ ...form, foundedYear: e.target.value })}
                  />
                </div>
                <div className="field span2">
                  <label htmlFor="cr-hq">Địa chỉ trụ sở *</label>
                  <input
                    id="cr-hq"
                    className="input"
                    value={form.headquarters}
                    onChange={(e) => setForm({ ...form, headquarters: e.target.value })}
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="cr-email">Email liên hệ *</label>
                  <input
                    id="cr-email"
                    className="input"
                    type="email"
                    value={form.contactEmail}
                    onChange={(e) => setForm({ ...form, contactEmail: e.target.value })}
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="cr-phone">Số điện thoại *</label>
                  <input
                    id="cr-phone"
                    className="input"
                    value={form.contactPhone}
                    onChange={(e) => setForm({ ...form, contactPhone: e.target.value })}
                    required
                  />
                </div>
                <div className="field span2">
                  <label htmlFor="cr-bio">Giới thiệu ngắn</label>
                  <textarea
                    id="cr-bio"
                    className="input"
                    value={form.shortBio}
                    onChange={(e) => setForm({ ...form, shortBio: e.target.value })}
                  />
                </div>
              </div>
            </section>

            <section className="card stack" style={{ gap: 16, padding: 28 }}>
              <h3 style={{ fontSize: 18 }}>Tài liệu xác minh</h3>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="cr-logo-file" className="lbl">Logo</label>
                  <div
                    style={{
                      border: "1.5px dashed var(--line-strong)",
                      padding: 18,
                      display: "flex",
                      gap: 14,
                      alignItems: "center",
                    }}
                  >
                    <span className="logo">{initials(form.name) || "CT"}</span>
                    <div>
                      <p className="small" style={{ fontWeight: 600 }}>
                        {form.logoFileName || "Chưa chọn tệp"}
                      </p>
                      <label htmlFor="cr-logo-file" className="btn btn-link tiny" style={{ cursor: "pointer" }}>
                        Đổi ảnh
                      </label>
                      <input
                        id="cr-logo-file"
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        onChange={handleLogoChange}
                        style={{ display: "none" }}
                      />
                    </div>
                  </div>
                </div>

                <div className="field">
                  <label htmlFor="cr-license-file" className="lbl">Giấy phép kinh doanh *</label>
                  <div
                    style={{
                      border: "1.5px dashed var(--line-strong)",
                      padding: 18,
                      display: "flex",
                      flexDirection: "column",
                      gap: 6,
                      alignItems: "flex-start",
                    }}
                  >
                    <p className="small" style={{ fontWeight: 600 }}>
                      {form.licenseFileName
                        ? `${form.licenseFileName}${form.licenseFileMeta ? ` · ${form.licenseFileMeta}` : ""}`
                        : "Chưa chọn tệp"}
                    </p>
                    <label htmlFor="cr-license-file" className="btn btn-link tiny" style={{ cursor: "pointer" }}>
                      {form.licenseFileName ? "Chọn tệp khác" : "Chọn tệp"}
                    </label>
                    <input
                      id="cr-license-file"
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png"
                      onChange={handleLicenseChange}
                      style={{ display: "none" }}
                    />
                    <span className="help">PDF/JPG, tối đa 10 MB. Chỉ quản trị viên xem được.</span>
                  </div>
                </div>
              </div>

              <label className="check small">
                <input
                  type="checkbox"
                  checked={form.confirmed}
                  onChange={(e) => setForm({ ...form, confirmed: e.target.checked })}
                />
                Tôi xác nhận thông tin trên là chính xác và tôi có quyền đại diện công ty.
              </label>
            </section>

            <div className="row" style={{ justifyContent: "flex-end" }}>
              <button
                type="button"
                className="btn btn-g"
                disabled={busy}
                onClick={() => void handleSaveDraft()}
              >
                Lưu nháp
              </button>
              <button type="submit" className="btn btn-p" disabled={busy}>
                {busy ? "Đang gửi…" : "Gửi đăng ký"}
              </button>
            </div>
          </form>

          <aside style={{ flex: "1 1 320px", maxWidth: 400, display: "flex", flexDirection: "column", gap: 16 }}>
            <section className="card stack" style={{ gap: 12 }}>
              <h4>Quy trình duyệt</h4>
              <ol
                style={{
                  margin: 0,
                  paddingLeft: 20,
                  display: "grid",
                  gap: 8,
                  fontSize: 14,
                  color: "var(--ink-soft)",
                }}
              >
                <li>
                  Gửi hồ sơ → trạng thái <strong>Chờ duyệt</strong>
                </li>
                <li>Quản trị viên kiểm tra giấy phép</li>
                <li>Được duyệt → đăng tin, mời thành viên</li>
              </ol>
            </section>

            <p className="kicker" style={{ color: "var(--muted)" }}>
              Trạng thái hồ sơ hiện tại
            </p>

            {company.status === "PENDING" ? (
              <section
                className="card stack"
                style={{ gap: 8, background: "var(--gold-soft)", borderColor: "var(--gold)" }}
              >
                <span className="badge b-gold" style={{ alignSelf: "flex-start" }}>
                  Chờ duyệt · PENDING
                </span>
                <p className="small" style={{ color: "var(--gold)" }}>
                  Hồ sơ đã gửi {company.submittedAt}. Trong lúc chờ, bạn có thể soạn tin ở dạng nháp nhưng chưa đăng được.
                </p>
              </section>
            ) : company.status === "REJECTED" ? (
              <section
                className="card stack"
                style={{ gap: 8, background: "var(--danger-soft)", borderColor: "var(--danger)" }}
              >
                <span className="badge b-danger" style={{ alignSelf: "flex-start" }}>
                  Bị từ chối · REJECTED
                </span>
                <p className="small" style={{ color: "var(--danger)" }}>
                  <strong>Lý do:</strong>{" "}
                  {company.rejectionReason ?? "Giấy phép kinh doanh không rõ nét. Vui lòng tải lại bản scan."}
                </p>
                <button
                  type="button"
                  className="btn btn-g btn-sm"
                  style={{ alignSelf: "flex-start" }}
                  onClick={() => toast("Hãy cập nhật thông tin hoặc tệp đính kèm bên trái rồi bấm Gửi đăng ký.")}
                >
                  Sửa và gửi lại
                </button>
              </section>
            ) : (
              <section
                className="card stack"
                style={{ gap: 8, background: "var(--ok-soft)", borderColor: "var(--ok)" }}
              >
                <span className="badge b-ok" style={{ alignSelf: "flex-start" }}>
                  Đã duyệt · ACTIVE
                </span>
                <p className="small" style={{ color: "var(--ok)" }}>
                  Công ty đã được duyệt.{" "}
                  <Link to="/recruiter" style={{ fontWeight: 700, textDecoration: "underline" }}>
                    Vào trang quản lý
                  </Link>
                </p>
              </section>
            )}

          </aside>
        </div>
      )}
    </RecruiterLayout>
  );
}
