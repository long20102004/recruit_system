import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Button,
  Chip,
  EmptyNote,
  Page,
  PageHead,
  Panel,
  SiteHeader,
  SplitActions,
} from "../../components/common";
import { jobsApi } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { mapJob } from "../../utils/mappers";
import type { Job } from "../../types";

function pieces(text: string, splitCommas = false): string[] {
  const trimmed = text.trim();
  if (!trimmed) return [];
  const byLine = trimmed.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (byLine.length >= 2) return byLine;
  if (splitCommas) {
    const byComma = trimmed.split(",").map((part) => part.trim()).filter(Boolean);
    if (byComma.length >= 2) return byComma;
  }
  return [trimmed];
}

function TextBlock({ text, splitCommas = false }: { text: string; splitCommas?: boolean }) {
  const lines = pieces(text, splitCommas);
  if (lines.length >= 2) {
    return (
      <ul className="cv-lines">
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    );
  }
  return <p>{lines[0]}</p>;
}

export function CandidateJobDetailPage() {
  const { jobId } = useParams();
  const { toast } = useToast();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const id = Number(jobId);
    if (!Number.isFinite(id)) {
      setLoading(false);
      return;
    }
    jobsApi
      .get(id)
      .then((dto) => setJob(mapJob(dto)))
      .catch((e) => toast(e instanceof Error ? e.message : "Không tải được tin tuyển dụng"))
      .finally(() => setLoading(false));
  }, [jobId, toast]);

  const id = Number(jobId);

  return (
    <>
      <SiteHeader active="matching" mode="candidate" />
      <Page>
        <PageHead
          title={job?.title ?? "Chi tiết công việc"}
          description={
            job
              ? [job.company, job.location, job.workType].filter(Boolean).join(" · ")
              : "Thông tin vị trí tuyển dụng"
          }
          actions={
            <Button variant="ghost" to="/candidate/matching">
              Quay lại
            </Button>
          }
        />
        <Panel>
          {loading ? (
            <EmptyNote>Đang tải tin tuyển dụng…</EmptyNote>
          ) : !job ? (
            <EmptyNote>Không tìm thấy tin tuyển dụng này.</EmptyNote>
          ) : (
            <article className="job-detail">
              <header>
                <p className="meta">
                  {[job.level, job.postedAgo].filter(Boolean).join(" · ")}
                </p>
              </header>

              {job.description ? (
                <section>
                  <h3>Mô tả công việc</h3>
                  <TextBlock text={job.description} />
                </section>
              ) : null}

              {job.requirements ? (
                <section>
                  <h3>Yêu cầu</h3>
                  <TextBlock text={job.requirements} splitCommas />
                </section>
              ) : null}

              {job.responsibilities ? (
                <section>
                  <h3>Trách nhiệm</h3>
                  <TextBlock text={job.responsibilities} splitCommas />
                </section>
              ) : null}

              <section>
                <h3>Đãi ngộ</h3>
                <ul className="cv-lines">
                  <li>Mức lương: {job.salary}</li>
                  {job.workType ? <li>Hình thức: {job.workType}</li> : null}
                  {job.location ? <li>Địa điểm: {job.location}</li> : null}
                  <li>
                    Kinh nghiệm:{" "}
                    {job.minYears > 0 ? `từ ${job.minYears} năm` : "không yêu cầu"}
                  </li>
                </ul>
              </section>

              {job.requiredSkills.length > 0 ? (
                <section>
                  <h3>Kỹ năng bắt buộc</h3>
                  <div className="job-tags">
                    {job.requiredSkills.map((skill) => (
                      <Chip key={skill} tone="brand">
                        {skill}
                      </Chip>
                    ))}
                  </div>
                </section>
              ) : null}

              {job.preferredSkills.length > 0 ? (
                <section>
                  <h3>Kỹ năng ưu tiên</h3>
                  <div className="job-tags">
                    {job.preferredSkills.map((skill) => (
                      <Chip key={skill}>{skill}</Chip>
                    ))}
                  </div>
                </section>
              ) : null}

              <SplitActions>
                <Button
                  variant="accent"
                  to={Number.isFinite(id) ? `/candidate/interview?jobId=${id}` : "/candidate/interview"}
                >
                  Ôn tập phỏng vấn
                </Button>
              </SplitActions>
            </article>
          )}
        </Panel>
      </Page>
    </>
  );
}
