import { useEffect, useState } from "react";
import {
  Button,
  EmptyNote,
  Field,
  Grid2,
  Page,
  PageHead,
  Panel,
  SiteHeader,
  SplitActions,
  Step,
  Steps,
  TextInput,
  TextTextarea,
  UploadZone,
} from "../../components/common";
import { cvsApi, type CvFormDto } from "../../api/client";
import { useToast } from "../../context/ToastContext";

const LONG_FIELDS = new Set(["Tóm tắt", "Học vấn", "Kinh nghiệm", "Chứng chỉ"]);
const HEADER_FIELDS = ["Họ tên", "Email", "Điện thoại"];

function cleanLines(lines: string[] | undefined): string[] {
  return (lines ?? [])
    .flatMap((line) => line.split(/\r?\n/))
    .map((line) => line.trim())
    .filter(Boolean);
}

function valuesFrom(form: CvFormDto) {
  return Object.fromEntries(
    form.fields.map((item) => {
      const lines = cleanLines(item.values);
      return [item.field, lines.length ? lines : [""]];
    })
  );
}

function FieldLines({
  lines,
  long,
  onChange,
}: {
  lines: string[];
  long: boolean;
  onChange: (lines: string[]) => void;
}) {
  const shown = lines.length ? lines : [""];

  function update(index: number, text: string) {
    const parts = text.split(/\r?\n/);
    const next = [...shown.slice(0, index), ...parts, ...shown.slice(index + 1)];
    onChange(next.length ? next : [""]);
  }

  if (shown.length >= 2) {
    return (
      <ul className="cv-lines">
        {shown.map((line, index) => (
          <li key={index}>
            {long ? (
              <TextTextarea rows={2} value={line} onChange={(e) => update(index, e.target.value)} />
            ) : (
              <TextInput value={line} onChange={(e) => update(index, e.target.value)} />
            )}
          </li>
        ))}
      </ul>
    );
  }

  return long ? (
    <TextTextarea rows={3} value={shown[0] ?? ""} onChange={(e) => update(0, e.target.value)} />
  ) : (
    <TextInput value={shown[0] ?? ""} onChange={(e) => update(0, e.target.value)} />
  );
}

function LineView({ lines }: { lines: string[] }) {
  const visible = cleanLines(lines);
  if (visible.length >= 2) {
    return (
      <ul className="cv-lines">
        {visible.map((line, index) => (
          <li key={`${index}-${line}`}>{line}</li>
        ))}
      </ul>
    );
  }
  return <p>{visible[0] || "Chưa có thông tin."}</p>;
}

export function CandidateCvPage() {
  const { toast } = useToast();
  const [step, setStep] = useState(1);
  const [fileName, setFileName] = useState("Chưa chọn file");
  const [fields, setFields] = useState<string[]>([]);
  const [values, setValues] = useState<Record<string, string[]>>({});
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);

  function applyForm(form: CvFormDto, nextStep?: number) {
    setFields(form.fields.map((item) => item.field));
    setValues(valuesFrom(form));
    setFileName(form.fileName || "Chưa chọn file");
    if (nextStep != null) {
      setStep(nextStep);
    } else {
      setStep(form.analyzed ? 3 : form.fileName ? 2 : 1);
    }
  }

  useEffect(() => {
    cvsApi
      .mine()
      .then((form) => applyForm(form))
      .catch(() => undefined)
      .finally(() => setLoaded(true));
  }, []);

  async function onUpload(file: File) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      toast("Chỉ nhận file PDF");
      return;
    }
    setBusy(true);
    try {
      const form = await cvsApi.upload(file);
      applyForm(form, 2);
      toast("Đã tải CV và điền các mục hồ sơ. Hãy kiểm tra trước khi xác nhận.");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Upload thất bại");
    } finally {
      setBusy(false);
    }
  }

  async function onConfirm() {
    if (!fileName || fileName === "Chưa chọn file") {
      toast("Hãy tải CV trước");
      return;
    }
    setBusy(true);
    try {
      const form = await cvsApi.confirm(
        fields.map((field) => ({ field, values: cleanLines(values[field]) }))
      );
      applyForm(form, 3);
      toast("Đã xác nhận hồ sơ");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Xác nhận thất bại");
    } finally {
      setBusy(false);
    }
  }

  function setField(field: string, lines: string[]) {
    setValues((current) => ({ ...current, [field]: lines }));
  }

  if (!loaded) {
    return (
      <>
        <SiteHeader active="cv" mode="candidate" />
        <Page>
          <EmptyNote>Đang tải hồ sơ…</EmptyNote>
        </Page>
      </>
    );
  }

  if (step === 3) {
    const nameLines = cleanLines(values["Họ tên"]);
    const emailLines = cleanLines(values["Email"]);
    const phoneLines = cleanLines(values["Điện thoại"]);
    const name = nameLines[0] || "Ứng viên";
    const contact = [
      emailLines.length < 2 ? emailLines[0] : "",
      phoneLines.length < 2 ? phoneLines[0] : "",
    ]
      .filter(Boolean)
      .join(" · ");
    const hasContact = emailLines.length > 0 || phoneLines.length > 0;
    const repeatedInHeader = new Set(
      HEADER_FIELDS.filter((field) => cleanLines(values[field]).length < 2)
    );

    return (
      <>
        <SiteHeader active="cv" mode="candidate" />
        <Page>
          <PageHead
            title="Hồ sơ của bạn"
            description="Thông tin này được dùng khi xếp hạng việc làm phù hợp."
          />
          <Panel>
            <article className="cv-profile">
              <header>
                <h2>{name}</h2>
                {contact || !hasContact ? (
                  <p className="contact">{contact || "Chưa có liên hệ"}</p>
                ) : null}
              </header>
              {fields
                .filter((field) => !repeatedInHeader.has(field))
                .map((field) => (
                  <section key={field}>
                    <h3>{field}</h3>
                    <LineView lines={values[field] ?? []} />
                  </section>
                ))}
              <SplitActions>
                <Button variant="primary" onClick={() => setStep(2)}>
                  Cập nhật hồ sơ
                </Button>
                <Button variant="ghost" to="/candidate/matching">
                  Xem việc phù hợp
                </Button>
              </SplitActions>
            </article>
          </Panel>
        </Page>
      </>
    );
  }

  return (
    <>
      <SiteHeader active="cv" mode="candidate" />
      <Page>
        <PageHead
          title="Hồ sơ & phân tích CV"
          description="Tải CV định dạng PDF. Các mục hiện ra theo danh sách field trong cấu hình."
        />

        <Steps>
          <Step status={step === 1 ? "active" : "done"}>1. Tải lên</Step>
          <Step status={step === 2 ? "active" : "idle"}>2. Kiểm tra</Step>
          <Step status="idle">3. Xác nhận</Step>
        </Steps>

        <Grid2>
          <Panel>
            <h2>Tải tài liệu</h2>
            <UploadZone onFile={onUpload} />
            <p className="hint">{fileName}</p>
            <SplitActions>
              <Button
                variant="ghost"
                onClick={() => {
                  setStep(1);
                  setFileName("Chưa chọn file");
                }}
              >
                Tải file khác
              </Button>
            </SplitActions>
          </Panel>

          <Panel>
            {step === 1 ? (
              <EmptyNote>Tải CV để hệ thống điền các mục, rồi kiểm tra trước khi xác nhận.</EmptyNote>
            ) : (
              <div className="cv-sheet">
                {fields.map((field) => (
                  <Field key={field} label={field}>
                    {field === "Kỹ năng suy ra" ? (
                      <p>Suy ra từ đồ thị kỹ năng, tách khỏi kỹ năng ghi trên CV.</p>
                    ) : null}
                    <FieldLines
                      lines={values[field] ?? [""]}
                      long={LONG_FIELDS.has(field)}
                      onChange={(lines) => setField(field, lines)}
                    />
                  </Field>
                ))}
              </div>
            )}
            <SplitActions>
              <Button variant="accent" onClick={onConfirm} disabled={busy || step < 2}>
                Xác nhận hồ sơ
              </Button>
            </SplitActions>
          </Panel>
        </Grid2>
      </Page>
    </>
  );
}
