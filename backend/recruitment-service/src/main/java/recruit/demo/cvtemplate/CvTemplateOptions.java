package recruit.demo.cvtemplate;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Set;

/** Hằng số bảng tuỳ chọn mẫu CONFIG và danh sách ký hiệu mẫu DOCX. */
public final class CvTemplateOptions {

    private CvTemplateOptions() {}

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class OptionItem {
        private String value;
        private String label;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class PlaceholderItem {
        private String tag;
        private String description;
        private String scope;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    public static class OptionsResponse {
        private List<OptionItem> layouts;
        private List<OptionItem> fonts;
        private List<OptionItem> accents;
        private List<OptionItem> backgrounds;
        private List<OptionItem> headers;
        private List<OptionItem> headings;
        private List<OptionItem> dates;
        private List<OptionItem> densities;
        private List<OptionItem> margins;
        private List<OptionItem> sections;
        private List<PlaceholderItem> docxPlaceholders;
    }

    public static final List<OptionItem> LAYOUTS = List.of(
            new OptionItem("ONE_COLUMN", "Một cột"),
            new OptionItem("TWO_COLUMN", "Hai cột")
    );

    public static final List<OptionItem> FONTS = List.of(
            new OptionItem("Tinos", "Tinos (Serif · cổ điển)"),
            new OptionItem("Be Vietnam Pro", "Be Vietnam Pro (Sans · hiện đại)"),
            new OptionItem("Inter", "Inter (Sans · tối giản ATS)"),
            new OptionItem("EB Garamond", "EB Garamond (Serif · học thuật)"),
            new OptionItem("Noto Serif", "Noto Serif (Serif · sắc nét)")
    );

    public static final List<OptionItem> ACCENTS = List.of(
            new OptionItem("#1f1d1a", "Đen (không nhấn)"),
            new OptionItem("#2f4cb8", "Xanh dương HireLens"),
            new OptionItem("#243a92", "Xanh navy"),
            new OptionItem("#2f6237", "Xanh rêu"),
            new OptionItem("#8a4527", "Nâu đất"),
            new OptionItem("#963226", "Đỏ gạch")
    );

    public static final List<OptionItem> BACKGROUNDS = List.of(
            new OptionItem("#ffffff", "Trắng tinh"),
            new OptionItem("#fffdf9", "Giấy kem nhạt"),
            new OptionItem("#f8f9fc", "Xanh xám rất nhạt")
    );

    public static final List<OptionItem> HEADERS = List.of(
            new OptionItem("LEFT", "Căn trái"),
            new OptionItem("CENTER", "Căn giữa (Harvard)")
    );

    public static final List<OptionItem> HEADINGS = List.of(
            new OptionItem("UPPERCASE_RULE", "Chữ hoa + đường gạch ngang"),
            new OptionItem("ACCENT", "Chữ màu nhấn + vạch trái"),
            new OptionItem("PLAIN", "Chữ đậm tối giản")
    );

    public static final List<OptionItem> DATES = List.of(
            new OptionItem("RIGHT_INLINE", "Cùng dòng, căn phải"),
            new OptionItem("BELOW", "Dòng phụ bên dưới")
    );

    public static final List<OptionItem> DENSITIES = List.of(
            new OptionItem("COMPACT", "Gọn (nhiều thông tin)"),
            new OptionItem("NORMAL", "Thoáng vừa")
    );

    public static final List<OptionItem> MARGINS = List.of(
            new OptionItem("NARROW", "Hẹp (10mm)"),
            new OptionItem("NORMAL", "Tiêu chuẩn (14mm)"),
            new OptionItem("WIDE", "Rộng (18mm)")
    );

    public static final List<OptionItem> SECTIONS = List.of(
            new OptionItem("info", "Thông tin cá nhân"),
            new OptionItem("objective", "Mục tiêu nghề nghiệp"),
            new OptionItem("education", "Học vấn"),
            new OptionItem("experience", "Kinh nghiệm làm việc"),
            new OptionItem("projects", "Dự án cá nhân"),
            new OptionItem("skills", "Kỹ năng"),
            new OptionItem("certificates", "Chứng chỉ"),
            new OptionItem("languages", "Ngoại ngữ"),
            new OptionItem("honours", "Giải thưởng & hoạt động")
    );

    public static final Set<String> VALID_LAYOUTS = Set.of("ONE_COLUMN", "TWO_COLUMN");
    public static final Set<String> VALID_FONTS = Set.of("Tinos", "Be Vietnam Pro", "Inter", "EB Garamond", "Noto Serif");
    public static final Set<String> VALID_ACCENTS = Set.of("#1f1d1a", "#2f4cb8", "#243a92", "#2f6237", "#8a4527", "#963226");
    public static final Set<String> VALID_BACKGROUNDS = Set.of("#ffffff", "#fffdf9", "#f8f9fc");
    public static final Set<String> VALID_HEADERS = Set.of("LEFT", "CENTER");
    public static final Set<String> VALID_HEADINGS = Set.of("UPPERCASE_RULE", "ACCENT", "PLAIN");
    public static final Set<String> VALID_DATES = Set.of("RIGHT_INLINE", "BELOW");
    public static final Set<String> VALID_DENSITIES = Set.of("COMPACT", "NORMAL");
    public static final Set<String> VALID_MARGINS = Set.of("NARROW", "NORMAL", "WIDE");
    public static final Set<String> VALID_SECTIONS = Set.of(
            "info", "objective", "education", "experience", "projects",
            "skills", "certificates", "languages", "honours"
    );

    public static final List<PlaceholderItem> DOCX_PLACEHOLDERS = List.of(
            new PlaceholderItem("{{full_name}}", "Họ và tên ứng viên", "ROOT"),
            new PlaceholderItem("{{title}}", "Tiêu đề CV", "ROOT"),
            new PlaceholderItem("{{email}}", "Email liên hệ", "ROOT"),
            new PlaceholderItem("{{phone}}", "Số điện thoại", "ROOT"),
            new PlaceholderItem("{{github}}", "Đường dẫn GitHub", "ROOT"),
            new PlaceholderItem("{{objective}}", "Mục tiêu nghề nghiệp", "ROOT"),
            new PlaceholderItem("{{skills_text}}", "Kỹ năng nối bằng dấu phẩy", "ROOT"),
            new PlaceholderItem("{{certificates_text}}", "Chứng chỉ nối dòng", "ROOT"),
            new PlaceholderItem("{{honours_text}}", "Giải thưởng & hoạt động nối dòng", "ROOT"),
            new PlaceholderItem("{{?experience}}...{{/experience}}", "Khối lặp kinh nghiệm làm việc", "SECTION"),
            new PlaceholderItem("{{job_title}}, {{company}}, {{location}}, {{start_date}}, {{end_date}}, {{description}}", "Trường trong khối experience", "experience"),
            new PlaceholderItem("{{?education}}...{{/education}}", "Khối lặp học vấn", "SECTION"),
            new PlaceholderItem("{{school}}, {{major}}, {{location}}, {{start_year}}, {{end_year}}, {{gpa}}", "Trường trong khối education", "education"),
            new PlaceholderItem("{{?projects}}...{{/projects}}", "Khối lặp dự án cá nhân", "SECTION"),
            new PlaceholderItem("{{name}}, {{role}}, {{team_size}}, {{start_date}}, {{end_date}}, {{github_url}}, {{tech_stack}}, {{description}}", "Trường trong khối projects", "projects"),
            new PlaceholderItem("{{?languages}}...{{/languages}}", "Khối lặp ngoại ngữ", "SECTION"),
            new PlaceholderItem("{{language}}, {{note}}", "Trường trong khối languages", "languages"),
            new PlaceholderItem("{{?skills}} {{value}} {{/skills}}", "Danh sách lặp kỹ năng", "skills"),
            new PlaceholderItem("{{?certificates}} {{value}} {{/certificates}}", "Danh sách lặp chứng chỉ", "certificates"),
            new PlaceholderItem("{{?honours}} {{value}} {{/honours}}", "Danh sách lặp giải thưởng", "honours")
    );

    public static final Set<String> SUPPORTED_DOCX_TAGS = Set.of(
            "full_name", "title", "email", "phone", "github", "objective",
            "skills_text", "certificates_text", "honours_text",
            "experience", "job_title", "company", "location", "start_date", "end_date", "description",
            "education", "school", "major", "start_year", "end_year", "gpa",
            "projects", "name", "role", "team_size", "github_url", "tech_stack",
            "languages", "language", "note",
            "skills", "certificates", "honours", "value"
    );

    public static OptionsResponse optionsResponse() {
        return new OptionsResponse(
                LAYOUTS, FONTS, ACCENTS, BACKGROUNDS, HEADERS,
                HEADINGS, DATES, DENSITIES, MARGINS, SECTIONS, DOCX_PLACEHOLDERS
        );
    }
}
