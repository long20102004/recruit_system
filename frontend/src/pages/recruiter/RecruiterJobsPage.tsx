import { useEffect, useState, type FormEvent } from "react";
import {
  Button,
  EmptyNote,
  Field,
  Grid2,
  JobCard,
  JobList,
  Page,
  PageHead,
  Panel,
  SiteHeader,
  TextInput,
  TextSelect,
  TextTextarea,
} from "../../components/common";
import { jobsApi, type JobDto } from "../../api/client";
import { useToast } from "../../context/ToastContext";
import { mapJob } from "../../utils/mappers";

export function RecruiterJobsPage() {
  const { toast } = useToast();
  const [jobs, setJobs] = useState<JobDto[]>([]);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    title: "",
    level: "Junior",
    workType: "Hybrid",
    location: "",
    city: "TP. Hồ Chí Minh",
    salary: "",
    required: "",
    preferred: "",
    description: "",
    requirements: "",
    responsibilities: "",
  });

  async function load() {
    setJobs(await jobsApi.mine());
  }

  useEffect(() => {
    load().catch((e) => toast(e.message));
  }, [toast]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await jobsApi.create({
        title: form.title,
        description: form.description || form.title,
        location: form.location,
        city: form.city,
        workType: form.workType,
        level: form.level,
        salaryText: form.salary,
        status: "PUBLISHED",
        requiredSkills: form.required
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        preferredSkills: form.preferred
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        requirements: form.requirements,
        responsibilities: form.responsibilities,
      });
      toast("Đã đăng tin tuyển dụng");
      setForm((f) => ({ ...f, title: "", description: "", requirements: "", responsibilities: "" }));
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Đăng tin thất bại");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <SiteHeader active="jobs" mode="recruiter" />
      <Page>
        <PageHead
          title="Đăng & quản lý tin tuyển dụng"
          description="Đăng vị trí, yêu cầu và kỹ năng. Tin sẽ hiện trên trang tìm việc của ứng viên."
        />

        <Grid2>
          <Panel>
            <h2>Tin đang mở</h2>
            <JobList>
              {jobs.length === 0 ? (
                <EmptyNote>Chưa có tin nào.</EmptyNote>
              ) : (
                jobs.map((j, i) => (
                  <JobCard key={j.id} job={mapJob(j)} delayMs={i * 40} />
                ))
              )}
            </JobList>
          </Panel>

          <Panel>
            <h2>Đăng vị trí mới</h2>
            <form onSubmit={onSubmit}>
              <Field label="Vị trí / tiêu đề tin">
                <TextInput
                  required
                  value={form.title}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                  placeholder="Tên vị trí"
                />
              </Field>
              <Field label="Cấp bậc">
                <TextSelect
                  value={form.level}
                  onChange={(e) => setForm({ ...form, level: e.target.value })}
                >
                  <option>Intern</option>
                  <option>Fresher</option>
                  <option>Junior</option>
                  <option>Mid</option>
                </TextSelect>
              </Field>
              <Field label="Hình thức">
                <TextSelect
                  value={form.workType}
                  onChange={(e) =>
                    setForm({ ...form, workType: e.target.value })
                  }
                >
                  <option>Tại văn phòng</option>
                  <option>Hybrid</option>
                  <option>Remote</option>
                </TextSelect>
              </Field>
              <Field label="Địa điểm">
                <TextInput
                  value={form.location}
                  onChange={(e) =>
                    setForm({ ...form, location: e.target.value })
                  }
                  placeholder="Quận, thành phố"
                />
              </Field>
              <Field label="Thành phố (lọc)">
                <TextSelect
                  value={form.city}
                  onChange={(e) => setForm({ ...form, city: e.target.value })}
                >
                  <option>TP. Hồ Chí Minh</option>
                  <option>Hà Nội</option>
                  <option>Remote</option>
                </TextSelect>
              </Field>
              <Field label="Mức lương">
                <TextInput
                  value={form.salary}
                  onChange={(e) => setForm({ ...form, salary: e.target.value })}
                  placeholder="Thỏa thuận hoặc khoảng lương"
                />
              </Field>
              <Field label="Kỹ năng bắt buộc (phẩy)">
                <TextInput
                  required
                  value={form.required}
                  onChange={(e) =>
                    setForm({ ...form, required: e.target.value })
                  }
                  placeholder="Các kỹ năng bắt buộc, cách nhau bởi dấu phẩy"
                />
              </Field>
              <Field label="Kỹ năng ưu tiên (phẩy)">
                <TextInput
                  value={form.preferred}
                  onChange={(e) =>
                    setForm({ ...form, preferred: e.target.value })
                  }
                  placeholder="Các kỹ năng ưu tiên, cách nhau bởi dấu phẩy"
                />
              </Field>
              <Field label="Mô tả công việc">
                <TextTextarea
                  rows={4}
                  required
                  value={form.description}
                  onChange={(e) =>
                    setForm({ ...form, description: e.target.value })
                  }
                  placeholder="Mô tả trách nhiệm, yêu cầu và quyền lợi"
                />
              </Field>
              <Field label="Trách nhiệm công việc (mỗi dòng một ý)">
                <TextTextarea
                  rows={4}
                  value={form.responsibilities}
                  onChange={(e) =>
                    setForm({ ...form, responsibilities: e.target.value })
                  }
                  placeholder={"Phát triển REST API bằng Spring Boot\nTối ưu truy vấn cơ sở dữ liệu"}
                />
              </Field>
              <Field label="Yêu cầu ứng viên (mỗi dòng một ý)">
                <TextTextarea
                  rows={3}
                  value={form.requirements}
                  onChange={(e) =>
                    setForm({ ...form, requirements: e.target.value })
                  }
                  placeholder={"Ít nhất 1 năm kinh nghiệm Java\nHiểu biết về Docker"}
                />
              </Field>
              <p className="muted">Mỗi dòng một ý giúp ghép hồ sơ chính xác hơn.</p>
              <Button variant="primary" block type="submit" disabled={busy}>
                {busy ? "Đang đăng…" : "Đăng tin"}
              </Button>
            </form>
          </Panel>
        </Grid2>
      </Page>
    </>
  );
}
