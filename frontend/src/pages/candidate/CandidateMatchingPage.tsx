import { useCallback, useEffect, useState } from "react";
import {
  Button,
  EmptyNote,
  MatchItem,
  Page,
  PageHead,
  Panel,
  SiteHeader,
} from "../../components/common";
import {
  cvsApi,
  jobsApi,
  matchingApi,
  type JobDto,
  type MatchDto,
} from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { mapJob, mapMatch } from "../../utils/mappers";

export function CandidateMatchingPage() {
  const { toast } = useToast();
  const [matches, setMatches] = useState<MatchDto[]>([]);
  const [jobs, setJobs] = useState<JobDto[]>([]);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [scoreError, setScoreError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const form = await cvsApi.mine();
    const analyzed = form.analyzed;
    setReady(analyzed);
    if (!analyzed) {
      setMatches([]);
      setJobs([]);
      setScoreError(null);
      return "empty" as const;
    }
    const jobList = await jobsApi.list();
    setJobs(jobList);
    let stored: MatchDto[] = [];
    try {
      stored = await matchingApi.mine();
    } catch {
      stored = [];
    }
    setMatches(stored);
    try {
      setMatches(await matchingApi.refreshMine());
      setScoreError(null);
      return "scored" as const;
    } catch (e) {
      const message = e instanceof Error ? e.message : "Không chấm được mức phù hợp";
      setScoreError(stored.length > 0 ? null : message);
      if (stored.length === 0 && jobList.length === 0) throw e;
      return stored.length > 0 ? ("stored" as const) : ("listed" as const);
    }
  }, []);

  useEffect(() => {
    load()
      .catch((e) => toast(e instanceof Error ? e.message : "Không tải được việc phù hợp"))
      .finally(() => setLoading(false));
  }, [load, toast]);

  async function rematch() {
    setBusy(true);
    try {
      const result = await load();
      if (result === "scored") toast("Đã cập nhật việc phù hợp theo CV");
      else if (result === "stored") toast("Giữ điểm đã lưu. Service chấm điểm đang không chạy.");
      else toast("Đã hiện tin tuyển dụng. Service chấm điểm đang không chạy.");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không cập nhật được danh sách");
    } finally {
      setBusy(false);
    }
  }

  const ranked = [...matches].sort(
    (a, b) => Number(b.overallScore) - Number(a.overallScore)
  );

  return (
    <>
      <SiteHeader active="matching" mode="candidate" />
      <Page>
        <PageHead
          title="Công việc phù hợp với tôi"
          description="Danh sách được xếp hạng từ kỹ năng và kinh nghiệm đã trích xuất trong CV của bạn."
          actions={
            ready ? (
              <Button variant="primary" onClick={rematch} disabled={busy}>
                {busy ? "Đang cập nhật…" : "Cập nhật theo CV"}
              </Button>
            ) : null
          }
        />

        <Panel>
          {loading ? (
            <EmptyNote>Đang kiểm tra hồ sơ…</EmptyNote>
          ) : !ready ? (
            <EmptyNote>
              Chưa có dữ liệu. Hãy tải CV ở mục Hồ sơ / CV để hệ thống phân tích
              và trích xuất kỹ năng, học vấn, kinh nghiệm. Việc phù hợp chỉ hiện
              sau bước đó.
              <div style={{ marginTop: "0.85rem" }}>
                <Button variant="primary" size="sm" to="/candidate/cv">
                  Tải CV
                </Button>
              </div>
            </EmptyNote>
          ) : ranked.length === 0 && jobs.length === 0 ? (
            <EmptyNote>
              CV đã được phân tích nhưng chưa có tin tuyển dụng để so khớp.
            </EmptyNote>
          ) : ranked.length === 0 ? (
            <>
              <EmptyNote>
                {scoreError
                  ? `Chưa chấm được mức phù hợp (${scoreError}). Các tin đang mở:`
                  : "Chưa có điểm phù hợp. Các tin đang mở:"}
              </EmptyNote>
              {jobs.map((job) => {
                const mapped = mapJob(job);
                return (
                  <article key={job.id} className="match-item">
                    <div>
                      <h3 style={{ margin: 0 }}>{mapped.title}</h3>
                      <div className="muted">
                        {mapped.company} · {mapped.location} · {mapped.salary}
                      </div>
                      <p className="match-gap">
                        Kỹ năng yêu cầu: {mapped.requiredSkills.join(", ") || "Chưa khai báo"}
                      </p>
                    </div>
                    <Button variant="accent" size="sm" to={`/candidate/jobs/${job.id}`}>
                      Xem chi tiết
                    </Button>
                  </article>
                );
              })}
            </>
          ) : (
            ranked.map((r, idx) => {
              const job = jobs.find((j) => j.id === r.jobId);
              if (!job) return null;
              const mapped = mapJob(job);
              const match = mapMatch(r);
              if (!match.rank) match.rank = idx + 1;
              return (
                <MatchItem
                  key={r.id}
                  job={mapped}
                  match={match}
                  actionHref={`/candidate/jobs/${job.id}`}
                  actionLabel="Xem chi tiết"
                />
              );
            })
          )}
        </Panel>
      </Page>
    </>
  );
}
