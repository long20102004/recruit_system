import { useEffect, useState } from "react";
import {
  EmptyNote,
  PageHead,
  Panel,
  RecruiterLayout,
  Table,
} from "../../components/common";
import { interviewsApi, type QuestionDto } from "../../api/client";
import { useToast } from "../../context/ToastContext";

export function RecruiterInterviewsPage() {
  const { toast } = useToast();
  const [questions, setQuestions] = useState<QuestionDto[]>([]);

  useEffect(() => {
    interviewsApi
      .questions()
      .then(setQuestions)
      .catch((e) => toast(e.message));
  }, [toast]);

  return (
    <RecruiterLayout active="interviews">
        <PageHead
          title="Ngân hàng câu hỏi & phỏng vấn"
          description="Danh sách câu hỏi dùng cho phiên luyện và đánh giá phỏng vấn."
        />
        <Panel>
          {questions.length === 0 ? (
            <EmptyNote>Chưa có câu hỏi trong hệ thống.</EmptyNote>
          ) : (
            <Table>
              <thead>
                <tr>
                  <th>Chủ đề</th>
                  <th>Độ khó</th>
                  <th>Kỹ năng</th>
                  <th>Câu hỏi</th>
                </tr>
              </thead>
              <tbody>
                {questions.map((q) => (
                  <tr key={q.id}>
                    <td>{q.topic}</td>
                    <td>
                      <span className={`badge b-plain ${q.difficulty === "Hard" ? "b-danger" : q.difficulty === "Medium" ? "b-gold" : "b-ok"}`}>
                        {q.difficulty}
                      </span>
                    </td>
                    <td>{q.skill}</td>
                    <td>{q.questionText}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Panel>
    </RecruiterLayout>
  );
}
