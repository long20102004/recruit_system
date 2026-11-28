import { useState, type FormEvent } from "react";
import { cvsApi, type DiscoverableCvDto, type PageDto } from "../../api/client";
import { Pager } from "../../components/common";

export function DiscoverableCvSearch() {
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PageDto<DiscoverableCvDto> | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function search(text: string, page: number) {
    setBusy(true);
    setError("");
    setResults(null);
    try {
      setResults(await cvsApi.search(text, page));
      setQuery(text);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Không tìm được CV");
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void search(draft.trim(), 0);
  }

  return (
    <section className="card stack">
      <h2>Tìm CV ứng viên đang mở tìm việc</h2>
      <form className="row" onSubmit={submit}>
        <input className="input" aria-label="Kỹ năng hoặc mô tả" placeholder="Kỹ năng hoặc mô tả"
          value={draft} onChange={(event) => setDraft(event.target.value)} minLength={2} maxLength={120} required />
        <button type="submit" className="btn btn-p" disabled={busy}>{busy ? "Đang tìm…" : "Tìm CV"}</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {results?.totalElements === 0 && <p className="muted">Không có CV phù hợp.</p>}
      {results?.content.map((item) => (
        <article key={item.id} className="card stack" style={{ gap: 6 }}>
          <strong>CV #{item.id}</strong>
          {item.yearsOfExperience != null && <p>{item.yearsOfExperience} năm kinh nghiệm</p>}
          <p className="small">{item.skills.join(", ")}</p>
        </article>
      ))}
      {results && <Pager data={results} onPage={(page) => void search(query, page)} />}
    </section>
  );
}
