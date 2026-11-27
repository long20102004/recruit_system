import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { SiteHeader, UploadZone } from "../../components/common";
import { cvsApi, type CandidateProfileDto, type CvFormDto } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { CvProfileEditor } from "./CvProfileEditor";
import { cleanProfile, normalizeProfile } from "./cvProfile";

/** Field "Kỹ năng suy ra" (đồ thị kỹ năng) không thuộc CandidateProfile nên vẫn lưu qua fields. */
const INFERRED_FIELD = "Kỹ năng suy ra";

function cleanLines(lines: string[] | undefined): string[] {
  return (lines ?? [])
    .flatMap((line) => line.split(/\r?\n/))
    .map((line) => line.trim())
    .filter(Boolean);
}

/** So sánh theo dữ liệu sẽ gửi lưu (bỏ dòng trống, khoảng trắng). */
function snapshot(profile: CandidateProfileDto, inferred: string[] | null) {
  return JSON.stringify([cleanProfile(profile), inferred ? cleanLines(inferred) : null]);
}

const EMPTY_FORM: CvFormDto = {
  cvId: null,
  title: null,
  main: false,
  fileName: null,
  parsingStatus: null,
  analyzed: false,
  fields: [],
  profile: null,
};

function UploadIcon() {
  return (
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.6" aria-hidden="true">
      <path d="M12 16V4M7 9l5-5 5 5" />
      <path d="M4 16v4h16v-4" />
    </svg>
  );
}

export function CandidateCvPage() {
  const { toast } = useToast();
  // ?cvId=X: sửa CV X; ?new=1: thêm CV mới; không có: CV chính (như trước khi có nhiều CV).
  const [params, setParams] = useSearchParams();
  const paramId = Number(params.get("cvId")) || null;
  const isNew = params.get("new") === "1" && paramId == null;
  const [cvId, setCvId] = useState<number | null>(paramId);
  const [title, setTitle] = useState<string | null>(null);
  const [isMain, setIsMain] = useState(false);
  /** Trang tự đổi query sau khi tạo CV mới: không tải lại form. */
  const selfNav = useRef(false);
  const [loaded, setLoaded] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [fileSize, setFileSize] = useState<number | null>(null);
  const [parsingStatus, setParsingStatus] = useState<string | null>(null);
  const [analyzed, setAnalyzed] = useState(false);
  const [profile, setProfile] = useState<CandidateProfileDto>(() => normalizeProfile(null));
  /** null khi cấu hình CV_FIELD không có "Kỹ năng suy ra". */
  const [inferred, setInferred] = useState<string[] | null>(null);
  const [savedSnapshot, setSavedSnapshot] = useState("");
  const [savedState, setSavedState] = useState<{ profile: CandidateProfileDto; inferred: string[] | null } | null>(null);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const previewRef = useRef<string | null>(null);

  function applyForm(form: CvFormDto, uploaded?: CandidateProfileDto | null) {
    const p = normalizeProfile(uploaded ?? form.profile);
    const inf = form.fields.find((f) => f.field === INFERRED_FIELD);
    const i = inf ? cleanLines(inf.values) : null;
    setProfile(p);
    setInferred(i);
    setSavedState({ profile: p, inferred: i });
    setSavedSnapshot(snapshot(p, i));
    setFileName(form.fileName);
    setParsingStatus(form.parsingStatus);
    setAnalyzed(form.analyzed);
    setCvId(form.cvId);
    setTitle(form.title);
    setIsMain(form.main);
  }

  useEffect(() => {
    if (selfNav.current) {
      selfNav.current = false;
      return;
    }
    setLoaded(false);
    setUploadError(null);
    setFileSize(null);
    setPreview(null);
    if (isNew) {
      applyForm(EMPTY_FORM);
      setLoaded(true);
      return;
    }
    let alive = true;
    cvsApi
      .mine(paramId)
      .then((form) => {
        if (alive) applyForm(form);
      })
      .catch((e) => {
        if (alive) toast(e instanceof Error ? e.message : "Không tải được CV");
      })
      .finally(() => {
        if (alive) setLoaded(true);
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramId, isNew]);

  useEffect(() => () => {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
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
    try {
      // Điền form từ profile AI trả về; GET /api/cvs lấy thêm trạng thái file và "Kỹ năng suy ra".
      if (isNew && cvId == null) {
        const res = await cvsApi.uploadNew(file);
        const id = res.data?.cvId;
        if (id == null) throw new Error("Upload thất bại");
        applyForm(await cvsApi.mine(id), res.data?.profile ?? null);
        selfNav.current = true;
        setParams({ cvId: String(id) }, { replace: true });
      } else if (cvId != null) {
        const res = await cvsApi.reupload(cvId, file);
        applyForm(await cvsApi.mine(cvId), res.data?.profile ?? null);
      } else {
        const res = await cvsApi.upload(file);
        applyForm(await cvsApi.mine(), res.data ?? null);
      }
      setAnalyzed(false);
      toast("AI đã điền các mục hồ sơ. Hãy kiểm tra trước khi lưu.");
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Upload thất bại");
    } finally {
      setUploading(false);
    }
  }

  const dirty = useMemo(() => snapshot(profile, inferred) !== savedSnapshot, [profile, inferred, savedSnapshot]);
  const hasProfile = parsingStatus === "COMPLETED";
  const failed = parsingStatus === "FAILED" || uploadError != null;
  const isSaved = analyzed && !dirty;

  async function onSave() {
    setSaving(true);
    try {
      const form = await cvsApi.confirm({
        profile: cleanProfile(profile),
        fields: inferred ? [{ field: INFERRED_FIELD, values: cleanLines(inferred) }] : undefined,
      }, cvId);
      applyForm(form);
      toast("Đã lưu hồ sơ CV");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Lưu thất bại");
    } finally {
      setSaving(false);
    }
  }

  const stepDone = [
    !!fileName && !uploading,
    hasProfile && !uploading,
    isSaved && !uploading,
  ];
  const activeStep = stepDone.findIndex((d) => !d);
  const steps = ["Tải file PDF", "AI trích xuất", "Kiểm tra & lưu"];

  return (
    <>
      <SiteHeader active="cv" mode="candidate" />
      <main className="cvu">
        <div className="cvu-wrap">
          <h1>Tải CV lên và kiểm tra thông tin AI trích xuất</h1>
          <p className="cvu-muted">
            {isNew && cvId == null ? "CV mới" : title ?? "CV chính"}
            {isMain ? " · CV chính" : ""}
            {" · "}
            <Link to="/candidate/cvs">Tất cả CV của tôi</Link>
          </p>

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
                        {!isSaved
                          ? "Kiểm tra từng mục bên dưới rồi bấm “Lưu CV”."
                          : isMain
                            ? "Hồ sơ này đang được dùng để xếp hạng việc làm phù hợp."
                            : "CV này được gửi khi bạn chọn nó lúc ứng tuyển. Đặt làm CV chính để dùng cho gợi ý việc làm."}
                      </p>
                      {isSaved && isMain ? (
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
                    <div className="cvu-note cvu-small">
                      AI có thể đọc sai, nhất là số điện thoại, ngày tháng và tên trường. Hãy xem lại từng mục trước khi lưu.
                    </div>

                    <CvProfileEditor
                      profile={profile}
                      onChange={setProfile}
                      inferred={inferred}
                      onInferredChange={setInferred}
                    />

                    <div className="cvu-actions">
                      <button type="button" className="cvu-btn cvu-btn-g"
                        disabled={!dirty || saving}
                        onClick={() => {
                          if (savedState) {
                            setProfile(savedState.profile);
                            setInferred(savedState.inferred);
                          }
                        }}>
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
