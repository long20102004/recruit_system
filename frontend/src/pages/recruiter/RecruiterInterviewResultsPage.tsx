import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { applicationsApi, type ApplicationDto, type PageDto } from "../../api/client";
import { EmptyNote, Pager, RecruiterLayout, Table } from "../../components/common";

export function RecruiterInterviewResultsPage() {
  const [page, setPage] = useState(0);
  const [results, setResults] = useState<PageDto<ApplicationDto> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    applicationsApi.recruiter({ page, resultsOnly: true }).then(
      (data) => {
        if (active) { setResults(data); setError(""); }
      },
      (failure) => {
        if (active) { setResults(null); setError(failure instanceof Error ? failure.message : "Không tải được kết quả"); }
      },
    );
    return () => { active = false; };
  }, [page]);

  return (
    <RecruiterLayout active="interviewResults">
      <h1>Kết quả phỏng vấn</h1>
      {error ? <p role="alert">{error}</p> : results == null ? (
        <p role="status">Đang tải kết quả…</p>
      ) : results.totalElements === 0 ? (
        <EmptyNote>Chưa có đơn ứng tuyển nào có kết quả phỏng vấn.</EmptyNote>
      ) : (
        <>
          <Table>
            <thead><tr><th>Ứng viên</th><th>Vị trí</th><th>Điểm phỏng vấn</th><th /></tr></thead>
            <tbody>
              {results.content.map((item) => (
                <tr key={item.id}>
                  <td>{item.candidateName}</td>
                  <td>{item.jobTitle}</td>
                  <td>{item.interviewScore?.toLocaleString("vi-VN", { maximumFractionDigits: 2 })}/10</td>
                  <td><Link to={`/recruiter/candidates/${item.id}?tab=interview`}>Xem phiên</Link></td>
                </tr>
              ))}
            </tbody>
          </Table>
          <Pager data={results} onPage={(next) => { setResults(null); setPage(next); }} />
        </>
      )}
    </RecruiterLayout>
  );
}
