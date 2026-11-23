import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Button, Chat, ChatBubble, EmptyNote, EvalBlock, Field, Grid2, Page, PageHead, Panel, SiteHeader, SplitActions, TextTextarea } from "../../components/common";
import { interviewsApi, type EvaluationDto, type SessionDto, type SessionSummaryDto } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import type { InterviewEvaluation } from "../../types";

const STATUS: Record<string,string> = { CREATED:"Mới tạo", IN_PROGRESS:"Đang làm", COMPLETED:"Đã hoàn thành" };
export function CandidateInterviewPage() {
  const { toast } = useToast();
  const [params] = useSearchParams();
  const jobId = Number(params.get("jobId"));
  const [session,setSession] = useState<SessionDto|null>(null);
  const [history,setHistory] = useState<SessionDto[]>([]);
  const [summary,setSummary] = useState<SessionSummaryDto|null>(null);
  const [idx,setIdx] = useState(0);
  const [answer,setAnswer] = useState("");
  const [lastAnswer,setLastAnswer] = useState<string|null>(null);
  const [evaluation,setEvaluation] = useState<EvaluationDto|null>(null);
  const [busy,setBusy] = useState(false);
  useEffect(() => { interviewsApi.mine().then(setHistory).catch(e => toast(e.message)); },[toast]);
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
      const s = await interviewsApi.createSession({ ...(Number.isFinite(jobId)&&jobId>0 ? {jobId}:{}),questionCount:6 });
      setSession(s);setIdx(s.currentIndex);setSummary(null);setAnswer("");setLastAnswer(null);setEvaluation(null);
      setHistory(await interviewsApi.mine());
    } catch(e) { toast(e instanceof Error ? e.message : "Không tạo được phiên"); }
    finally { setBusy(false); }
  }
  async function submit() {
    if(!session||!q||!answer.trim()) { toast("Hãy nhập câu trả lời");return; }
    setBusy(true);setLastAnswer(answer.trim());
    try {
      const ev = await interviewsApi.submit(session.id,q.questionId,answer.trim());setEvaluation(ev);
      const [s,report] = await Promise.all([interviewsApi.getSession(session.id),interviewsApi.summary(session.id)]);
      setSession(s);setSummary(report);setHistory(await interviewsApi.mine());toast("Đã lưu kết quả đánh giá");
    } catch(e) { toast(e instanceof Error ? e.message : "Đánh giá thất bại"); }
    finally { setBusy(false); }
  }
  function next() {
    if(!session||!evaluation) return;
    setIdx(session.currentIndex);setAnswer("");setLastAnswer(null);setEvaluation(null);
  }
  const ev:InterviewEvaluation|null = evaluation ? {
    bertPrecision:Number(evaluation.bertscorePrecision??0),bertRecall:Number(evaluation.bertscoreRecall??0),
    bertF1:Number(evaluation.bertscoreF1??0),predictedScore:Number(evaluation.predictedScore),scoreScale:evaluation.scoreScale,
    coveredPoints:evaluation.coveredPoints,missingPoints:evaluation.missingPoints,comment:evaluation.comment??"",
    modelVersion:evaluation.modelVersion??evaluation.evaluationMethod,scoringMode:evaluation.scoringMode,
    coverageScore:evaluation.coverageScore,criterionResults:evaluation.criterionResults??[],
  }:null;
  return <>
    <SiteHeader active="interview" mode="candidate" />
    <Page>
      <PageHead title="Luyện phỏng vấn" description={session ? `${session.jobTitle??"Luyện tập theo hồ sơ"} · ${STATUS[session.status]}` : "6 câu được chọn theo kỹ năng JD, CV và cấp độ; có tính đến các câu đã gặp gần đây."}
        actions={<Button variant="primary" onClick={start} disabled={busy}>{busy?"Đang xử lý…":session?"Tạo phiên mới":"Bắt đầu phiên 6 câu"}</Button>} />
      {history.length>0 && <Panel><h2>Phiên gần đây</h2><div className="job-tags">{history.slice(0,5).map(s=><Button key={s.id} variant="ghost" disabled={busy} onClick={()=>openSession(s.id)}>
        #{s.id} · {s.jobTitle??"Luyện tập"} · {STATUS[s.status]}
      </Button>)}</div></Panel>}
      <Grid2>
        <Panel>
          <h2>{q?`Câu ${idx+1}/${session?.questions.length} · ${q.topic??""} · ${q.difficulty??""}`:session?.status==="COMPLETED"?"Đã hoàn thành phiên":"Câu hỏi"}</h2>
          <Chat>{q?<ChatBubble role="ai" meta="Người phỏng vấn">{q.questionText}</ChatBubble>:<EmptyNote>{session?.status==="COMPLETED"?"Bạn đã trả lời toàn bộ câu hỏi. Xem tổng kết hoặc tạo phiên mới.":"Nhấn bắt đầu để tạo phiên hoặc mở lại một phiên đang làm."}</EmptyNote>}
            {lastAnswer&&<ChatBubble role="user" meta="Bạn">{lastAnswer}</ChatBubble>}
          </Chat>
          {q&&<><Field label="Câu trả lời của bạn"><TextTextarea rows={5} maxLength={4000} value={answer} onChange={e=>setAnswer(e.target.value)} /></Field>
            <SplitActions>
              <Button variant="primary" onClick={submit} disabled={busy||session?.status==="COMPLETED"}>{busy?"Đang chấm…":"Gửi & nhận đánh giá"}</Button>
              <Button variant="ghost" onClick={next} disabled={busy||!evaluation}>{session?.status==="COMPLETED"?"Xem tổng kết":"Câu tiếp theo"}</Button>
            </SplitActions></>}
        </Panel>
        <Panel><h2>Kết quả đánh giá</h2>{ev?<EvalBlock evaluation={ev}/>:<EmptyNote>Điểm luyện tập 0–10, kèm bằng chứng theo từng tiêu chí. Điểm tương đồng không phải xác nhận mọi phát biểu đều đúng.</EmptyNote>}
          {summary&&<section><h3>Tổng kết phiên</h3><p>{summary.answeredQuestions}/{summary.totalQuestions} câu đã chấm · Trung bình {summary.averageScore==null?"—":Number(summary.averageScore).toFixed(2)}/10</p>
            {summary.evaluations.map((item,index)=><details key={item.responseId}><summary>Câu {index+1} · {Number(item.predictedScore).toFixed(1)}/10 · {item.scoringMode}</summary>
              <p>{item.comment}</p><p>Cần bổ sung: {item.missingPoints.join("; ")||"Không ghi nhận ý thiếu."}</p></details>)}
          </section>}
        </Panel>
      </Grid2>
    </Page>
  </>;
}
