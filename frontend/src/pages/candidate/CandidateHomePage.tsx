import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Chip,
  ChipFilter,
  CompanyRow,
  EmptyNote,
  FilterChips,
  HeroSearch,
  JobCard,
  JobList,
  LayoutFeed,
  Page,
  Panel,
  SearchBar,
  SectionHead,
  SidePanel,
  SiteHeader,
  SplitActions,
} from "../../components/common";
import {
  applicationsApi,
  cvsApi,
  jobsApi,
  matchingApi,
  type JobDto,
  type MatchDto,
} from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { mapJob, mapMatch } from "../../utils/mappers";
import { filterJobs, jobById, matchForJob } from "../../utils/jobs";
import { pct } from "../../utils/format";
import { Link } from "react-router-dom";

export function CandidateHomePage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [keyword, setKeyword] = useState("");
  const [city, setCity] = useState("TP. Hồ Chí Minh");
  const [mode, setMode] = useState<"near" | "match">("near");
  const [jobs, setJobs] = useState<JobDto[]>([]);
  const [matches, setMatches] = useState<MatchDto[]>([]);
  const [cvReady, setCvReady] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    jobsApi.list().then(setJobs).catch((e) => toast(e.message));
    cvsApi
      .mine()
      .then(async (form) => {
        const ready = form.analyzed;
        setCvReady(ready);
        if (!ready) {
          setMatches([]);
          return;
        }
        setMatches(await matchingApi.mine());
      })
      .catch(() => {
        setCvReady(false);
        setMatches([]);
      });
  }, [toast]);

  const mapped = useMemo(() => jobs.map(mapJob), [jobs]);
  const matchResults = useMemo(() => matches.map(mapMatch), [matches]);

  const list = useMemo(() => {
    if (mode === "match") {
      const byScore = [...matchResults].sort((a, b) => b.score - a.score);
      const ranked = byScore
        .map((m) => mapped.find((j) => j.id === m.jobId))
        .filter(Boolean) as ReturnType<typeof mapJob>[];
      if (ranked.length > 0 || !cvReady) return ranked;
      return mapped;
    }
    return filterJobs(mapped, { keyword, city });
  }, [mode, mapped, matchResults, keyword, city, cvReady]);

  const top = matchResults[0];
  const topJob = top ? mapped.find((j) => j.id === top.jobId) : undefined;
  const firstName = user?.fullName?.split(" ").slice(-1)[0] ?? "bạn";
  const activeId =
    selectedId && list.some((job) => job.id === selectedId)
      ? selectedId
      : list[0]?.id ?? null;
  const selected = activeId ? jobById(mapped, activeId) : undefined;
  const selectedMatch = activeId ? matchForJob(matchResults, activeId) : undefined;

  async function apply(jobId: string) {
    try {
      await applicationsApi.apply(Number(jobId));
      toast("Đã nộp hồ sơ ứng tuyển");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Ứng tuyển thất bại");
    }
  }

  return (
    <>
      <SiteHeader active="jobs" mode="candidate" />
      <Page>
        <HeroSearch
          kicker={`Chào ${firstName}`}
          title="Việc làm phù hợp với bạn"
          lead="Lọc theo khu vực hoặc xem những tin khớp với CV đã cập nhật."
        >
          <SearchBar
            keyword={keyword}
            onKeywordChange={setKeyword}
            city={city}
            onCityChange={setCity}
            onSubmit={() => undefined}
          />
          <FilterChips>
            <ChipFilter active={mode === "near"} onClick={() => setMode("near")}>
              Theo khu vực
            </ChipFilter>
            <ChipFilter active={mode === "match"} onClick={() => setMode("match")}>
              Phù hợp CV
            </ChipFilter>
            <Link to="/candidate/cv" className="chip-filter" style={{ textDecoration: "none" }}>
              Cập nhật CV
            </Link>
          </FilterChips>
        </HeroSearch>

        <LayoutFeed>
          <section>
            <SectionHead
              title={mode === "near" ? "Việc làm theo khu vực" : "Việc phù hợp CV"}
              subtitle={
                mode === "near"
                  ? `Khu vực: ${city}`
                  : matchResults.length > 0
                    ? "Theo mức phù hợp với hồ sơ của bạn"
                    : "Chưa có điểm chấm. Đang hiện các tin đã đăng."
              }
              actions={
                <Button variant="soft" size="sm" to="/candidate/matching">
                  Xem xếp hạng
                </Button>
              }
            />
            <JobList>
              {mode === "match" && !cvReady ? (
                <EmptyNote>
                  Tải CV để hệ thống phân tích và trích xuất dữ liệu. Việc phù hợp
                  chỉ hiện sau khi hồ sơ đã được đọc.
                  <div style={{ marginTop: "0.85rem" }}>
                    <Button variant="primary" size="sm" to="/candidate/cv">
                      Tải CV
                    </Button>
                  </div>
                </EmptyNote>
              ) : list.length === 0 ? (
                <EmptyNote>Chưa có tin phù hợp.</EmptyNote>
              ) : (
                list.map((job, i) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    match={cvReady ? matchForJob(matchResults, job.id) : undefined}
                    showMatch={cvReady && matchResults.length > 0}
                    active={job.id === activeId}
                    delayMs={i * 40}
                    onClick={() => setSelectedId(job.id)}
                    onApply={apply}
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
                  <div className="job-tags" style={{ marginBottom: ".75rem" }}>
                    {selected.requiredSkills.map((skill) => (
                      <Chip key={skill} tone="ok">
                        {skill}
                      </Chip>
                    ))}
                    {selected.preferredSkills.map((skill) => (
                      <Chip key={skill} tone="accent">
                        {skill}
                      </Chip>
                    ))}
                  </div>
                  {cvReady && selectedMatch ? (
                    <EmptyNote>
                      <strong>{pct(selectedMatch.score)}% phù hợp.</strong>
                    </EmptyNote>
                  ) : (
                    <EmptyNote>
                      Tải CV để hệ thống đọc hồ sơ và tính mức phù hợp với tin này.
                    </EmptyNote>
                  )}
                  <SplitActions>
                    <Button variant="primary" size="sm" onClick={() => apply(selected.id)}>
                      Ứng tuyển
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      to={`/candidate/interview?jobId=${selected.id}`}
                    >
                      Ôn tập phỏng vấn
                    </Button>
                  </SplitActions>
                </>
              ) : (
                <>
                  <h3>Chi tiết việc làm</h3>
                  <p className="muted">
                    Chọn một tin bên trái để xem mô tả, kỹ năng và mức lương.
                  </p>
                </>
              )}
            </Panel>
            <Panel>
              <h3>Gợi ý tốt nhất</h3>
              {top && topJob ? (
                <>
                  <p style={{ margin: "0 0 .35rem" }}>
                    <strong>{topJob.title}</strong>
                  </p>
                  <p className="muted" style={{ margin: "0 0 .5rem" }}>
                    {topJob.company} · {pct(top.score)}%
                  </p>
                  <Chip tone="brand">{pct(top.score)}%</Chip>
                </>
              ) : (
                <EmptyNote>
                  {cvReady
                    ? "Chưa có việc được xếp hạng. Mở “Phù hợp với tôi” để cập nhật theo CV."
                    : "Tải CV để hệ thống đọc kỹ năng và kinh nghiệm, rồi mới xếp hạng việc phù hợp."}
                </EmptyNote>
              )}
            </Panel>
          </SidePanel>
        </LayoutFeed>
      </Page>
    </>
  );
}
