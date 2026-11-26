import { useEffect, useMemo, useState, type FormEvent } from "react";
import { EmptyNote, MockNote, RecruiterLayout } from "../../components/common";
import { useToast } from "../../context/ToastContext";
import {
  QUESTION_LEVELS,
  QUESTION_TYPES,
  questionBankMock,
  type BankQuestion,
  type BankQuestionInput,
  type QuestionType,
  type RubricCriterion,
} from "../../api/mock/questionBankMock";

/** Màn AD05 · Ngân hàng câu hỏi cho admin (design canvas QuestionBank.dc.html). */

const emptyCriterion = (): RubricCriterion => ({ name: "", weight: 0, points: "", keywords: "", misconceptions: "" });

const emptyDraft = (): BankQuestionInput => ({
  questionText: "",
  topic: "",
  level: "Junior",
  type: "Kiến thức",
  referenceAnswer: "",
  rubric: [{ ...emptyCriterion(), weight: 100 }],
});

const toDraft = (q: BankQuestion): BankQuestionInput => ({
  questionText: q.questionText,
  topic: q.topic,
  level: q.level,
  type: q.type,
  referenceAnswer: q.referenceAnswer,
  rubric: q.rubric.map((r) => ({ ...r })),
});

export function AdminQuestionBankPage() {
  const { toast } = useToast();
  const [items, setItems] = useState<BankQuestion[] | null>(null);
  const [q, setQ] = useState("");
  const [topic, setTopic] = useState("");
  const [level, setLevel] = useState("");
  const [review, setReview] = useState<"" | "pending" | "approved">("");
  /** null = đang thêm câu hỏi mới. */
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState<BankQuestionInput>(emptyDraft);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    questionBankMock.list()
      .then((list) => {
        setItems(list);
        if (list[0]) { setEditingId(list[0].id); setDraft(toDraft(list[0])); }
      })
      .catch((e) => { setItems([]); toast(e instanceof Error ? e.message : "Không tải được câu hỏi"); });
  }, [toast]);

  const topics = useMemo(() => [...new Set((items ?? []).map((x) => x.topic))].sort(), [items]);
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return (items ?? []).filter((x) =>
      (!needle || x.questionText.toLowerCase().includes(needle))
      && (!topic || x.topic === topic)
      && (!level || x.level === level)
      && (!review || (review === "approved") === x.approved));
  }, [items, q, topic, level, review]);

  const editing = editingId == null ? null : (items ?? []).find((x) => x.id === editingId) ?? null;
  const totalWeight = draft.rubric.reduce((s, r) => s + (Number(r.weight) || 0), 0);

  function replace(updated: BankQuestion) {
    setItems((xs) => (xs ?? []).map((x) => (x.id === updated.id ? updated : x)));
  }

  function select(x: BankQuestion) {
    setEditingId(x.id);
    setDraft(toDraft(x));
    setError(null);
  }

  function startNew() {
    setEditingId(null);
    setDraft(emptyDraft());
    setError(null);
  }

  const setRubric = (i: number, patch: Partial<RubricCriterion>) =>
    setDraft((d) => ({ ...d, rubric: d.rubric.map((r, j) => (j === i ? { ...r, ...patch } : r)) }));

  async function onSave(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (editingId == null) {
        const created = await questionBankMock.create(draft);
        setItems((xs) => [created, ...(xs ?? [])]);
        setEditingId(created.id);
        toast("Đã thêm câu hỏi, chờ chuyên gia duyệt");
      } else {
        replace(await questionBankMock.update(editingId, draft));
        toast("Đã lưu câu hỏi. Câu hỏi đã sửa cần duyệt lại.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không lưu được câu hỏi");
    } finally {
      setBusy(false);
    }
  }

  async function toggleEnabled(x: BankQuestion) {
    try {
      replace(await questionBankMock.setEnabled(x.id, !x.enabled));
      toast(x.enabled ? "Đã tắt câu hỏi" : "Đã bật câu hỏi");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Không cập nhật được");
    }
  }

  async function toggleApproved(x: BankQuestion) {
    try {
      replace(await questionBankMock.setApproved(x.id, !x.approved));
      toast(x.approved ? "Đã chuyển về Cần duyệt" : "Đã đánh dấu đã duyệt");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Không cập nhật được");
    }
  }

  return (
    <RecruiterLayout active="questions">
      <div className="page-head" style={{ marginBottom: 0 }}>
        <div>
          <h1 style={{ fontSize: 32 }}>Ngân hàng câu hỏi</h1>
          <p className="muted">
            {items ? `${items.length} câu · ${topics.length} chủ đề · rubric theo tiêu chí. Nhà tuyển dụng chỉ xem.` : "Đang tải…"}
          </p>
        </div>
        <button type="button" className="btn btn-p" onClick={startNew}>+ Thêm câu hỏi</button>
      </div>
      <MockNote>Danh sách câu hỏi lấy từ API; thêm, sửa, duyệt, bật/tắt và rubric chi tiết chưa có API nên chỉ lưu tạm.</MockNote>

      <div className="row">
        <input className="input" type="search" placeholder="Tìm nội dung câu hỏi" aria-label="Tìm câu hỏi"
          value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: "1 1 240px", maxWidth: 320 }} />
        <select className="input" aria-label="Chủ đề" style={{ width: "auto" }} value={topic} onChange={(e) => setTopic(e.target.value)}>
          <option value="">Mọi chủ đề</option>
          {topics.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select className="input" aria-label="Cấp độ" style={{ width: "auto" }} value={level} onChange={(e) => setLevel(e.target.value)}>
          <option value="">Mọi cấp độ</option>
          {QUESTION_LEVELS.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select className="input" aria-label="Duyệt" style={{ width: "auto" }} value={review}
          onChange={(e) => setReview(e.target.value as "" | "pending" | "approved")}>
          <option value="">Mọi trạng thái duyệt</option>
          <option value="pending">Cần chuyên gia duyệt</option>
          <option value="approved">Đã duyệt</option>
        </select>
      </div>

      {items === null ? (
        <p className="muted">Đang tải…</p>
      ) : (
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap", alignItems: "flex-start" }}>
          <div className="tbl-box" style={{ flex: "1 1 480px", minWidth: 0 }}>
            {shown.length === 0 ? (
              <EmptyNote>Không có câu hỏi khớp bộ lọc.</EmptyNote>
            ) : (
              <table className="tbl" style={{ minWidth: 560 }}>
                <thead><tr><th>Câu hỏi</th><th>Chủ đề</th><th>Cấp</th><th>Duyệt</th><th>Bật</th></tr></thead>
                <tbody>
                  {shown.map((x) => (
                    <tr key={x.id} style={{ background: x.id === editingId ? "var(--brand-soft)" : undefined, opacity: x.enabled ? 1 : 0.6 }}>
                      <td style={{ maxWidth: 300 }}>
                        <button type="button" onClick={() => select(x)}
                          style={{ all: "unset", cursor: "pointer", fontWeight: 600, fontSize: 13.5 }}>
                          {x.questionText}
                        </button>
                        <p className="tiny muted">{x.type}</p>
                      </td>
                      <td className="small">{x.topic}</td>
                      <td className="small">{x.level}</td>
                      <td><span className={x.approved ? "badge b-ok" : "badge b-warn"}>{x.approved ? "Đã duyệt" : "Cần duyệt"}</span></td>
                      <td>
                        <input type="checkbox" checked={x.enabled} aria-label={`Bật câu hỏi: ${x.questionText}`}
                          onChange={() => toggleEnabled(x)} style={{ width: 18, height: 18, accentColor: "var(--brand)" }} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <form className="card" onSubmit={onSave}
            style={{ flex: "1 1 460px", minWidth: 0, display: "flex", flexDirection: "column", gap: 14, padding: 24 }}>
            <div className="between">
              <h3 style={{ fontSize: 18 }}>{editingId == null ? "Thêm câu hỏi" : "Sửa câu hỏi"}</h3>
              {editing ? (
                <span className={editing.approved ? "badge b-ok" : "badge b-warn"}>
                  {editing.approved ? "Đã duyệt" : "Cần chuyên gia duyệt"}
                </span>
              ) : null}
            </div>
            <div className="field">
              <label htmlFor="qb-text">Nội dung câu hỏi</label>
              <textarea id="qb-text" className="input" style={{ minHeight: 80 }} value={draft.questionText}
                onChange={(e) => setDraft({ ...draft, questionText: e.target.value })} />
            </div>
            <div className="form-grid" style={{ gridTemplateColumns: "repeat(3, minmax(0, 1fr))" }}>
              <div className="field">
                <label htmlFor="qb-topic">Chủ đề</label>
                <input id="qb-topic" className="input" list="qb-topics" value={draft.topic}
                  onChange={(e) => setDraft({ ...draft, topic: e.target.value })} />
                <datalist id="qb-topics">{topics.map((t) => <option key={t} value={t} />)}</datalist>
              </div>
              <div className="field">
                <label htmlFor="qb-level">Cấp độ</label>
                <select id="qb-level" className="input" value={draft.level} onChange={(e) => setDraft({ ...draft, level: e.target.value })}>
                  {QUESTION_LEVELS.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="field">
                <label htmlFor="qb-type">Dạng</label>
                <select id="qb-type" className="input" value={draft.type}
                  onChange={(e) => setDraft({ ...draft, type: e.target.value as QuestionType })}>
                  {QUESTION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>
            <div className="field">
              <label htmlFor="qb-answer">Đáp án tham khảo</label>
              <textarea id="qb-answer" className="input" value={draft.referenceAnswer}
                onChange={(e) => setDraft({ ...draft, referenceAnswer: e.target.value })} />
            </div>

            <div className="between">
              <p className="lbl">
                Rubric (tổng trọng số{" "}
                <span style={{ color: totalWeight === 100 ? "var(--ok)" : "var(--danger)" }}>{totalWeight}%</span>)
              </p>
              <button type="button" className="btn btn-link small"
                onClick={() => setDraft({ ...draft, rubric: [...draft.rubric, emptyCriterion()] })}>
                + Tiêu chí
              </button>
            </div>
            {draft.rubric.map((r, i) => (
              <div key={i} style={{ border: "1px solid var(--line)", padding: 14, display: "grid", gap: 10, background: "var(--surface)" }}>
                <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 90px auto", gap: 10, alignItems: "center" }}>
                  <input className="input" placeholder="Tên tiêu chí" aria-label={`Tên tiêu chí ${i + 1}`} value={r.name}
                    onChange={(e) => setRubric(i, { name: e.target.value })} />
                  <input className="input" type="number" min={0} max={100} aria-label={`Trọng số tiêu chí ${i + 1} (%)`}
                    value={r.weight} onChange={(e) => setRubric(i, { weight: Number(e.target.value) })} />
                  <button type="button" className="btn btn-link small" aria-label={`Xoá tiêu chí ${i + 1}`}
                    disabled={draft.rubric.length === 1}
                    onClick={() => setDraft({ ...draft, rubric: draft.rubric.filter((_, j) => j !== i) })}>×</button>
                </div>
                <input className="input" placeholder="Ý đúng" aria-label={`Ý đúng tiêu chí ${i + 1}`} value={r.points}
                  onChange={(e) => setRubric(i, { points: e.target.value })} />
                <input className="input" placeholder="Từ khoá gợi ý" aria-label={`Từ khoá tiêu chí ${i + 1}`} value={r.keywords}
                  onChange={(e) => setRubric(i, { keywords: e.target.value })} />
                <input className="input" placeholder="Ngộ nhận cần phát hiện" aria-label={`Ngộ nhận tiêu chí ${i + 1}`}
                  value={r.misconceptions} onChange={(e) => setRubric(i, { misconceptions: e.target.value })} />
              </div>
            ))}

            {error ? <p className="note note-warn small" role="alert">{error}</p> : null}
            <div className="row" style={{ justifyContent: "space-between" }}>
              {editing ? (
                <button type="button" className={editing.enabled ? "btn btn-d btn-sm" : "btn btn-g btn-sm"}
                  onClick={() => toggleEnabled(editing)}>
                  {editing.enabled ? "Tắt câu hỏi" : "Bật câu hỏi"}
                </button>
              ) : <span />}
              <div className="row" style={{ gap: 8 }}>
                {editing ? (
                  <button type="button" className="btn btn-g" onClick={() => toggleApproved(editing)}>
                    {editing.approved ? "Bỏ duyệt" : "Đánh dấu đã duyệt"}
                  </button>
                ) : null}
                <button type="submit" className="btn btn-p" disabled={busy}>{busy ? "Đang lưu…" : "Lưu"}</button>
              </div>
            </div>
          </form>
        </div>
      )}
    </RecruiterLayout>
  );
}
