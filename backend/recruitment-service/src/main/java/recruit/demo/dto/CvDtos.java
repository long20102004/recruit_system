package recruit.demo.dto;

import java.util.List;

public final class CvDtos {

    private CvDtos() {
    }

    public record FieldValue(String field, List<String> values) {
    }

    public record CvFormResponse(
            String fileName,
            String parsingStatus,
            boolean analyzed,
            List<FieldValue> fields
    ) {
    }

    public record ConfirmCvRequest(List<FieldValue> fields) {
    }
}
