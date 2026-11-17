import { useEffect, useState } from "react";
import {
  Button,
  Chip,
  EmptyNote,
  Field,
  Page,
  PageHead,
  Panel,
  SiteHeader,
  TextSelect,
} from "../../components/common";
import {
  applicationsApi,
  jobsApi,
  matchingApi,
  type JobDto,
  type MatchDto,
} from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { pct } from "../../utils/format";

export function RecruiterMatchingPage() {
  const { toast } = useToast();
  const [jobs, setJobs] = useState<JobDto[]>([]);
  const [jobId, setJobId] = useState<number | "">("");
  const [matches, setMatches] = useState<MatchDto[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    jobsApi
      .mine()
      .then((list) => {
        setJobs(list);
        if (list[0]) setJobId(list[0].id);
      })
      .catch((e) => toast(e.message));
  }, [toast]);

  useEffect(() => {
    if (!jobId) return;
    matchingApi
      .forJob(Number(jobId))
      .then(setMatches)
      .catch(() => setMatches([]));
  }, [jobId]);

  async function run() {
    if (!jobId) return;
    setBusy(true);
    try {
      const applicants = (await applicationsApi.recruiter()).filter(
        (a) => a.jobId === Number(jobId),
      );
      const candidateIds = [...new Set(applicants.map((a) => a.candidateId))];
      for (const candidateId of candidateIds) {
        await matchingApi.run(Number(jobId), candidateId);
      }
      setMatches(await matchingApi.forJob(Number(jobId)));
      toast("Đã cập nhật xếp hạng ứng viên");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Không xếp hạng được. Thử lại.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <SiteHeader active="matching" mode="recruiter" />
      <Page>
        <PageHead
          title="Ghép hồ sơ – tin tuyển dụng"
          description="Xếp hạng ứng viên theo kỹ năng và mức phù hợp với tin đã chọn."
          actions={
            <Button variant="primary" onClick={run} disabled={busy || !jobId}>
              {busy ? "Đang chạy…" : "Làm mới xếp hạng"}
            </Button>
          }
        />

        <Panel>
          <Field label="Chọn tin tuyển dụng">
            <TextSelect
              value={jobId}
              onChange={(e) =>
                setJobId(e.target.value ? Number(e.target.value) : "")
              }
            >
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title}
                </option>
              ))}
            </TextSelect>
          </Field>

          {matches.length === 0 ? (
            <EmptyNote>
              Chưa có kết quả. Bấm “Làm mới xếp hạng” để ghép ứng viên với tin đã
              chọn.
            </EmptyNote>
          ) : (
            matches.map((m) => (
              <article
                key={m.id}
                className="match-item"
                style={{ marginTop: "1rem" }}
              >
                <div>
                  <h3 style={{ margin: "0 0 .35rem" }}>
                    {m.candidateName} · {pct(Number(m.overallScore))}%
                  </h3>
                  <div className="job-tags">
                    {(m.matchedSkills ?? []).map((s) => (
                      <Chip key={s} tone="ok">
                        {s}
                      </Chip>
                    ))}
                    {(m.missingSkills ?? []).map((s) => (
                      <Chip key={`x-${s}`} tone="warn">
                        Thiếu: {s}
                      </Chip>
                    ))}
                  </div>
                  <p className="muted">
                    {(m.reasons ?? []).join(" · ") || "—"}
                  </p>
                </div>
              </article>
            ))
          )}
        </Panel>
      </Page>
    </>
  );
}
