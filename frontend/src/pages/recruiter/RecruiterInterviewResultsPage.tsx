import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { EmptyNote, MockNote, RecruiterLayout, Table } from "../../components/common";
import {
  getRecruiterInterviewResults,
  remindInterviewCandidate,
  type InterviewResultStatus,
  type RecruiterInterviewResult,
} from "../../api/mock/recruiterMock";
import { useToast } from "../../context/ToastContext";
import { initials } from "../../utils/format";

type StatusFilter = "ALL" | InterviewResultStatus;
type SortMode = "score_desc" | "newest";

function interviewStatusBadge(status: InterviewResultStatus): { label: string; cls: string } {
  switch (status) {
    case "COMPLETED":
      return { label: "Hoàn thành", cls: "badge b-ok" };
    case "PENDING":
      return { label: "Chờ làm", cls: "badge b-gold" };
    case "IN_PROGRESS":
      return { label: "Đang làm", cls: "badge b-brand" };
    case "CANCELLED":
      return { label: "Đã huỷ", cls: "badge b-plain" };
  }
}

function actionLabel(status: InterviewResultStatus): string {
  switch (status) {
    case "COMPLETED":
      return "Xem phiên";
    case "PENDING":
      return "Nhắc ứng viên";
    case "IN_PROGRESS":
      return "Xem tiến độ";
    case "CANCELLED":
      return "Chi tiết";
  }
}

function formatScore(score: number | null): string {
  if (score === null) return "—";
  return score.toFixed(1).replace(".", ",");
}

export function RecruiterInterviewResultsPage() {
  const { toast } = useToast();
  const [rows, setRows] = useState<RecruiterInterviewResult[] | null>(null);
  const [jobFilter, setJobFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [sortMode, setSortMode] = useState<SortMode>("score_desc");
  const [selected, setSelected] = useState<RecruiterInterviewResult | null>(null);

  useEffect(() => {
    getRecruiterInterviewResults()
      .then(setRows)
      .catch((e) => {
        setRows([]);
        toast(e instanceof Error ? e.message : "Không tải được kết quả phỏng vấn");
      });
  }, [toast]);

  const jobOptions = useMemo(
    () => [...new Set((rows ?? []).map((r) => r.jobTitle))],
    [rows]
  );

  const stats = useMemo(() => {
    const list = rows ?? [];
    const completed = list.filter((r) => r.status === "COMPLETED" && r.score !== null);
    const pending = list.filter((r) => r.status === "PENDING" || r.status === "IN_PROGRESS");
    const avg =
      completed.length > 0
        ? completed.reduce((sum, r) => sum + (r.score ?? 0), 0) / completed.length
        : null;
    return {
      total: list.length,
      completedCount: completed.length,
      pendingCount: pending.length,
      avgText: avg === null ? "—" : avg.toFixed(1).replace(".", ","),
    };
  }, [rows]);

  const filtered = useMemo(() => {
    const list = (rows ?? []).filter((r) => {
      if (jobFilter && r.jobTitle !== jobFilter) return false;
      if (statusFilter !== "ALL" && r.status !== statusFilter) return false;
      return true;
    });
    return [...list].sort((a, b) => {
      if (sortMode === "newest") {
        return b.invitedIso.localeCompare(a.invitedIso);
      }
      const sa = a.score ?? -1;
      const sb = b.score ?? -1;
      if (sb !== sa) return sb - sa;
      return b.invitedIso.localeCompare(a.invitedIso);
    });
  }, [rows, jobFilter, statusFilter, sortMode]);

  async function handleRowAction(r: RecruiterInterviewResult) {
    if (r.status === "PENDING") {
      try {
        await remindInterviewCandidate(r.id);
        toast(`Đã gửi lời nhắc làm phỏng vấn tới ${r.candidateName}.`);
      } catch (e) {
        toast(e instanceof Error ? e.message : "Không gửi được lời nhắc");
      }
      return;
    }
    setSelected(r);
  }

  return (
    <RecruiterLayout active="interviewResults">
      <MockNote />

      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1 style={{ fontSize: 32 }}>Kết quả phỏng vấn</h1>
          <p className="muted">
            Lời mời đã gửi và kết quả phiên của ứng viên ứng tuyển tin của công ty.
          </p>
        </div>
        <Link to="/recruiter/interviews" className="btn btn-g">
          Xem ngân hàng câu hỏi
        </Link>
      </div>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 200px), 1fr))",
          gap: 20,
        }}
      >
        <div className="stat">
          <p className="l">Lời mời đã gửi</p>
          <p className="v">{stats.total}</p>
        </div>
        <div className="stat">
          <p className="l">Đã hoàn thành</p>
          <p className="v">{stats.completedCount}</p>
        </div>
        <div className="stat">
          <p className="l">Chờ ứng viên làm</p>
          <p className="v">{stats.pendingCount}</p>
        </div>
        <div className="stat">
          <p className="l">Điểm trung bình</p>
          <p className="v">{stats.avgText}</p>
        </div>
      </section>

      <div className="row">
        <select
          className="input"
          aria-label="Tin tuyển dụng"
          style={{ width: "auto" }}
          value={jobFilter}
          onChange={(e) => setJobFilter(e.target.value)}
        >
          <option value="">Tất cả tin</option>
          {jobOptions.map((j) => (
            <option key={j} value={j}>
              {j}
            </option>
          ))}
        </select>

        <select
          className="input"
          aria-label="Trạng thái"
          style={{ width: "auto" }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
        >
          <option value="ALL">Mọi trạng thái</option>
          <option value="COMPLETED">Hoàn thành</option>
          <option value="PENDING">Chờ làm</option>
          <option value="IN_PROGRESS">Đang làm</option>
          <option value="CANCELLED">Đã huỷ</option>
        </select>

        <select
          className="input"
          aria-label="Sắp xếp"
          style={{ width: "auto" }}
          value={sortMode}
          onChange={(e) => setSortMode(e.target.value as SortMode)}
        >
          <option value="score_desc">Điểm cao nhất</option>
          <option value="newest">Mới nhất</option>
        </select>
      </div>

      {rows === null ? (
        <p className="muted">Đang tải danh sách kết quả phỏng vấn…</p>
      ) : filtered.length === 0 ? (
        <EmptyNote>Không có phiên phỏng vấn nào khớp bộ lọc hiện tại.</EmptyNote>
      ) : (
        <Table style={{ minWidth: 960 }}>
          <thead>
            <tr>
              <th>Ứng viên</th>
              <th>Tin</th>
              <th>Mời lúc</th>
              <th>Trạng thái</th>
              <th>Điểm</th>
              <th>Chủ đề yếu nhất</th>
              <th style={{ textAlign: "right" }} aria-label="Thao tác" />
            </tr>
          </thead>
          <tbody>
            {filtered.map((r) => {
              const badge = interviewStatusBadge(r.status);
              return (
                <tr key={r.id}>
                  <td>
                    <div className="row" style={{ gap: 10, flexWrap: "nowrap" }}>
                      <span className="avatar">{initials(r.candidateName)}</span>
                      <Link
                        to={`/recruiter/candidates/${r.applicationId}`}
                        style={{ fontWeight: 650 }}
                      >
                        {r.candidateName}
                      </Link>
                    </div>
                  </td>
                  <td className="small">{r.jobTitle}</td>
                  <td className="small muted">{r.invitedAt}</td>
                  <td>
                    <span className={badge.cls}>{badge.label}</span>
                  </td>
                  <td className="disp" style={{ color: "var(--brand)", fontSize: 18 }}>
                    {formatScore(r.score)}
                  </td>
                  <td className="small">{r.weakestTopic ?? "—"}</td>
                  <td style={{ textAlign: "right" }}>
                    <button
                      type="button"
                      className="btn btn-g btn-sm"
                      onClick={() => void handleRowAction(r)}
                    >
                      {actionLabel(r.status)}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      )}

      {selected ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="iv-summary-title"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 50,
            display: "grid",
            placeItems: "center",
            padding: 20,
          }}
        >
          <div className="scrim" onClick={() => setSelected(null)} />
          <div className="modal stack" style={{ gap: 14, maxHeight: "90vh", overflowY: "auto" }}>
            <div className="between">
              <div>
                <h2 id="iv-summary-title" style={{ fontSize: 22 }}>
                  Phiên phỏng vấn · {selected.candidateName}
                </h2>
                <p className="small muted">
                  {selected.jobTitle} · Mời lúc {selected.invitedAt}
                </p>
              </div>
              <button
                type="button"
                className="btn btn-g btn-sm"
                onClick={() => setSelected(null)}
              >
                Đóng
              </button>
            </div>

            {selected.score !== null ? (
              <div className="row" style={{ gap: 20 }}>
                <p className="disp" style={{ fontSize: 38, color: "var(--brand)" }}>
                  {formatScore(selected.score)}
                  <span className="small muted" style={{ fontFamily: "var(--font-body)" }}>
                    /10
                  </span>
                </p>
                <p className="small muted">
                  {selected.questionCount} câu · {selected.durationMinutes ?? 25} phút
                </p>
              </div>
            ) : null}

            {selected.topicScores.length > 0 ? (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 180px), 1fr))",
                  gap: 12,
                }}
              >
                {selected.topicScores.map((t) => (
                  <div key={t.topic}>
                    <div className="between tiny" style={{ marginBottom: 4 }}>
                      <span className="muted">{t.topic}</span>
                      <strong>{t.score.toFixed(1).replace(".", ",")}</strong>
                    </div>
                    <div className="meter">
                      <span style={{ width: `${Math.min(100, t.score * 10)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            ) : null}

            <p className="small" style={{ color: "var(--ink-soft)" }}>
              {selected.summaryComment}
            </p>

            <div
              className="row"
              style={{
                justifyContent: "flex-end",
                borderTop: "1px solid var(--line)",
                paddingTop: 12,
              }}
            >
              <Link
                to={`/recruiter/candidates/${selected.applicationId}`}
                className="btn btn-p btn-sm"
              >
                Mở hồ sơ ứng viên
              </Link>
            </div>
          </div>
        </div>
      ) : null}
    </RecruiterLayout>
  );
}
