package recruit.demo.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.util.List;

public final class QuestionBankDtos {
    private QuestionBankDtos() {}

    public record Criterion(@NotBlank @Size(max = 255) String name, @Min(1) @Max(100) int weight,
            @Size(max = 4000) String points, @Size(max = 2000) String keywords,
            @Size(max = 2000) String misconceptions) {}

    public record Input(@NotBlank @Size(max = 4000) String questionText, @NotBlank @Size(max = 120) String topic,
            @NotBlank String level, @NotBlank String type, @NotBlank @Size(max = 4000) String referenceAnswer,
            @NotEmpty @Size(max = 20) List<@NotNull @Valid Criterion> rubric) {}

    public record Question(Integer id, String questionText, String topic, String level, String type,
            String referenceAnswer, List<Criterion> rubric, boolean approved, boolean enabled) {}

    public record State(Boolean enabled, Boolean approved) {}
}
