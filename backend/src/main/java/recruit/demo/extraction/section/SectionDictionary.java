package recruit.demo.extraction.section;

import java.text.Normalizer;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Từ điển tiêu đề section tiếng Việt/tiếng Anh (Giai đoạn 2).
 *
 * <p>Khóa đã chuẩn hóa: in hoa, bỏ dấu câu thừa và số thứ tự đầu dòng.
 * Subsection (ví dụ NGOẠI NGỮ trong KỸ NĂNG KHÁC) được ánh xạ trực tiếp về
 * section chuẩn của nó.
 */
public final class SectionDictionary {

    private static final Map<String, CvSection> HEADINGS = new java.util.LinkedHashMap<>();

    static {
        reg(CvSection.OBJECTIVE,
                "MỤC TIÊU NGHỀ NGHIỆP", "MỤC TIÊU", "TÓM TẮT", "GIỚI THIỆU BẢN THÂN",
                "OBJECTIVE", "CAREER OBJECTIVE", "SUMMARY", "PROFILE", "ABOUT ME");
        reg(CvSection.EDUCATION,
                "HỌC VẤN", "GIÁO DỤC", "TRÌNH ĐỘ HỌC VẤN", "QUÁ TRÌNH HỌC TẬP",
                "HỌC TẬP", "BẰNG CẤP",
                "EDUCATION", "ACADEMIC BACKGROUND", "ACADEMIC QUALIFICATIONS");
        reg(CvSection.EXPERIENCE,
                "KINH NGHIỆM LÀM VIỆC", "KINH NGHIỆM", "QUÁ TRÌNH CÔNG VIỆC",
                "QUÁ TRÌNH LÀM VIỆC", "LỊCH SỬ LÀM VIỆC",
                "WORK EXPERIENCE", "EXPERIENCE", "EMPLOYMENT HISTORY",
                "PROFESSIONAL EXPERIENCE", "WORK HISTORY");
        reg(CvSection.PROJECTS,
                "DỰ ÁN CÁ NHÂN", "DỰ ÁN TIÊU BIỂU", "DỰ ÁN", "DỰ ÁN THỰC HIỆN",
                "DỰ ÁN NỔI BẬT", "SẢN PHẨM CÁ NHÂN",
                "PROJECTS", "PERSONAL PROJECTS", "SIDE PROJECTS", "SELECTED PROJECTS",
                "PET PROJECTS");
        reg(CvSection.SKILLS,
                "KỸ NĂNG CHUYÊN MÔN", "KỸ NĂNG KHÁC", "KỸ NĂNG MỀM", "KỸ NĂNG",
                "NĂNG LỰC CHUYÊN MÔN", "CHUYÊN MÔN", "KỸ THUẬT VÀ CÔNG CỤ",
                "TECHNICAL SKILLS", "TECHNICAL SKILL", "SKILLS", "CORE SKILLS", "TECH STACK",
                "COMPETENCIES", "KEY SKILLS");
        reg(CvSection.CERTIFICATES,
                "CHỨNG CHỈ", "CHỨNG NHẬN", "BẰNG CẤP CHỨNG CHỈ",
                "CERTIFICATES", "CERTIFICATIONS", "LICENSES");
        reg(CvSection.HONOURS,
                "GIẢI THƯỞNG", "THÀNH TÍCH", "DANH HIỆU", "KHEN THƯỞNG",
                "HOẠT ĐỘNG NGOẠI KHÓA", "AWARDS", "HONORS", "HONOURS",
                "HONOURS & ACHIEVEMENTS", "HONORS & ACHIEVEMENTS", "HONOURS AND ACHIEVEMENTS",
                "ACHIEVEMENTS", "ACTIVITIES");
        reg(CvSection.LANGUAGES,
                "NGOẠI NGỮ", "NGOẠI NGỮ TIẾNG ANH", "NGÔN NGỮ", "TRÌNH ĐỘ NGOẠI NGỮ",
                "LANGUAGES", "FOREIGN LANGUAGES", "LANGUAGE SKILLS");
        reg(CvSection.REFERENCES,
                "THAM KHẢO", "NGƯỜI THAM CHIẾU", "THÔNG TIN THAM KHẢO",
                "REFERENCES", "REFEREES");
    }

    private static void reg(CvSection section, String... headings) {
        for (String h : headings) {
            HEADINGS.put(normalizeHeading(h), section);
        }
    }

    private SectionDictionary() {
    }

    /** Chuẩn hóa một dòng để so khớp tiêu đề. */
    public static String normalizeHeading(String line) {
        if (line == null) {
            return "";
        }
        String s = line.strip();
        // Bỏ số thứ tự đầu dòng ("1. ", "I. ", "A. ")
        s = s.replaceAll("^[0-9IVX]+[.)]\\s+", "");
        // Bỏ dấu hai chấm cuối và bullet đầu dòng
        s = s.replaceAll("^[•◦▪▫○●\\-\\*+]+\\s*", "");
        s = s.replaceAll("[:：]+$", "").strip();
        // Bỏ dấu để so khớp không dấu
        String noAccent = Normalizer.normalize(s, Normalizer.Form.NFD)
                .replaceAll("\\p{M}", "");
        return noAccent.toUpperCase().replaceAll("\\s+", " ").trim();
    }

    /** Tiêu đề thuộc vùng header/contact — giữ section hiện tại là HEADER. */
    public static final java.util.Set<String> HEADER_HEADINGS = java.util.Set.of(
            "THONG TIN LIEN HE", "LIEN HE", "CONTACT", "CONTACT INFORMATION",
            "THONG TIN CA NHAN", "PERSONAL INFORMATION", "PERSONAL DETAILS");

    /** So khớp chính xác sau chuẩn hóa (kể cả bản không dấu). */
    public static Optional<CvSection> lookup(String line) {
        String key = normalizeHeading(line);
        if (key.isEmpty() || key.length() > 48) {
            return Optional.empty();
        }
        if (HEADER_HEADINGS.contains(key)) {
            return Optional.of(CvSection.HEADER);
        }
        CvSection hit = HEADINGS.get(key);
        return Optional.ofNullable(hit);
    }

    public static Map<CvSection, List<String>> all() {
        Map<CvSection, List<String>> out = new EnumMap<>(CvSection.class);
        HEADINGS.forEach((k, v) -> out.computeIfAbsent(v, x -> new java.util.ArrayList<>()).add(k));
        return out;
    }
}
