package recruit.demo.service;

import java.util.List;
import java.util.Set;
import recruit.demo.dto.ServiceDtos.InterviewContext;
import recruit.demo.entity.InterviewQuestion;

public interface QuestionSelectionService {
    List<InterviewQuestion> select(List<InterviewQuestion> pool, InterviewContext context, Set<Integer> recent, int count);
}
