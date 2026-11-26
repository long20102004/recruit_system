package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.entity.Setting;
import recruit.demo.repository.SettingRepository;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

@Service
@RequiredArgsConstructor
public class SettingService {

    public static final String CV_FIELD = "CV_FIELD";
    public static final String DEFAULT_CV_FIELDS =
            "Họ tên,Email,Điện thoại,GitHub,Tóm tắt,Kỹ năng,Kỹ năng suy ra,Học vấn,Kinh nghiệm,Mô tả kinh nghiệm,"
            + "Dự án,Chứng chỉ,Giải thưởng,Ngoại ngữ";
    public static final String IMPLIED_SKILL_FIELD = "Kỹ năng suy ra";

    private final SettingRepository settingRepository;

    @Transactional
    public List<String> cvFields() {
        List<Setting> rows = settingRepository.findByName(CV_FIELD);
        Setting setting;
        if (rows.isEmpty()) {
            setting = settingRepository.save(Setting.builder()
                    .name(CV_FIELD)
                    .value(DEFAULT_CV_FIELDS)
                    .build());
        } else {
            setting = rows.get(0);
        }
        if (setting.getValue() == null || setting.getValue().isBlank()) {
            return List.of();
        }
        List<String> fields = new ArrayList<>(splitCsv(setting.getValue()));
        if (!fields.contains(IMPLIED_SKILL_FIELD)) {
            int skill = fields.indexOf("Kỹ năng");
            fields.add(skill < 0 ? fields.size() : skill + 1, IMPLIED_SKILL_FIELD);
            setting.setValue(String.join(",", fields));
            settingRepository.save(setting);
        }
        return fields;
    }

    private List<String> splitCsv(String raw) {
        if (raw == null || raw.isBlank()) {
            return List.of();
        }
        return Arrays.stream(raw.split(","))
                .map(String::trim)
                .filter(field -> !field.isEmpty())
                .toList();
    }
}
