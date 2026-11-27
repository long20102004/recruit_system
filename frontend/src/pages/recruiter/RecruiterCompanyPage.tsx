import { useEffect, useState, type ChangeEvent, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import { RecruiterLayout } from "../../components/common";
import {
  getCompanyProfile,
  updateCompanyProfile,
  uploadCompanyFile,
  type CompanyProfile,
  type CompanyProfileUpdateInput,
  type CompanyVerificationStatus,
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
const OVERTIME_OPTIONS = ["Không OT", "Có OT", "Linh hoạt"];

function statusBadge(status: CompanyVerificationStatus): { label: string; cls: string } {
  switch (status) {
    case "ACTIVE":
      return { label: "Đã duyệt", cls: "badge b-ok" };
    case "REJECTED":
      return { label: "Bị từ chối", cls: "badge b-danger" };
    default:
      return { label: "Chờ duyệt", cls: "badge b-gold" };
  }
}

function toUpdateInput(c: CompanyProfile): CompanyProfileUpdateInput {
  return {
    displayName: c.displayName,
    industry: c.industry,
    size: c.size,
    companyType: c.companyType,
    website: c.website,
    workingDays: c.workingDays,
    overtimePolicy: c.overtimePolicy,
    officeAddress: c.officeAddress,
    description: c.description,
    whyWorkHere: c.whyWorkHere,
    techStack: [...c.techStack],
    logoFileName: c.logoFileName,
    coverFileName: c.coverFileName,
  };
}

export function RecruiterCompanyPage() {
  const { toast } = useToast();
  const [company, setCompany] = useState<CompanyProfile | null>(null);
  const [form, setForm] = useState<CompanyProfileUpdateInput | null>(null);
  const [newTag, setNewTag] = useState("");
  const [addingTag, setAddingTag] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getCompanyProfile()
      .then((data) => {
        setCompany(data);
        setForm(toUpdateInput(data));
      })
      .catch((e) => toast(e instanceof Error ? e.message : "Không tải được hồ sơ công ty"));
  }, [toast]);

  function addTag() {
    if (!form) return;
    const cleaned = newTag.trim();
    if (!cleaned) {
      setAddingTag(false);
      return;
    }
    if (form.techStack.some((t) => t.toLowerCase() === cleaned.toLowerCase())) {
      toast("Công nghệ này đã có trong danh sách.");
      return;
    }
    setForm({ ...form, techStack: [...form.techStack, cleaned] });
    setNewTag("");
    setAddingTag(false);
  }

  function removeTag(tag: string) {
    if (!form) return;
    setForm({ ...form, techStack: form.techStack.filter((t) => t !== tag) });
  }

  function handleTagKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      e.preventDefault();
      addTag();
    } else if (e.key === "Escape") {
      setNewTag("");
      setAddingTag(false);
    }
  }

  /** Ảnh tải thẳng lên R2 khi chọn; form chỉ cập nhật tên file để lần lưu sau không ghi đè. */
  async function uploadImage(kind: "logo" | "cover", e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || !form) return;
    try {
      const updated = await uploadCompanyFile(kind, file);
      setCompany(updated);
      setForm((f) => (f ? { ...f, logoFileName: updated.logoFileName, coverFileName: updated.coverFileName } : f));
      toast(kind === "logo" ? "Đã cập nhật logo." : "Đã cập nhật ảnh bìa.");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Không tải được ảnh.");
    }
  }

  const handleCoverChange = (e: ChangeEvent<HTMLInputElement>) => void uploadImage("cover", e);
  const handleLogoChange = (e: ChangeEvent<HTMLInputElement>) => void uploadImage("logo", e);

  async function handleSave() {
    if (!form) return;
    setSaving(true);
    try {
      const updated = await updateCompanyProfile(form);
      setCompany(updated);
      setForm(toUpdateInput(updated));
      toast("Đã lưu thay đổi hồ sơ công ty.");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Lưu hồ sơ thất bại");
    } finally {
      setSaving(false);
    }
  }

  const badge = statusBadge(company?.status ?? "ACTIVE");

  return (
    <RecruiterLayout active="company">
      {!company || !form ? (
        <p className="muted">Đang tải hồ sơ công ty…</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div className="page-head" style={{ marginBottom: 0 }}>
            <div>
              <div className="row">
                <h1 style={{ fontSize: 32 }}>Hồ sơ công ty</h1>
                <span className={badge.cls}>{badge.label}</span>
              </div>
              <p className="muted">
                Thông tin hiển thị trên trang công ty công khai. Chỉ Owner và Manager được sửa.
              </p>
            </div>
            <div className="row">
              <Link to="/jobs" className="btn btn-g">
                Xem trang công khai
              </Link>
              <button
                type="button"
                className="btn btn-p"
                disabled={saving}
                onClick={() => void handleSave()}
              >
                {saving ? "Đang lưu…" : "Lưu thay đổi"}
              </button>
            </div>
          </div>

          <section className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div
              style={{
                height: 140,
                background: company.coverUrl
                  ? `center / cover no-repeat url("${company.coverUrl}")`
                  : "var(--sky)",
                borderBottom: "1px solid var(--line)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-end",
                padding: 12,
              }}
            >
              <span className="tiny muted">Ảnh bìa: {form.coverFileName}</span>
              <label htmlFor="cp-cover" className="btn btn-g btn-sm" style={{ cursor: "pointer" }}>
                Đổi ảnh bìa
              </label>
              <input
                id="cp-cover"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={handleCoverChange}
                style={{ display: "none" }}
              />
            </div>
            <div
              style={{
                padding: "0 24px 24px",
                display: "flex",
                gap: 18,
                alignItems: "flex-end",
                marginTop: -44,
                flexWrap: "wrap",
              }}
            >
              {company.logoUrl ? (
                <img
                  className="logo logo-lg"
                  src={company.logoUrl}
                  alt={`Logo ${form.displayName}`}
                  style={{ background: "var(--paper)", objectFit: "contain" }}
                />
              ) : (
                <span className="logo logo-lg" style={{ background: "var(--paper)" }}>
                  {initials(form.displayName) || "LF"}
                </span>
              )}
              <div style={{ flex: 1, minWidth: 200, paddingBottom: 6 }}>
                <p className="disp" style={{ fontSize: 24 }}>
                  {form.displayName}
                </p>
                <p className="small muted">
                  Tạo bởi {company.createdBy}
                  {company.approvedAt ? ` · Duyệt ngày ${company.approvedAt}` : ""}
                  {form.logoFileName ? ` · Logo: ${form.logoFileName}` : ""}
                </p>
              </div>
              <label htmlFor="cp-logo" className="btn btn-g btn-sm" style={{ cursor: "pointer" }}>
                Đổi logo
              </label>
              <input
                id="cp-logo"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={handleLogoChange}
                style={{ display: "none" }}
              />
            </div>
          </section>

          <section className="card stack" style={{ gap: 16, padding: 26 }}>
            <h3 style={{ fontSize: 18 }}>Thông tin cơ bản</h3>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="cp-display-name">Tên hiển thị</label>
                <input
                  id="cp-display-name"
                  className="input"
                  value={form.displayName}
                  onChange={(e) => setForm({ ...form, displayName: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="cp-tax-code">Mã số thuế</label>
                <input
                  id="cp-tax-code"
                  className="input"
                  value={company.taxCode}
                  disabled
                  style={{ background: "var(--bg)", color: "var(--muted)" }}
                />
                <span className="help">Đổi MST cần quản trị viên duyệt lại.</span>
              </div>
              <div className="field">
                <label htmlFor="cp-industry">Lĩnh vực</label>
                <select
                  id="cp-industry"
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
                <label htmlFor="cp-size">Quy mô</label>
                <select
                  id="cp-size"
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
                <label htmlFor="cp-type">Loại công ty</label>
                <select
                  id="cp-type"
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
                <label htmlFor="cp-website">Website</label>
                <input
                  id="cp-website"
                  className="input"
                  type="url"
                  value={form.website}
                  onChange={(e) => setForm({ ...form, website: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="cp-days">Ngày làm việc</label>
                <input
                  id="cp-days"
                  className="input"
                  value={form.workingDays}
                  onChange={(e) => setForm({ ...form, workingDays: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="cp-ot">Làm thêm giờ</label>
                <select
                  id="cp-ot"
                  className="input"
                  value={form.overtimePolicy}
                  onChange={(e) => setForm({ ...form, overtimePolicy: e.target.value })}
                >
                  {OVERTIME_OPTIONS.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field span2">
                <label htmlFor="cp-address">Địa chỉ văn phòng</label>
                <input
                  id="cp-address"
                  className="input"
                  value={form.officeAddress}
                  onChange={(e) => setForm({ ...form, officeAddress: e.target.value })}
                />
              </div>
            </div>
          </section>

          <section className="card stack" style={{ gap: 16, padding: 26 }}>
            <h3 style={{ fontSize: 18 }}>Giới thiệu</h3>
            <div className="field">
              <label htmlFor="cp-desc">Giới thiệu công ty</label>
              <textarea
                id="cp-desc"
                className="input"
                style={{ minHeight: 140 }}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="cp-why">Vì sao nên làm việc tại đây</label>
              <textarea
                id="cp-why"
                className="input"
                value={form.whyWorkHere}
                onChange={(e) => setForm({ ...form, whyWorkHere: e.target.value })}
              />
            </div>
            <div className="field">
              <span className="lbl">Chuyên môn / công nghệ</span>
              <div className="row" style={{ gap: 6 }}>
                {form.techStack.map((tag) => (
                  <button
                    key={tag}
                    type="button"
                    className="tag tag-on"
                    aria-label={`Xoá ${tag}`}
                    onClick={() => removeTag(tag)}
                  >
                    {tag} ×
                  </button>
                ))}
                {addingTag ? (
                  <span className="row" style={{ gap: 6 }}>
                    <input
                      type="text"
                      className="input"
                      aria-label="Nhập tên công nghệ"
                      placeholder="VD: Docker"
                      value={newTag}
                      onChange={(e) => setNewTag(e.target.value)}
                      onKeyDown={handleTagKeyDown}
                      style={{ height: 32, width: 150, padding: "0 10px" }}
                      autoFocus
                    />
                    <button type="button" className="btn btn-p btn-sm" onClick={addTag}>
                      Thêm
                    </button>
                    <button
                      type="button"
                      className="btn btn-g btn-sm"
                      onClick={() => {
                        setNewTag("");
                        setAddingTag(false);
                      }}
                    >
                      Huỷ
                    </button>
                  </span>
                ) : (
                  <button
                    type="button"
                    className="tag"
                    style={{ borderStyle: "dashed" }}
                    onClick={() => setAddingTag(true)}
                  >
                    + Thêm
                  </button>
                )}
              </div>
            </div>
          </section>
        </div>
      )}
    </RecruiterLayout>
  );
}
