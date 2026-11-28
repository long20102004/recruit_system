import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Link } from "react-router-dom";
import { EmptyNote, Pager, SiteHeader } from "../../components/common";
import { interviewsApi, type EvaluationDto, type PageDto, type SessionDto, type SessionSummaryDto } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { shortDate } from "../../utils/format";
import { ANSWER_LIMIT, useInterviewDictation } from "./useInterviewDictation";

const STATUS: Record<string, string> = { CREATED: "Mới tạo", IN_PROGRESS: "Đang làm", COMPLETED: "Đã hoàn thành" };
const STATUS_CLS: Record<string, string> = { CREATED: "badge", IN_PROGRESS: "badge b-brand", COMPLETED: "badge b-ok" };
const score = (v: number | null | undefined) => (v == null ? "—" : Number(v).toFixed(1).replace(".", ","));
export function CandidateInterviewPage() {
  const { toast } = useToast();
  const [params] = useSearchParams();
  const jobId = Number(params.get("jobId"));
  const applicationId = Number(params.get("applicationId"));
  const linkedApplication = Number.isSafeInteger(applicationId) && applicationId > 0;
  const [session,setSession] = useState<SessionDto|null>(null);
  const [historyData,setHistoryData] = useState<PageDto<SessionDto>|null>(null);
  const history = historyData?.content ?? [];
  const [summary,setSummary] = useState<SessionSummaryDto|null>(null);
  const [idx,setIdx] = useState(0);
  const [answer,setAnswer] = useState("");
  const dictation = useInterviewDictation((text) => {
    setAnswer((previous) => [previous.trimEnd(), text].filter(Boolean).join(" ").slice(0, ANSWER_LIMIT));
  });
  const dictating = dictation.phase !== "idle";
  const displayedAnswer = dictation.interimText
    ? [answer.trimEnd(), dictation.interimText].filter(Boolean).join(" ").slice(0, ANSWER_LIMIT)
    : answer;
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
      const s = await interviewsApi.createSession({
        ...(Number.isSafeInteger(jobId) && jobId > 0 ? { jobId } : {}),
        ...(linkedApplication ? { applicationId } : {}),
        questionCount: count,
      });
      setSession(s);setIdx(s.currentIndex);setSummary(null);setAnswer("");setLastAnswer(null);setEvaluation(null);
      setHistoryData(await interviewsApi.mine());
    } catch(e) { toast(e instanceof Error ? e.message : "Không tạo được phiên"); }
    finally { setBusy(false); }
  }
  async function submit() {
    if (dictating || busy) return;
    if(!session||!q||!answer.trim()) { toast("Hãy nhập câu trả lời");return; }
    setBusy(true);setLastAnswer(answer.trim());
    try {
      let result = await interviewsApi.queueEvaluation(session.id, q.questionId, answer.trim());
      const timeout = Date.now() + 240_000;
      while (result.status === "PENDING" && Date.now() < timeout) {
        await new Promise<void>((resolve) => window.setTimeout(resolve, 2_000));
        result = await interviewsApi.evaluationStatus(session.id, q.questionId);
      }
      if (result.status === "PENDING") throw new Error("Bài đang chờ chấm. Bạn có thể tải lại kết quả bằng nút gửi.");
      if (!result.evaluation) throw new Error("Chấm điểm thất bại. Hãy gửi lại câu trả lời.");
      setEvaluation(result.evaluation);
      const [s,report] = await Promise.all([interviewsApi.getSession(session.id),interviewsApi.summary(session.id)]);
      setSession(s);setSummary(report);setHistoryData(await interviewsApi.mine());toast("Đã lưu kết quả đánh giá");
    } catch(e) { toast(e instanceof Error ? e.message : "Đánh giá thất bại"); }
    finally { setBusy(false); }
  }
  function next() {
    if(!session||!evaluation) return;
    dictation.cancel();
    setIdx(session.currentIndex);setAnswer("");setLastAnswer(null);setEvaluation(null);
  }
  function exit() {
    dictation.cancel();
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
              <h2 style={{ fontSize: 22 }}>{linkedApplication ? "Phỏng vấn theo đơn ứng tuyển" : "Tự luyện"}</h2>
              {linkedApplication && <p className="small muted">Nhà tuyển dụng phụ trách tin có thể xem kết quả phiên này.</p>}
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
              <button type="submit" className="btn btn-p" disabled={busy}>{busy ? "Đang tạo…" : linkedApplication ? "Bắt đầu phỏng vấn" : "Bắt đầu phiên luyện"}</button>
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
                  <textarea id="iv-answer" className="input" style={{ minHeight: 220 }} maxLength={ANSWER_LIMIT}
                    readOnly={dictating || busy} value={displayedAnswer} onChange={(e) => setAnswer(e.target.value)} />
                  <div className="between">
                    <button type="button" className="btn btn-g btn-sm" onClick={dictation.toggle}
                      disabled={!dictation.supported || busy || dictation.phase === "stopping" || dictation.phase === "connecting" || (!dictating && answer.length >= ANSWER_LIMIT)}>
                      {dictation.phase === "connecting" ? "Đang kết nối…" : dictation.phase === "stopping" ? "Đang hoàn tất…" : dictating ? "Dừng nói" : "Trả lời bằng giọng nói"}
                    </button>
                    <span className="help">{displayedAnswer.length}/{ANSWER_LIMIT} ký tự</span>
                  </div>
                  <p className="help" role="status">
                    {!dictation.supported ? "Trình duyệt này chưa hỗ trợ nhận dạng giọng nói. Bạn vẫn có thể gõ câu trả lời."
                      : dictation.phase === "listening" ? "Đang nghe tiếng Việt và tiếng Anh…"
                      : dictation.message || "Khi bật micro, âm thanh được gửi tới Deepgram để chép lời."}
                  </p>
                </div>
              )}
              <div className="row" style={{ justifyContent: "flex-end" }}>
                {evaluation ? (
                  <button type="button" className="btn btn-p" onClick={next} disabled={busy}>Câu tiếp theo</button>
                ) : (
                  <button type="button" className="btn btn-p" onClick={submit} disabled={busy || dictating}>
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

            </section>
          ) : null}

          {done && summary ? (() => {
            const qById = new Map((session?.questions ?? []).map((x) => [x.questionId, x]));
            const topics = new Map<string, number[]>();
            for (const ev of summary.evaluations) {
              const t = qById.get(ev.questionId)?.topic || "Khác";
              topics.set(t, [...(topics.get(t) ?? []), Number(ev.predictedScore)]);
            }
            const frequency = new Map<string, number>();
            for (const result of summary.evaluations) {
              for (const point of new Set(result.missingPoints)) frequency.set(point, (frequency.get(point) ?? 0) + 1);
            }
            const review = [...frequency.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5);
            const weakest = [...topics.entries()].map(([topic, values]) => ({
              topic,
              average: values.reduce((sum, value) => sum + value, 0) / values.length,
            })).sort((a, b) => a.average - b.average)[0];
            const retry = [...summary.evaluations].filter((item) => item.missingPoints.length > 0)
              .sort((a, b) => Number(a.predictedScore) - Number(b.predictedScore)).slice(0, 3);
            return (
              <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
                <section className="card" style={{ padding: 32, display: "flex", gap: 32, flexWrap: "wrap", alignItems: "center" }}>
                  <div style={{ flex: "0 0 auto", textAlign: "center" }}>
                    <p className="disp" style={{ fontSize: 72, color: "var(--brand)", lineHeight: 1 }}>{score(summary.averageScore)}</p>
                    <p className="small muted">điểm trung bình / 10</p>
                  </div>
                  <div style={{ flex: "1 1 380px", display: "flex", flexDirection: "column", gap: 10 }}>
                    <div className="row" style={{ gap: 8 }}>
                      <span className={summary.answeredQuestions >= summary.totalQuestions ? "badge b-ok" : "badge b-gold"}>
                        {summary.answeredQuestions >= summary.totalQuestions ? "Hoàn thành" : "Chưa xong"}
                      </span>
                      <span className="badge b-plain">{summary.answeredQuestions}/{summary.totalQuestions} câu đã chấm</span>
                    </div>
                    <h1 style={{ fontSize: 28 }}>{session?.jobTitle || "Phiên luyện tập"}</h1>
                    <p style={{ color: "var(--ink-soft)" }}>Điểm luyện tập do AI chấm tự động, dùng để tự đánh giá và ôn tập.</p>
                  </div>
                  <div className="row" style={{ flex: "0 0 auto", flexDirection: "column", alignItems: "stretch" }}>
                    <button type="button" className="btn btn-p" onClick={start} disabled={busy}>Luyện lại phiên mới</button>
                    <button type="button" className="btn btn-g" onClick={exit}>Về trang phỏng vấn</button>
                  </div>
                </section>

                <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 300px), 1fr))", gap: 16 }}>
                  <div className="card stack" style={{ gap: 10 }}>
                    <h3 style={{ fontSize: 18 }}>Theo chủ đề</h3>
                    {[...topics].map(([t, xs]) => {
                      const avg = xs.reduce((a, b) => a + b, 0) / xs.length;
                      return (
                        <div key={t} style={{ display: "grid", gridTemplateColumns: "110px 1fr 40px", gap: 10, alignItems: "center", fontSize: 14 }}>
                          <span>{t}</span>
                          <div className="meter"><span style={{ width: `${Math.max(0, Math.min(100, avg * 10))}%` }} /></div>
                          <strong style={{ textAlign: "right" }}>{score(avg)}</strong>
                        </div>
                      );
                    })}
                  </div>
                  <div className="card stack" style={{ gap: 10 }}>
                    <h3 style={{ fontSize: 18 }}>Nên ôn thêm</h3>
                    {weakest && <p className="small">Điểm thấp nhất · <strong>{weakest.topic}</strong> ({score(weakest.average)}/10)</p>}
                    {review.length ? (
                      <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 6, fontSize: 14, color: "var(--ink-soft)" }}>
                        {review.map(([point, count]) => <li key={point}>{point} · {count} câu còn thiếu</li>)}
                      </ul>
                    ) : <p className="small muted">Không ghi nhận ý còn thiếu.</p>}
                    {retry.length > 0 && (
                      <div>
                        <strong>Câu nên luyện lại</strong>
                        <ol style={{ paddingLeft: 18 }}>
                          {retry.map((item) => <li key={item.questionId}>{qById.get(item.questionId)?.questionText ?? `Câu #${item.questionId}`}</li>)}
                        </ol>
                      </div>
                    )}
                  </div>
                </section>

                <section className="stack" style={{ gap: 10 }}>
                  <h2 style={{ fontSize: 22 }}>Chi tiết từng câu</h2>
                  {summary.evaluations.map((item, i) => {
                    const q = qById.get(item.questionId);
                    return (
                      <details key={item.responseId} className="card" style={{ padding: 0 }} open={i === 0}>
                        <summary style={{ display: "flex", gap: 16, alignItems: "center", padding: "16px 20px", cursor: "pointer", flexWrap: "wrap" }}>
                          <span className="disp" style={{ fontSize: 22, color: "var(--brand)", width: 52 }}>{score(item.predictedScore)}</span>
                          <span style={{ flex: "1 1 320px", fontWeight: 600 }}>{q?.questionText ?? `Câu ${i + 1}`}</span>
                          {q?.topic ? <span className="badge b-plain">{q.topic}</span> : null}
                        </summary>
                        <div style={{ padding: "0 20px 18px 88px", display: "grid", gap: 8, fontSize: 14 }}>
                          <p><strong style={{ color: "var(--ok)" }}>Đã nêu:</strong> {item.coveredPoints.join("; ") || "—"}</p>
                          <p><strong style={{ color: "var(--hot)" }}>Còn thiếu:</strong> {item.missingPoints.join("; ") || "Không ghi nhận ý thiếu."}</p>
                          {item.comment ? <p className="muted">{item.comment}</p> : null}
                        </div>
                      </details>
                    );
                  })}
                </section>
              </div>
            );
          })() : null}
        </main>
      </div>
    </>
  );
}
