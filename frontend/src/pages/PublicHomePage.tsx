import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
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
  QuickLink,
  SearchBar,
  SectionHead,
  SidePanel,
  SiteHeader,
  SplitActions,
} from "../components/common";
import { jobsApi, matchingApi, type JobDto, type MatchDto } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { mapJob, mapMatch } from "../utils/mappers";
import { filterJobs, jobById, matchForJob } from "../utils/jobs";
import { pct } from "../utils/format";
import { accountPath } from "../utils/account";

export function PublicHomePage() {
  const { toast } = useToast();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [keyword, setKeyword] = useState("");
  const [city, setCity] = useState("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [remoteJobs, setRemoteJobs] = useState<JobDto[]>([]);
  const [matches, setMatches] = useState<ReturnType<typeof mapMatch>[]>([]);

  useEffect(() => {
    jobsApi
      .list()
      .then((list) => {
        setRemoteJobs(list);
      })
      .catch(() => {
        toast("Không tải được danh sách việc làm. Thử lại sau.");
      });
  }, [toast]);

  useEffect(() => {
    if (!user || user.role !== "CANDIDATE") return;
    matchingApi
      .mine()
      .then((list: MatchDto[]) => setMatches(list.map(mapMatch)))
      .catch(() => undefined);
  }, [user]);

  const allJobs = useMemo(
    () => (remoteJobs.length ? remoteJobs.map(mapJob) : []),
    [remoteJobs]
  );

  const jobs = useMemo(
    () => filterJobs(allJobs, { keyword, city }),
    [allJobs, keyword, city]
  );

  const activeId =
    selectedId && jobs.some((j) => j.id === selectedId)
      ? selectedId
      : jobs[0]?.id ?? null;
  const selected = activeId ? jobById(allJobs, activeId) : undefined;
  const match = activeId ? matchForJob(matches, activeId) : undefined;

  function goApply() {
    if (!user) {
      navigate("/register");
      return;
    }
    navigate(accountPath(user));
  }

  return (
    <>
      <SiteHeader active="jobs" mode="public" />
      <Page>
        <HeroSearch
          kicker="HireLens"
          title="Tìm việc hoặc tuyển người trên cùng một hệ thống."
          lead="Xem tin đang mở ngay. Đăng ký bằng email, rồi chọn vai trò ứng viên hoặc nhà tuyển dụng khi vào tài khoản lần đầu."
        >
          <SearchBar
            keyword={keyword}
            onKeywordChange={setKeyword}
            city={city}
            onCityChange={setCity}
            onSubmit={() => undefined}
          />
          <FilterChips>
            <ChipFilter active={city === "all"} onClick={() => setCity("all")}>
              Tất cả khu vực
            </ChipFilter>
            <ChipFilter
              active={city === "TP. Hồ Chí Minh"}
              onClick={() => setCity("TP. Hồ Chí Minh")}
            >
              TP. Hồ Chí Minh
            </ChipFilter>
            <ChipFilter active={city === "Hà Nội"} onClick={() => setCity("Hà Nội")}>
              Hà Nội
            </ChipFilter>
            <ChipFilter active={city === "Remote"} onClick={() => setCity("Remote")}>
              Remote
            </ChipFilter>
          </FilterChips>
        </HeroSearch>

        <LayoutFeed>
          <section>
            <SectionHead
              title="Việc làm đang tuyển"
              subtitle={
                city === "all"
                  ? "Tất cả tin đang mở trên hệ thống"
                  : `Khu vực: ${city}`
              }
              actions={<Chip tone="brand">{jobs.length} việc</Chip>}
            />
            <JobList>
              {jobs.length === 0 ? (
                <EmptyNote>
                  Chưa có tin phù hợp với bộ lọc hiện tại. Thử đổi khu vực hoặc từ
                  khóa.
                </EmptyNote>
              ) : (
                jobs.map((job, i) => (
                  <JobCard
                    key={job.id}
                    job={job}
                    match={matchForJob(matches, job.id)}
                    showMatch={Boolean(user && user.role === "CANDIDATE")}
                    active={job.id === activeId}
                    delayMs={i * 40}
                    onClick={() => setSelectedId(job.id)}
                    onApply={goApply}
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
                  {user?.role === "CANDIDATE" && match ? (
                    <EmptyNote>
                      <strong>{pct(match.score)}% phù hợp.</strong>
                      <br />
                      {match.reasons[0]}
                    </EmptyNote>
                  ) : !user ? (
                    <EmptyNote>
                      Tạo tài khoản ứng viên và tải CV để xem mức phù hợp theo hồ
                      sơ của bạn.
                    </EmptyNote>
                  ) : user.role === "CANDIDATE" ? (
                    <EmptyNote>
                      Mức phù hợp hiện sau khi bạn tải CV để hệ thống phân tích.
                    </EmptyNote>
                  ) : null}
                  <SplitActions>
                    <Button variant="primary" size="sm" onClick={goApply}>
                      {user?.role === "RECRUITER" || user?.role === "ADMIN"
                        ? "Trang tuyển dụng"
                        : "Ứng tuyển"}
                    </Button>
                    {user?.role === "RECRUITER" || user?.role === "ADMIN" ? null : (
                      <Button
                        variant="ghost"
                        size="sm"
                        to={user ? "/candidate/interview" : "/register"}
                      >
                        Luyện phỏng vấn
                      </Button>
                    )}
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
              <h3>{user ? "Lối tắt" : "Bắt đầu"}</h3>
              {user ? (
                <>
                  <QuickLink to={accountPath(user)} label="Trang của tôi" meta="Làm việc" />
                </>
              ) : (
                <>
                  <QuickLink to="/register" label="Tạo tài khoản" meta="Email và mật khẩu" />
                  <QuickLink to="/login" label="Đăng nhập" meta="Đã có tài khoản" />
                </>
              )}
            </Panel>
          </SidePanel>
        </LayoutFeed>
      </Page>
    </>
  );
}
