import { useEffect, useMemo, useState } from "react";
import { EmptyNote, RecruiterLayout } from "../../components/common";
import { MAX_PAGE_SIZE, interviewsApi, type QuestionDto } from "../../api/client";
import { useToast } from "../../context/ToastContext";

/** Màn AD05 · Ngân hàng câu hỏi (design canvas QuestionBank.dc.html), chế độ chỉ xem. */

const DIFF_CLS: Record<string, string> = { Hard: "badge b-danger", Medium: "badge b-gold", Easy: "badge b-ok" };

export function RecruiterInterviewsPage() {
  const { toast } = useToast();
  const [questions, setQuestions] = useState<QuestionDto[] | null>(null);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    interviewsApi
      .questions({ size: MAX_PAGE_SIZE })
      .then((p) => { setQuestions(p.content); setTotal(p.totalElements); })
      .catch((e) => { setQuestions([]); toast(e.message); });
  }, [toast]);

  const topics = useMemo(
    () => [...new Set((questions ?? []).map((x) => x.topic).filter((x): x is string => !!x))].sort(),
    [questions]
  );
  const levels = useMemo(
    () => [...new Set((questions ?? []).map((x) => x.difficulty).filter((x): x is string => !!x))],
    [questions]
  );
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (questions ?? []).filter((x) =>
      (!needle || x.questionText.toLowerCase().includes(needle))
      && (!topic || x.topic === topic)
      && (!level || x.difficulty === level));
  }, [questions, q, topic, level]);

  const selected = shown.find((x) => x.id === selectedId) ?? shown[0] ?? null;

  return (
    <RecruiterLayout active="interviews">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1 style={{ fontSize: 32 }}>Ngân hàng câu hỏi</h1>
          <p className="muted">
            {total} câu · {topics.length} chủ đề. Dùng cho phiên luyện và đánh giá phỏng vấn. Nhà tuyển dụng chỉ xem.
          </p>
        </div>
      </div>

      <div className="row">
        <input className="input" type="search" placeholder="Tìm nội dung câu hỏi" aria-label="Tìm câu hỏi"
          value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: "1 1 240px", maxWidth: 320 }} />
        <select className="input" aria-label="Chủ đề" style={{ width: "auto" }} value={topic} onChange={(e) => setTopic(e.target.value)}>
          <option value="">Mọi chủ đề</option>
          {topics.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select className="input" aria-label="Cấp độ" style={{ width: "auto" }} value={level} onChange={(e) => setLevel(e.target.value)}>
          <option value="">Mọi cấp độ</option>
          {levels.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      {questions === null ? (
        <p className="muted">Đang tải…</p>
      ) : shown.length === 0 ? (
        <EmptyNote>{questions.length === 0 ? "Chưa có câu hỏi trong hệ thống." : "Không có câu hỏi khớp bộ lọc."}</EmptyNote>
      ) : (
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
          <div className="tbl-box" style={{ flex: "1 1 480px", minWidth: 0 }}>
            <table className="tbl" style={{ minWidth: 520 }}>
              <thead><tr><th>Câu hỏi</th><th>Chủ đề</th><th>Cấp</th></tr></thead>
              <tbody>
                {shown.map((x) => (
                  <tr key={x.id} onClick={() => setSelectedId(x.id)} aria-selected={selected?.id === x.id}
                    style={{ cursor: "pointer", background: selected?.id === x.id ? "var(--brand-soft)" : undefined }}>
                    <td style={{ maxWidth: 320 }}>
                      <button type="button" onClick={() => setSelectedId(x.id)}
                        style={{ all: "unset", cursor: "pointer", fontWeight: 600, fontSize: 13.5 }}>
                        {x.questionText}
                      </button>
                      {x.skill ? <p className="tiny muted">{x.skill}</p> : null}
                    </td>
                    <td className="small">{x.topic ?? "—"}</td>
                    <td>{x.difficulty ? <span className={DIFF_CLS[x.difficulty] ?? "badge"}>{x.difficulty}</span> : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selected ? (
            <section className="card" style={{ flex: "1 1 420px", minWidth: 0, display: "flex", flexDirection: "column", gap: 14, padding: 24 }}>
              <div className="between">
                <h3 style={{ fontSize: 18 }}>Chi tiết câu hỏi</h3>
                {selected.difficulty ? <span className={DIFF_CLS[selected.difficulty] ?? "badge"}>{selected.difficulty}</span> : null}
              </div>
              <div>
                <p className="lbl">Nội dung câu hỏi</p>
                <p style={{ marginTop: 6 }}>{selected.questionText}</p>
              </div>
              <div className="row" style={{ gap: "6px 20px", fontSize: 14 }}>
                <span><span className="muted">Chủ đề:</span> {selected.topic ?? "—"}</span>
                {selected.skill ? <span><span className="muted">Kỹ năng:</span> {selected.skill}</span> : null}
              </div>
              {selected.referenceAnswer ? (
                <div>
                  <p className="lbl">Đáp án tham khảo</p>
                  <p className="small" style={{ marginTop: 6, color: "var(--ink-soft)", whiteSpace: "pre-line" }}>{selected.referenceAnswer}</p>
                </div>
              ) : null}
              {selected.rubricLabels.length ? (
                <div>
                  <p className="lbl">Rubric ({selected.rubricLabels.length} tiêu chí)</p>
                  <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
                    {selected.rubricLabels.map((r) => (
                      <div key={r} style={{ border: "1px solid var(--line)", padding: "10px 14px", background: "var(--surface)", fontSize: 14 }}>{r}</div>
                    ))}
                  </div>
                </div>
              ) : null}
            </section>
          ) : null}
        </div>
      )}
    </RecruiterLayout>
  );
}
