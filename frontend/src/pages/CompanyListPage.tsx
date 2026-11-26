import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { EmptyNote, Pager, SiteHeader } from "../components/common";
import { listCompanies, type CompanyDto } from "../api/mock/companyMock";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

type CompanySort = "jobs" | "newest" | "name";
const PAGE_SIZE = 9;

/** Màn P04 · Danh sách công ty IT công khai (design canvas CompanyList.dc.html). */
export function CompanyListPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [companies, setCompanies] = useState<CompanyDto[] | null>(null);
  const [keyword, setKeyword] = useState("");
  const [city, setCity] = useState("all");
  const [industry, setIndustry] = useState("all");
  const [sort, setSort] = useState<CompanySort>("jobs");
  const [page, setPage] = useState(0);

  useEffect(() => {
    listCompanies({ status: "ACTIVE" })
      .then(setCompanies)
      .catch((e: unknown) => {
        setCompanies([]);
        toast(e instanceof Error ? e.message : "Không tải được danh sách công ty.");
      });
  }, [toast]);

  const cities = useMemo(
    () => [...new Set((companies ?? []).map((c) => c.city).filter(Boolean))].sort(),
    [companies]
  );

  const industries = useMemo(
    () => [...new Set((companies ?? []).map((c) => c.industry).filter(Boolean))].sort(),
    [companies]
  );

  const filtered = useMemo(() => {
    const needle = keyword.trim().toLowerCase();
    const list = (companies ?? []).filter((c) => {
      if (city !== "all" && c.city !== city) return false;
      if (industry !== "all" && c.industry !== industry) return false;
      if (needle) {
        const hay = `${c.name} ${c.tagline} ${c.industry} ${c.skills.join(" ")}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      return true;
    });

    return [...list].sort((a, b) => {
      if (sort === "jobs") return b.openJobsCount - a.openJobsCount;
      if (sort === "newest") return b.submittedAt.localeCompare(a.submittedAt);
      return a.name.localeCompare(b.name, "vi");
    });
  }, [companies, keyword, city, industry, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const paged = useMemo(
    () => filtered.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE),
    [filtered, safePage]
  );

  const startIndex = filtered.length === 0 ? 0 : safePage * PAGE_SIZE + 1;
  const endIndex = Math.min(filtered.length, (safePage + 1) * PAGE_SIZE);
  const hasFilters = Boolean(keyword.trim()) || city !== "all" || industry !== "all";

  function onSearchSubmit(e: FormEvent) {
    e.preventDefault();
    setPage(0);
  }

  function clearFilters() {
    setKeyword("");
    setCity("all");
    setIndustry("all");
    setPage(0);
  }

  return (
    <>
      <SiteHeader mode={user?.role === "CANDIDATE" ? "candidate" : "public"} active="companies" />

      <section style={{ padding: "40px 0 24px", borderBottom: "1px solid var(--line)" }}>
        <div className="wrap" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <p className="kicker">{companies ? `${companies.length} công ty đã xác minh` : "Danh bạ công ty IT"}</p>
          <h1 style={{ fontSize: 40 }}>Tìm công ty IT phù hợp với bạn</h1>
          <form className="search" role="search" style={{ maxWidth: 880 }} onSubmit={onSearchSubmit}>
            <label className="seg" style={{ flex: "3 1 300px" }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" strokeWidth="2" aria-hidden="true">
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" />
              </svg>
              <input
                type="search"
                placeholder="Tên công ty"
                aria-label="Tên công ty"
                value={keyword}
                onChange={(e) => {
                  setKeyword(e.target.value);
                  setPage(0);
                }}
              />
            </label>
            <label className="seg" style={{ flex: "1 1 180px" }}>
              <select
                aria-label="Thành phố"
                value={city}
                onChange={(e) => {
                  setCity(e.target.value);
                  setPage(0);
                }}
              >
                <option value="all">Tất cả thành phố</option>
                {cities.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>
            <label className="seg" style={{ flex: "1 1 180px" }}>
              <select
                aria-label="Ngành"
                value={industry}
                onChange={(e) => {
                  setIndustry(e.target.value);
                  setPage(0);
                }}
              >
                <option value="all">Tất cả ngành</option>
                {industries.map((ind) => (
                  <option key={ind} value={ind}>{ind}</option>
                ))}
              </select>
            </label>
            <button type="submit" className="btn btn-p">Tìm</button>
          </form>
        </div>
      </section>

      <section style={{ padding: "28px 0 64px" }}>
        <div className="wrap" style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div className="between">
            <p className="muted">
              {filtered.length === 0
                ? "0 công ty phù hợp"
                : `Hiển thị ${startIndex}–${endIndex} trong ${filtered.length} công ty`}
            </p>
            <div className="row" style={{ gap: 12 }}>
              {hasFilters ? (
                <button type="button" className="btn btn-link small" onClick={clearFilters}>
                  Xoá bộ lọc
                </button>
              ) : null}
              <label className="row small" style={{ gap: 8 }}>
                <span className="muted">Sắp xếp</span>
                <select
                  className="input"
                  aria-label="Sắp xếp công ty"
                  style={{ height: 38, width: "auto" }}
                  value={sort}
                  onChange={(e) => {
                    setSort(e.target.value as CompanySort);
                    setPage(0);
                  }}
                >
                  <option value="jobs">Nhiều việc nhất</option>
                  <option value="newest">Mới tham gia</option>
                  <option value="name">Tên A–Z</option>
                </select>
              </label>
            </div>
          </div>

          {companies === null ? (
            <p className="muted">Đang tải danh sách công ty…</p>
          ) : paged.length === 0 ? (
            <EmptyNote>
              Không tìm thấy công ty khớp bộ lọc hiện tại.{" "}
              {hasFilters ? (
                <button type="button" className="btn btn-link small" onClick={clearFilters}>
                  Xem tất cả công ty
                </button>
              ) : null}
            </EmptyNote>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 340px), 1fr))", gap: 16 }}>
              {paged.map((c) => (
                <Link
                  key={c.id}
                  to={`/companies/${c.id}`}
                  className="card"
                  style={{ display: "flex", flexDirection: "column", gap: 14, padding: 0, overflow: "hidden" }}
                >
                  <div style={{ height: 64, background: "var(--sky)", borderBottom: "1px solid var(--line)" }} />
                  <div style={{ padding: "0 20px 20px", marginTop: -40, display: "flex", flexDirection: "column", gap: 12, flex: 1 }}>
                    <span className="logo" style={{ background: "var(--paper)" }}>{c.logo}</span>
                    <div>
                      <p className="disp" style={{ fontSize: 19 }}>{c.name}</p>
                      <p className="small muted">{c.industry} · {c.size}</p>
                    </div>
                    <p className="small" style={{ color: "var(--ink-soft)" }}>{c.tagline}</p>
                    <div className="row" style={{ gap: 6 }}>
                      {c.skills.slice(0, 4).map((s) => (
                        <span key={s} className="tag">{s}</span>
                      ))}
                    </div>
                    <div className="between small" style={{ borderTop: "1px solid var(--line)", paddingTop: 12, marginTop: "auto" }}>
                      <span className="muted">{c.city}</span>
                      <span style={{ fontWeight: 650, color: "var(--brand)" }}>{c.openJobsCount} việc đang tuyển</span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}

          <Pager
            data={
              companies
                ? {
                    content: paged,
                    pageNumber: safePage,
                    pageSize: PAGE_SIZE,
                    totalElements: filtered.length,
                    totalPages,
                    last: safePage >= totalPages - 1,
                  }
                : null
            }
            onPage={setPage}
          />
        </div>
      </section>
    </>
  );
}
