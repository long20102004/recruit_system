import { useMemo, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import {
  Button,
  Chip,
  ChipFilter,
  CompanyRow,
  DemoBanner,
  EmptyNote,
  FilterChips,
  HeroSearch,
  JobCard,
  JobList,
  LayoutFeed,
  Page,
  Panel,
  QuickLink,
  SearchBar,
  SectionHead,
  SidePanel,
  SiteHeader,
  SplitActions,
} from "./components/common";
import { ToastProvider, useToast } from "./context/ToastContext";
import { mockJobs, mockMatchingResults, mockMeta } from "./data/mockData";
import { filterJobs, jobById, matchForJob } from "./utils/jobs";
import { pct } from "./utils/format";

function PublicHomePage() {
  const { toast } = useToast();
  const [keyword, setKeyword] = useState("Java");
  const [city, setCity] = useState("TP. Hồ Chí Minh");
  const [nearOnly, setNearOnly] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const jobs = useMemo(() => {
    let list = filterJobs(mockJobs, { keyword, city, nearOnly });
    if (!list.length && nearOnly) {
      list = filterJobs(mockJobs, { city, nearOnly: true, keyword: "" });
    }
    return list;
  }, [keyword, city, nearOnly]);

  const activeId =
    selectedId && jobs.some((j) => j.id === selectedId)
      ? selectedId
      : jobs[0]?.id ?? null;

  const selected = activeId ? jobById(mockJobs, activeId) : undefined;
  const match = activeId
    ? matchForJob(mockMatchingResults, activeId)
    : undefined;

  return (
    <>
      <DemoBanner>
        Bản mẫu giao diện ·{" "}
        <span>dữ liệu minh họa, chưa nối backend</span>
      </DemoBanner>
      <SiteHeader
        active="jobs"
        mode="public"
        userLocation={mockMeta.userLocation}
      />
      <Page>
        <HeroSearch
          kicker="Quận 1 · việc IT"
          title="Việc quanh bạn, xếp theo mức gần và mức hợp."
          lead="Đọc danh sách trước. CV, ghép nối và phỏng vấn nằm phía sau, khi bạn cần."
        >
          <SearchBar
            keyword={keyword}
            onKeywordChange={setKeyword}
            city={city}
            onCityChange={setCity}
            onSubmit={() => undefined}
          />
          <FilterChips>
            <ChipFilter active={nearOnly} onClick={() => setNearOnly(true)}>
              Gần bạn
            </ChipFilter>
            <ChipFilter active={!nearOnly} onClick={() => setNearOnly(false)}>
              Tất cả khu vực
            </ChipFilter>
            <ChipFilter
              onClick={() => {
                setKeyword("Intern");
              }}
            >
              Fresher / Intern
            </ChipFilter>
            <ChipFilter
              onClick={() => {
                setKeyword("Remote");
                setCity("Remote");
                setNearOnly(false);
              }}
            >
              Remote
            </ChipFilter>
            <ChipFilter onClick={() => setKeyword("NLP")}>NLP / AI</ChipFilter>
          </FilterChips>
        </HeroSearch>

        <LayoutFeed>
          <section>
            <SectionHead
              title={nearOnly ? "Việc làm gần bạn" : "Việc làm phù hợp tìm kiếm"}
              subtitle={
                nearOnly
                  ? `Dựa trên vị trí minh họa: ${mockMeta.userLocation}`
                  : "Kết quả theo từ khóa / khu vực đã chọn"
              }
              actions={<Chip tone="brand">{jobs.length} việc</Chip>}
            />
            <JobList>
              {jobs.length === 0 ? (
                <EmptyNote>
                  Không tìm thấy việc phù hợp. Thử bỏ lọc “Gần bạn” hoặc đổi từ
                  khóa.
                </EmptyNote>
              ) : (
                jobs.map((job, i) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    match={matchForJob(mockMatchingResults, job.id)}
                    showMatch
                    active={job.id === activeId}
                    delayMs={i * 40}
                    onClick={() => setSelectedId(job.id)}
                    onApply={() =>
                      toast("Demo: đăng nhập để ứng tuyển / matching")
                    }
                  />
                ))
              )}
            </JobList>
          </section>

          <SidePanel>
            <Panel>
              {selected ? (
                <>
                  <CompanyRow
                    logo={selected.logo}
                    logoColor={selected.logoColor}
                    title={selected.title}
                    meta={`${selected.company} · ${selected.location}`}
                  />
                  <div className="salary" style={{ marginBottom: ".75rem" }}>
                    {selected.salary}
                  </div>
                  <p style={{ margin: "0 0 .75rem" }}>{selected.description}</p>
                  <div style={{ marginBottom: ".75rem" }}>
                    {selected.requiredSkills.map((s) => (
                      <Chip key={s} tone="ok">
                        {s}
                      </Chip>
                    ))}
                    {selected.preferredSkills.map((s) => (
                      <Chip key={s} tone="accent">
                        {s}
                      </Chip>
                    ))}
                  </div>
                  {match ? (
                    <EmptyNote>
                      <strong>{pct(match.score)}% phù hợp (minh họa).</strong>
                      <br />
                      {match.reasons[0]}
                    </EmptyNote>
                  ) : (
                    <EmptyNote>
                      Chưa có điểm matching cho tin này. Đăng nhập để chạy Module
                      2.
                    </EmptyNote>
                  )}
                  <SplitActions>
                    <Button variant="primary" size="sm" to="/login">
                      Ứng tuyển demo
                    </Button>
                    <Button variant="ghost" size="sm" to="/login">
                      Phỏng vấn AI
                    </Button>
                  </SplitActions>
                </>
              ) : (
                <>
                  <h3>Chi tiết việc làm</h3>
                  <p className="muted">
                    Chọn một tin bên trái để xem mô tả, kỹ năng và mức phù hợp
                    (nếu có).
                  </p>
                </>
              )}
            </Panel>

            <Panel>
              <h3>Công cụ AI của đồ án</h3>
              <QuickLink to="/login" label="Phân tích CV (NER)" meta="Module 1" />
              <QuickLink
                to="/login"
                label="Ghép nối CV–Job"
                meta="Module 2"
              />
              <QuickLink
                to="/login"
                label="Phỏng vấn + BERTScore"
                meta="Module 3"
              />
              <p className="hint">
                Đăng nhập demo để xem đủ luồng ứng viên / nhà tuyển dụng.
              </p>
            </Panel>
          </SidePanel>
        </LayoutFeed>
      </Page>
    </>
  );
}

function LoginPlaceholder() {
  return (
    <>
      <DemoBanner>
        Prototype UI minh họa ·{" "}
        <span>Đăng nhập giả lập, không xác thực thật</span>
      </DemoBanner>
      <Page>
        <p className="muted">
          Trang đăng nhập sẽ dùng AuthPage / AuthPanel / RoleSwitch — component
          đã sẵn trong <code>components/common</code>.
        </p>
        <Button to="/">Quay lại danh sách việc</Button>
      </Page>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <Routes>
          <Route path="/" element={<PublicHomePage />} />
          <Route path="/login" element={<LoginPlaceholder />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </ToastProvider>
    </BrowserRouter>
  );
}
