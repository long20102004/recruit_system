package recruit.demo.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/** Một field hồ sơ CV (danh sách trong setting CV_FIELD) và các dòng giá trị của nó. */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CvFieldValue {
    private String field;
    private List<String> values;
}
