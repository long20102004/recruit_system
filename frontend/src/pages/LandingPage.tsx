import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button, EmptyNote, JobCard, SiteHeader } from "../components/common";
import { MAX_PAGE_SIZE, jobsApi, type JobDto } from "../api/client";
import { useToast } from "../context/ToastContext";
import { mapJob } from "../utils/mappers";
import { loginPath } from "../utils/account";

const CANDIDATE_STEPS = [
  {
    n: "1",
    t: "Tải CV PDF",
    d: "AI trích xuất học vấn, kinh nghiệm, kỹ năng; bạn chỉnh lại rồi lưu.",
  },
  {
    n: "2",
    t: "Xem việc phù hợp",
    d: "Mỗi tin có điểm phù hợp và giải thích kỹ năng còn thiếu.",
  },
  {
    n: "3",
    t: "Luyện phỏng vấn",
    d: "Câu hỏi theo JD, chấm điểm từng câu trả lời.",
  },
];

function countBy(items: string[], limit = 4): Array<{ label: string; count: number }> {
  const counts = new Map<string, number>();
  for (const item of items) {
    const key = item.trim();
    if (!key) continue;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([label, count]) => ({ label, count }));
}

export function LandingPage() {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState("");
  const [city, setCity] = useState("all");
  const [remoteJobs, setRemoteJobs] = useState<JobDto[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    jobsApi
      .list({ size: MAX_PAGE_SIZE })
      .then((page) => {
        if (active) setRemoteJobs(page.content);
      })
      .catch(() => {
        if (active) toast("Không tải được danh sách việc làm. Thử lại sau.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [toast]);

  const publishedDtos = useMemo(
    () => remoteJobs.filter((j) => (j.status ?? "").toUpperCase() === "PUBLISHED"),
    [remoteJobs]
  );

  const publishedJobs = useMemo(
    () => publishedDtos.map(mapJob),
    [publishedDtos]
  );

  const featuredJobs = useMemo(() => {
    const sorted = [...publishedDtos].sort((a, b) => {
      if (a.hot !== b.hot) return Number(b.hot) - Number(a.hot);
      const ta = a.postedAt ? Date.parse(a.postedAt) || 0 : 0;
      const tb = b.postedAt ? Date.parse(b.postedAt) || 0 : 0;
      return tb - ta;
    });
    return sorted.slice(0, 6).map(mapJob);
  }, [publishedDtos]);

  const cities = useMemo(
    () => [...new Set(publishedJobs.map((j) => j.city).filter(Boolean))].sort(),
    [publishedJobs]
  );

  const popularKeywords = useMemo(() => {
    const counts = new Map<string, number>();
    for (const j of publishedJobs) {
      for (const skill of j.requiredSkills) {
        counts.set(skill, (counts.get(skill) ?? 0) + 1);
      }
    }
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([k]) => k);
  }, [publishedJobs]);

  const cityCounts = useMemo(
    () => countBy(publishedJobs.map((j) => j.city)),
    [publishedJobs]
  );
  const levelCounts = useMemo(
    () => countBy(publishedJobs.map((j) => j.level)),
    [publishedJobs]
  );
  const workTypeCounts = useMemo(
    () => countBy(publishedJobs.map((j) => j.workType)),
    [publishedJobs]
  );

  function handleSearch(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const params = new URLSearchParams();
    const kw = keyword.trim();
    if (kw) params.set("keyword", kw);
    if (city !== "all") params.set("city", city);
    const query = params.toString();
    navigate(query ? `/jobs?${query}` : "/jobs");
  }

  return (
    <>
      <SiteHeader mode="public" active="jobs" />

      <main>
        <section style={{ padding: "64px 0 40px", borderBottom: "1px solid var(--line)" }}>
          <div className="wrap" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <p className="kicker">
              {loading ? "Đang tải việc làm IT…" : `${publishedJobs.length} việc làm IT đang tuyển`}
            </p>
            <h1 style={{ maxWidth: 820, fontSize: 52 }}>
              Việc làm IT hợp với bạn, xếp theo kỹ năng và CV.
            </h1>
            <p className="muted" style={{ maxWidth: 640, fontSize: 17 }}>
              Tìm theo vị trí, kỹ năng hoặc công ty. Tải CV lên để xem mức phù hợp và luyện phỏng vấn cho đúng tin bạn
              ứng tuyển.
            </p>
            <form className="search" role="search" style={{ marginTop: 8 }} onSubmit={handleSearch}>
              <label className="seg" style={{ flex: "3 1 320px" }}>
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--muted)"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <circle cx="11" cy="11" r="7" />
                  <path d="m20 20-3.5-3.5" />
                </svg>
                <input
                  type="search"
                  placeholder="Vị trí, kỹ năng, công ty…"
                  aria-label="Từ khóa"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                />
              </label>
              <label className="seg" style={{ flex: "1 1 200px" }}>
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--muted)"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z" />
                  <circle cx="12" cy="9.5" r="2.5" />
                </svg>
                <select aria-label="Thành phố" value={city} onChange={(e) => setCity(e.target.value)}>
                  <option value="all">Tất cả thành phố</option>
                  {cities.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>
              <button type="submit" className="btn btn-p">
                Tìm việc
              </button>
            </form>
            {popularKeywords.length > 0 ? (
              <div className="row" style={{ gap: 8 }}>
                <span className="small muted" style={{ marginRight: 4 }}>
                  Từ khóa phổ biến:
                </span>
                {popularKeywords.map((k) => (
                  <Link key={k} to={`/jobs?keyword=${encodeURIComponent(k)}`} className="tag">
                    {k}
                  </Link>
                ))}
              </div>
            ) : null}
          </div>
        </section>

        <section style={{ padding: "48px 0" }}>
          <div className="wrap" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            <div className="between">
              <div>
                <p className="kicker">Mới cập nhật</p>
                <h2>Việc làm nổi bật</h2>
              </div>
              <Link to="/jobs" className="btn btn-link">
                Xem tất cả việc làm →
              </Link>
            </div>
            {loading ? (
              <p className="muted small">Đang tải việc làm nổi bật…</p>
            ) : featuredJobs.length === 0 ? (
              <EmptyNote>Hiện chưa có việc làm đang tuyển.</EmptyNote>
            ) : (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 520px), 1fr))",
                  gap: 14,
                }}
              >
                {featuredJobs.map((job, i) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    delayMs={i * 40}
                    onClick={() => navigate(loginPath(`/candidate/jobs/${job.id}`))}
                  />
                ))}
              </div>
            )}
          </div>
        </section>

        <section style={{ padding: "8px 0 48px" }}>
          <div className="wrap">
            <div
              className="card"
              style={{
                display: "flex",
                gap: 32,
                alignItems: "center",
                flexWrap: "wrap",
                padding: 32,
                background: "var(--brand-soft)",
                borderColor: "var(--line)",
              }}
            >
              <div style={{ flex: "1 1 420px", display: "flex", flexDirection: "column", gap: 10 }}>
                <p className="kicker">Dành cho ứng viên</p>
                <h2>Tải CV một lần, xem mức phù hợp với mọi tin.</h2>
                <p style={{ color: "var(--ink-soft)" }}>
                  AI đọc CV PDF của bạn, điền sẵn hồ sơ, rồi chấm mức khớp kỹ năng và kinh nghiệm với từng tin tuyển
                  dụng.
                </p>
              </div>
              <ol
                style={{
                  flex: "1 1 380px",
                  listStyle: "none",
                  margin: 0,
                  padding: 0,
                  display: "grid",
                  gap: 14,
                }}
              >
                {CANDIDATE_STEPS.map((s) => (
                  <li key={s.n} style={{ display: "flex", gap: 14, alignItems: "flex-start" }}>
                    <span className="disp" style={{ fontSize: 22, color: "var(--brand)", width: 28 }}>
                      {s.n}
                    </span>
                    <div>
                      <p style={{ fontWeight: 650 }}>{s.t}</p>
                      <p className="small muted">{s.d}</p>
                    </div>
                  </li>
                ))}
              </ol>
              <Button variant="primary" to="/register">
                Tạo tài khoản miễn phí
              </Button>
            </div>
          </div>
        </section>

        {publishedJobs.length > 0 ? (
          <section style={{ padding: "0 0 56px" }}>
            <div
              className="wrap"
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 300px), 1fr))",
                gap: 24,
              }}
            >
              <div className="card-flat">
                <p className="kicker">Theo thành phố</p>
                <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "grid", gap: 4 }}>
                  {cityCounts.map((item) => (
                    <li
                      key={item.label}
                      className="between"
                      style={{ padding: "8px 0", borderBottom: "1px solid var(--line)" }}
                    >
                      <Link to={`/jobs?city=${encodeURIComponent(item.label)}`} style={{ fontWeight: 600 }}>
                        {item.label}
                      </Link>
                      <span className="small muted">{item.count} việc</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="card-flat">
                <p className="kicker">Theo cấp bậc</p>
                <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "grid", gap: 4 }}>
                  {levelCounts.map((item) => (
                    <li
                      key={item.label}
                      className="between"
                      style={{ padding: "8px 0", borderBottom: "1px solid var(--line)" }}
                    >
                      <Link to={`/jobs?level=${encodeURIComponent(item.label)}`} style={{ fontWeight: 600 }}>
                        {item.label}
                      </Link>
                      <span className="small muted">{item.count} việc</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="card-flat">
                <p className="kicker">Theo hình thức</p>
                <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, display: "grid", gap: 4 }}>
                  {workTypeCounts.map((item) => (
                    <li
                      key={item.label}
                      className="between"
                      style={{ padding: "8px 0", borderBottom: "1px solid var(--line)" }}
                    >
                      <Link to={`/jobs?workType=${encodeURIComponent(item.label)}`} style={{ fontWeight: 600 }}>
                        {item.label}
                      </Link>
                      <span className="small muted">{item.count} việc</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        ) : null}

        <section style={{ background: "var(--ink)", color: "var(--bg)", padding: "56px 0" }}>
          <div className="wrap between" style={{ gap: 28 }}>
            <div style={{ maxWidth: 640, display: "flex", flexDirection: "column", gap: 10 }}>
              <p className="kicker" style={{ color: "var(--brand-soft)" }}>
                Dành cho nhà tuyển dụng
              </p>
              <h2 style={{ color: "var(--surface)" }}>
                Đăng tin, xếp hạng ứng viên bằng matching và xem kết quả phỏng vấn ở một nơi.
              </h2>
            </div>
            <div className="row">
              <Link
                to="/register"
                className="btn"
                style={{ background: "var(--surface)", color: "var(--ink)" }}
              >
                Đăng ký nhà tuyển dụng
              </Link>
              <Link
                to="/login"
                className="btn"
                style={{ borderColor: "var(--line-strong)", color: "var(--surface)" }}
              >
                Đăng nhập nhà tuyển dụng
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="foot">
        <div
          className="wrap"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 200px), 1fr))",
            gap: 28,
          }}
        >
          <div>
            <p className="disp" style={{ fontSize: 24, color: "var(--surface)", marginBottom: 10 }}>
              HireLens
            </p>
            <p style={{ color: "var(--line)", fontSize: 13.5 }}>
              Hệ thống tuyển dụng IT: trích xuất CV, matching CV–JD và luyện phỏng vấn.
            </p>
          </div>
          <div>
            <h4>Ứng viên</h4>
            <Link to="/jobs">Việc làm IT</Link>
            <Link to="/candidate/cv">CV của tôi</Link>
            <Link to="/candidate/matching">Việc phù hợp</Link>
            <Link to="/candidate/interview">Luyện phỏng vấn</Link>
          </div>
          <div>
            <h4>Nhà tuyển dụng</h4>
            <Link to="/register">Đăng ký tài khoản</Link>
            <Link to="/recruiter/jobs">Đăng tin</Link>
            <Link to="/recruiter/candidates">Quản lý ứng viên</Link>
          </div>
          <div>
            <h4>Tài khoản</h4>
            <Link to="/login">Đăng nhập</Link>
            <Link to="/register">Đăng ký</Link>
            <Link to="/forgot-password">Quên mật khẩu</Link>
          </div>
        </div>
        <div
          className="wrap"
          style={{
            borderTop: "1px solid var(--ink-soft)",
            marginTop: 32,
            paddingTop: 18,
            fontSize: 12.5,
            color: "var(--line)",
          }}
        >
          © 2026 HireLens · PTIT
        </div>
      </footer>
    </>
  );
}
