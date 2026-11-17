import { useEffect, useState } from "react";
import {
  Button,
  EmptyNote,
  Grid2,
  Grid3,
  JobCard,
  JobList,
  Page,
  PageHead,
  Panel,
  SiteHeader,
  SplitActions,
  Stat,
} from "../../components/common";
import {
  applicationsApi,
  dashboardApi,
  jobsApi,
  type ApplicationDto,
  type JobDto,
  type RecruiterStatsDto,
} from "../../api/client";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { applicationStatusLabel, mapJob } from "../../utils/mappers";

export function RecruiterHomePage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [stats, setStats] = useState<RecruiterStatsDto | null>(null);
  const [jobs, setJobs] = useState<JobDto[]>([]);
  const [apps, setApps] = useState<ApplicationDto[]>([]);

  useEffect(() => {
    Promise.all([
      dashboardApi.recruiter(),
      jobsApi.mine(),
      applicationsApi.recruiter(),
    ])
      .then(([s, j, a]) => {
        setStats(s);
        setJobs(j);
        setApps(a);
      })
      .catch((e) => toast(e.message));
  }, [toast]);

  const firstName = user?.fullName?.split(" ").slice(-1)[0] ?? "bạn";

  return (
    <>
      <SiteHeader active="home" mode="recruiter" />
      <Page>
        <PageHead
          title={
            <>
              Xin chào, <span>{firstName}</span>
            </>
          }
          description={
            <>
              Quản lý tin đăng, hồ sơ ứng viên và phiên phỏng vấn.
            </>
          }
          actions={
            <Button variant="primary" to="/recruiter/jobs">
              Đăng vị trí mới
            </Button>
          }
        />

        <div style={{ marginBottom: "1.15rem" }}>
          <Grid3>
            <Stat
              label="Tin đang mở"
              value={
                stats?.openJobsCount ??
                jobs.filter((j) => j.status === "PUBLISHED").length
              }
              note="Hiển thị trên trang tìm việc"
            />
            <Stat
              label="Hồ sơ ứng viên"
              value={stats?.applicationsCount ?? apps.length}
              note="Đã nộp / đang xem xét"
            />
            <Stat
              label="Câu hỏi phỏng vấn"
              value={stats?.questionsCount ?? 0}
              note="Ngân hàng theo vị trí"
            />
          </Grid3>
        </div>

        <Grid2>
          <Panel>
            <h2>Tin tuyển dụng gần đây</h2>
            <JobList>
              {jobs.slice(0, 4).map((j, i) => (
                <JobCard key={j.id} job={mapJob(j)} delayMs={i * 40} />
              ))}
              {!jobs.length ? <EmptyNote>Chưa có tin. Hãy đăng vị trí mới.</EmptyNote> : null}
            </JobList>
            <SplitActions>
              <Button variant="soft" size="sm" to="/recruiter/jobs">
                Quản lý tất cả tin
              </Button>
            </SplitActions>
          </Panel>
          <Panel>
            <h2>Ứng viên mới</h2>
            {apps.length === 0 ? (
              <EmptyNote>Chưa có đơn ứng tuyển.</EmptyNote>
            ) : (
              apps.slice(0, 6).map((a) => (
                <div key={a.id} style={{ marginBottom: ".75rem" }}>
                  <strong>{a.candidateName}</strong>
                  <div className="muted">
                    {a.jobTitle} · {applicationStatusLabel(a.status)}
                  </div>
                </div>
              ))
            )}
            <SplitActions>
              <Button variant="soft" size="sm" to="/recruiter/candidates">
                Xem hồ sơ
              </Button>
              <Button variant="ghost" size="sm" to="/recruiter/matching">
                Ghép hồ sơ–tin
              </Button>
            </SplitActions>
          </Panel>
        </Grid2>
      </Page>
    </>
  );
}
