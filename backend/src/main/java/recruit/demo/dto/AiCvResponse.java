package recruit.demo.dto;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class AiCvResponse {
    private CandidateProfile data;
    private String detail;
    private String error;
}
