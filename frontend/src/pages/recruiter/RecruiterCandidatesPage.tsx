import { useEffect, useState } from "react";
import {
  Button,
  EmptyNote,
  Pager,
  PageHead,
  Panel,
  RecruiterLayout,
  SplitActions,
  Table,
} from "../../components/common";
import { applicationsApi, type ApplicationDto, type PageDto } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { applicationBadge, initials, shortDate } from "../../utils/format";

export function RecruiterCandidatesPage() {
  const { toast } = useToast();
  const [page, setPage] = useState(0);
  const [data, setData] = useState<PageDto<ApplicationDto> | null>(null);
  const apps = data?.content ?? [];

  useEffect(() => {
    applicationsApi
      .recruiter({ page })
      .then(setData)
      .catch((e) => toast(e.message));
  }, [toast, page]);

  return (
    <RecruiterLayout active="candidates">
        <PageHead
          title="Đơn ứng tuyển"
          description="Danh sách đơn ứng tuyển vào các tin bạn đang quản lý."
        />
        <Panel>
          {apps.length === 0 ? (
            <EmptyNote>Chưa có ứng viên nộp hồ sơ.</EmptyNote>
          ) : (
            <Table>
              <thead>
                <tr>
                  <th>Ứng viên</th>
                  <th>Vị trí</th>
                  <th>Công ty</th>
                  <th>Trạng thái</th>
                  <th>Ngày nộp</th>
                </tr>
              </thead>
              <tbody>
                {apps.map((a) => {
                  const b = applicationBadge(a.status);
                  return (
                    <tr key={a.id}>
                      <td>
                        <div className="row" style={{ gap: 10, flexWrap: "nowrap" }}>
                          <span className="avatar">{initials(a.candidateName)}</span>
                          <span style={{ fontWeight: 650 }}>{a.candidateName}</span>
                        </div>
                      </td>
                      <td className="small">{a.jobTitle}</td>
                      <td className="small">{a.companyName}</td>
                      <td><span className={b.cls}>{b.label}</span></td>
                      <td className="small muted">{shortDate(a.appliedAt)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>
          )}
          <Pager data={data} onPage={setPage} />
          <SplitActions>
            <Button variant="soft" size="sm" to="/recruiter/matching">
              Ghép hồ sơ
            </Button>
            <Button variant="ghost" size="sm" to="/recruiter/interviews">
              Phỏng vấn
            </Button>
          </SplitActions>
        </Panel>
    </RecruiterLayout>
  );
}
