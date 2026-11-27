package recruit.demo.cvtemplate;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/** Cấu hình trình bày cho mẫu CV loại CONFIG. */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class CvTemplateConfig {
    private String layout;
    private String font;
    private String accent;
    private String background;
    private String header;
    private String heading;
    private String dates;
    private String density;
    private String margin;
    private List<String> sections;
}
