import { useEffect, useState } from "react";
import {
  Button,
  EmptyNote,
  Page,
  PageHead,
  Panel,
  SiteHeader,
  SplitActions,
  Table,
} from "../../components/common";
import { applicationsApi, type ApplicationDto } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { applicationStatusLabel } from "../../utils/mappers";

export function RecruiterCandidatesPage() {
  const { toast } = useToast();
  const [apps, setApps] = useState<ApplicationDto[]>([]);

  useEffect(() => {
    applicationsApi
      .recruiter()
      .then(setApps)
      .catch((e) => toast(e.message));
  }, [toast]);

  return (
    <>
      <SiteHeader active="candidates" mode="recruiter" />
      <Page>
        <PageHead
          title="Hồ sơ ứng viên"
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
                {apps.map((a) => (
                  <tr key={a.id}>
                    <td>{a.candidateName}</td>
                    <td>{a.jobTitle}</td>
                    <td>{a.companyName}</td>
                    <td>{applicationStatusLabel(a.status)}</td>
                    <td>{new Date(a.appliedAt).toLocaleDateString("vi-VN")}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
          <SplitActions>
            <Button variant="soft" size="sm" to="/recruiter/matching">
              Ghép hồ sơ
            </Button>
            <Button variant="ghost" size="sm" to="/recruiter/interviews">
              Phỏng vấn
            </Button>
          </SplitActions>
        </Panel>
      </Page>
    </>
  );
}
