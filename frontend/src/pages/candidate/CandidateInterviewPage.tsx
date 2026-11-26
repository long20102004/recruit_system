import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Link } from "react-router-dom";
import { EmptyNote, Pager, SiteHeader } from "../../components/common";
import { interviewsApi, type EvaluationDto, type PageDto, type SessionDto, type SessionSummaryDto } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { shortDate } from "../../utils/format";

const STATUS: Record<string, string> = { CREATED: "Mới tạo", IN_PROGRESS: "Đang làm", COMPLETED: "Đã hoàn thành" };
const STATUS_CLS: Record<string, string> = { CREATED: "badge", IN_PROGRESS: "badge b-brand", COMPLETED: "badge b-ok" };
const score = (v: number | null | undefined) => (v == null ? "—" : Number(v).toFixed(1).replace(".", ","));
export function CandidateInterviewPage() {
  const { toast } = useToast();
  const [params] = useSearchParams();
  const jobId = Number(params.get("jobId"));
  const [session,setSession] = useState<SessionDto|null>(null);
  const [historyData,setHistoryData] = useState<PageDto<SessionDto>|null>(null);
  const history = historyData?.content ?? [];
  const [summary,setSummary] = useState<SessionSummaryDto|null>(null);
  const [idx,setIdx] = useState(0);
  const [answer,setAnswer] = useState("");
  const [lastAnswer,setLastAnswer] = useState<string|null>(null);
  const [evaluation,setEvaluation] = useState<EvaluationDto|null>(null);
  const [busy,setBusy] = useState(false);
  const [count,setCount] = useState(6);
  useEffect(() => { interviewsApi.mine().then(setHistoryData).catch(e => toast(e.message)); },[toast]);
  const q = session?.questions[idx];
  async function openSession(id:number) {
    setBusy(true);
    try {
      const [s,report] = await Promise.all([interviewsApi.getSession(id),interviewsApi.summary(id)]);
      setSession(s);setSummary(report);setIdx(s.currentIndex);setAnswer("");setLastAnswer(null);setEvaluation(null);
    } catch(e) { toast(e instanceof Error ? e.message : "Không tải được phiên"); }
    finally { setBusy(false); }
  }
  async function start() {
    setBusy(true);
    try {
      const s = await interviewsApi.createSession({ ...(Number.isFinite(jobId)&&jobId>0 ? {jobId}:{}),questionCount:count });
      setSession(s);setIdx(s.currentIndex);setSummary(null);setAnswer("");setLastAnswer(null);setEvaluation(null);
      setHistoryData(await interviewsApi.mine());
    } catch(e) { toast(e instanceof Error ? e.message : "Không tạo được phiên"); }
    finally { setBusy(false); }
  }
  async function submit() {
    if(!session||!q||!answer.trim()) { toast("Hãy nhập câu trả lời");return; }
    setBusy(true);setLastAnswer(answer.trim());
    try {
      const ev = await interviewsApi.submit(session.id,q.questionId,answer.trim());setEvaluation(ev);
      const [s,report] = await Promise.all([interviewsApi.getSession(session.id),interviewsApi.summary(session.id)]);
      setSession(s);setSummary(report);setHistoryData(await interviewsApi.mine());toast("Đã lưu kết quả đánh giá");
    } catch(e) { toast(e instanceof Error ? e.message : "Đánh giá thất bại"); }
    finally { setBusy(false); }
  }
  function next() {
    if(!session||!evaluation) return;
    setIdx(session.currentIndex);setAnswer("");setLastAnswer(null);setEvaluation(null);
  }
  function exit() {
    setSession(null); setSummary(null); setEvaluation(null); setAnswer(""); setLastAnswer(null);
  }
  const total = session?.questions.length ?? 0;
  const answered = summary?.answeredQuestions ?? 0;
  const done = session?.status === "COMPLETED";
  const evalFor = (questionId: number) => summary?.evaluations.find((e) => e.questionId === questionId);

  if (!session) {
    return (
      <>
        <SiteHeader active="interview" mode="candidate" />
        <div className="wrap" style={{ paddingTop: 32, paddingBottom: 64, display: "flex", flexDirection: "column", gap: 24 }}>
          <div>
            <h1 style={{ fontSize: 34 }}>Phỏng vấn</h1>
            <p className="muted" style={{ marginTop: 6 }}>Tự luyện với câu hỏi chọn theo kỹ năng trong JD và CV; AI chấm từng câu trả lời.</p>
          </div>
          <section style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-start" }}>
            <form className="card" style={{ flex: "1 1 360px", maxWidth: 460, display: "flex", flexDirection: "column", gap: 14 }}
              onSubmit={(e) => { e.preventDefault(); void start(); }}>
              <h2 style={{ fontSize: 22 }}>Tự luyện</h2>
              <div className="field">
                <label>Luyện cho tin</label>
                <p className="small">
                  {Number.isFinite(jobId) && jobId > 0
                    ? <>Tin #{jobId} · <Link to="/candidate/interview" style={{ color: "var(--brand)", fontWeight: 600 }}>bỏ chọn</Link></>
                    : "Không chọn tin: dùng kỹ năng trong CV"}
                </p>
                <span className="help">Câu hỏi ưu tiên kỹ năng bắt buộc của JD, sau đó kỹ năng trong CV; tránh câu đã gặp gần đây.</span>
              </div>
              <div className="field">
                <label htmlFor="iv-count">Số câu</label>
                <select id="iv-count" className="input" value={count} onChange={(e) => setCount(Number(e.target.value))}>
                  {[3, 6, 9, 12].map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
              <button type="submit" className="btn btn-p" disabled={busy}>{busy ? "Đang tạo…" : "Bắt đầu phiên luyện"}</button>
            </form>
            <div style={{ flex: "999 1 520px", minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
              <h2 style={{ fontSize: 22 }}>Lịch sử phiên<span className="count">{historyData?.totalElements ?? 0}</span></h2>
              {history.length === 0 ? (
                <EmptyNote>Chưa có phiên nào. Bắt đầu một phiên luyện ở bên trái.</EmptyNote>
              ) : (
                <div className="tbl-box">
                  <table className="tbl" style={{ minWidth: 560 }}>
                    <thead><tr><th>Ngày</th><th>Tin / chủ đề</th><th>Số câu</th><th>Trạng thái</th><th /></tr></thead>
                    <tbody>
                      {history.map((h) => (
                        <tr key={h.id}>
                          <td className="small">{shortDate(h.createdAt)}</td>
                          <td style={{ fontWeight: 600 }}>{h.jobTitle ?? "Luyện theo CV"}</td>
                          <td>{h.questions.length}</td>
                          <td><span className={STATUS_CLS[h.status] ?? "badge"}>{STATUS[h.status] ?? h.status}</span></td>
                          <td>
                            <button type="button" className="btn btn-link small" disabled={busy} onClick={() => openSession(h.id)}>
                              {h.status === "COMPLETED" ? "Xem kết quả" : "Làm tiếp"}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <Pager data={historyData} onPage={(p) => interviewsApi.mine({ page: p }).then(setHistoryData).catch((e) => toast(e.message))} />
            </div>
          </section>
        </div>
      </>
    );
  }

  return (
    <>
      <header style={{ background: "var(--ink)", color: "#e9e2d7" }}>
        <div className="wrap between" style={{ minHeight: 64 }}>
          <div className="row" style={{ gap: 14 }}>
            <button type="button" className="small" onClick={exit}
              style={{ color: "#d8cfc2", background: "none", border: 0, cursor: "pointer", font: "inherit" }}>← Thoát</button>
            <span style={{ width: 1, height: 20, background: "#4a433c" }} />
            <p style={{ fontWeight: 650, color: "#fbf8f3" }}>{session.jobTitle ?? "Luyện theo CV"}</p>
            <span className={STATUS_CLS[session.status] ?? "badge"}>{STATUS[session.status] ?? session.status}</span>
          </div>
          <div className="row" style={{ gap: 14, fontSize: 14 }}>
            <span>Đã chấm {answered} / {total}</span>
            <div className="meter" style={{ width: 160, background: "#4a433c" }}>
              <span style={{ width: `${total ? (answered / total) * 100 : 0}%`, background: "#b8c5f0" }} />
            </div>
          </div>
        </div>
      </header>
      <div className="wrap" style={{ paddingTop: 28, paddingBottom: 64, display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-start" }}>
        <nav aria-label="Danh sách câu hỏi" className="card" style={{ flex: "1 1 220px", maxWidth: 260, padding: 8, display: "flex", flexDirection: "column", gap: 2 }}>
          {session.questions.map((item, i) => {
            const e = evalFor(item.questionId);
            const on = i === idx && !done;
            return (
              <div key={item.questionId} style={{ display: "flex", justifyContent: "space-between", gap: 8, padding: "10px 12px", borderRadius: 2, fontSize: 14,
                fontWeight: 600, background: on ? "var(--brand-soft)" : undefined, color: on ? "var(--brand-deep)" : e ? "var(--ink)" : "var(--muted)" }}>
                <span>Câu {i + 1}{item.topic ? ` · ${item.topic}` : ""}</span>
                <span className="tiny">{e ? score(e.predictedScore) : on ? "Đang làm" : ""}</span>
              </div>
            );
          })}
        </nav>
        <main style={{ flex: "999 1 560px", minWidth: 0, display: "flex", flexDirection: "column", gap: 18 }}>
          {q && !done ? (
            <section className="card" style={{ padding: 28, display: "flex", flexDirection: "column", gap: 14 }}>
              <div className="row" style={{ gap: 8 }}>
                {q.topic ? <span className="badge b-brand b-plain">{q.topic}</span> : null}
                {q.difficulty ? <span className="badge b-plain">{q.difficulty}</span> : null}
                <span className="badge b-plain">Câu {idx + 1} / {total}</span>
              </div>
              <h2 style={{ fontSize: 24, lineHeight: 1.3 }}>{q.questionText}</h2>
              {lastAnswer && evaluation ? (
                <div className="note small"><strong>Câu trả lời đã nộp:</strong> {lastAnswer}</div>
              ) : (
                <div className="field">
                  <label htmlFor="iv-answer">Câu trả lời của bạn</label>
                  <textarea id="iv-answer" className="input" style={{ minHeight: 220 }} maxLength={4000}
                    value={answer} onChange={(e) => setAnswer(e.target.value)} />
                  <div className="between">
                    <span className="help">Gợi ý: nêu khái niệm, cách làm, ví dụ và cách kiểm chứng.</span>
                    <span className="help">{answer.length} ký tự</span>
                  </div>
                </div>
              )}
              <div className="row" style={{ justifyContent: "flex-end" }}>
                {evaluation ? (
                  <button type="button" className="btn btn-p" onClick={next} disabled={busy}>Câu tiếp theo</button>
                ) : (
                  <button type="button" className="btn btn-p" onClick={submit} disabled={busy}>
                    {busy ? "Đang chấm…" : "Nộp câu trả lời"}
                  </button>
                )}
              </div>
              {busy && !evaluation ? (
                <div className="note small" role="status">Đang chấm câu trả lời… thường 10–60 giây.</div>
              ) : null}
            </section>
          ) : null}

          {evaluation ? (
            <section className="card" style={{ padding: 24, display: "flex", flexDirection: "column", gap: 14 }}>
              <div className="between">
                <div>
                  <p className="kicker" style={{ color: "var(--muted)" }}>Kết quả câu {idx + 1}{q?.topic ? ` · ${q.topic}` : ""}</p>
                  <h3 style={{ marginTop: 4 }}>{q?.questionText}</h3>
                </div>
                <p className="disp" style={{ fontSize: 40, color: "var(--brand)" }}>
                  {score(evaluation.predictedScore)}<span className="small muted" style={{ fontFamily: "var(--font-body)" }}>/10</span>
                </p>
              </div>
              {evaluation.criterionResults?.length ? (
                <div style={{ display: "grid", gap: 10 }}>
                  {evaluation.criterionResults.map((c) => (
                    <div key={c.key} style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 160px 52px", gap: 12, alignItems: "center", fontSize: 14 }}>
                      <span><strong>{c.label}</strong>{c.feedback ? <span className="muted small"> · {c.feedback}</span> : null}</span>
                      <div className="meter"><span style={{ width: `${c.max_points ? (c.points / c.max_points) * 100 : 0}%` }} /></div>
                      <span style={{ textAlign: "right", fontWeight: 650 }}>{c.points.toFixed(1)}/{c.max_points.toFixed(0)}</span>
                    </div>
                  ))}
                </div>
              ) : null}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 260px), 1fr))", gap: 14 }}>
                <div style={{ background: "var(--ok-soft)", padding: 14, borderRadius: 2 }}>
                  <p className="small" style={{ fontWeight: 700, color: "var(--ok)", marginBottom: 6 }}>Ý đã nêu</p>
                  {evaluation.coveredPoints.length ? (
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13.5, display: "grid", gap: 4 }}>
                      {evaluation.coveredPoints.map((x) => <li key={x}>{x}</li>)}
                    </ul>
                  ) : <p className="small muted">Chưa nêu được ý chính nào.</p>}
                </div>
                <div style={{ background: "var(--warn-soft)", padding: 14, borderRadius: 2 }}>
                  <p className="small" style={{ fontWeight: 700, color: "var(--warn)", marginBottom: 6 }}>Ý còn thiếu</p>
                  {evaluation.missingPoints.length ? (
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13.5, display: "grid", gap: 4 }}>
                      {evaluation.missingPoints.map((x) => <li key={x}>{x}</li>)}
                    </ul>
                  ) : <p className="small muted">Không ghi nhận ý thiếu.</p>}
                </div>
              </div>
              {evaluation.comment ? <p className="small" style={{ color: "var(--ink-soft)" }}>{evaluation.comment}</p> : null}
              <p className="help">
                {evaluation.scoringMode === "bertscore"
                  ? `BERTScore + rubric · F1 ${Number(evaluation.bertscoreF1 ?? 0).toFixed(3)} · điểm luyện tập tự động`
                  : "Đối chiếu từ vựng + rubric · điểm luyện tập tự động"}
              </p>
            </section>
          ) : null}

          {done && summary ? (
            <section className="card" style={{ padding: 24, display: "flex", flexDirection: "column", gap: 14 }}>
              <div className="between">
                <div>
                  <p className="kicker">Tổng kết phiên</p>
                  <h3 style={{ marginTop: 4 }}>{summary.answeredQuestions}/{summary.totalQuestions} câu đã chấm</h3>
                </div>
                <p className="disp" style={{ fontSize: 40, color: "var(--brand)" }}>
                  {score(summary.averageScore)}<span className="small muted" style={{ fontFamily: "var(--font-body)" }}>/10</span>
                </p>
              </div>
              {summary.evaluations.map((item, i) => (
                <details key={item.responseId} style={{ borderTop: "1px solid var(--line)", paddingTop: 10 }}>
                  <summary style={{ cursor: "pointer", fontWeight: 600 }}>
                    Câu {i + 1} · {score(item.predictedScore)}/10
                  </summary>
                  {item.comment ? <p className="small" style={{ marginTop: 6 }}>{item.comment}</p> : null}
                  <p className="small muted" style={{ marginTop: 4 }}>Cần bổ sung: {item.missingPoints.join("; ") || "Không ghi nhận ý thiếu."}</p>
                </details>
              ))}
              <div className="row">
                <button type="button" className="btn btn-p" onClick={start} disabled={busy}>Luyện phiên mới</button>
                <button type="button" className="btn btn-g" onClick={exit}>Về trang phỏng vấn</button>
              </div>
            </section>
          ) : null}
        </main>
      </div>
    </>
  );
}
