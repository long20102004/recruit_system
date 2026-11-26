package recruit.demo.service.cvmatch;

import recruit.demo.entity.JobStatus;
import tools.jackson.databind.ObjectMapper;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;
import java.util.regex.Pattern;

/**
 * Dung JSON gui sang cvmatch (ham thuan, plan I05). CV = dau ra Module 1 ({@code extracted_profile}) + cac truong
 * nguoi dung da sua tren form; JD = bang {@code jobs} / {@code job_skills}. Ten truong theo schema Module 1, adapter
 * cua cvmatch doi sang ten noi bo.
 */
public final class CvMatchPayloads {
    public static final String JD_PREFIX = "job-";

    /** Truong do KG cua Module 1 them ({@code ?include=kg}): khong gui (KG doi khong duoc sinh version CV moi). */
    static final List<String> KG_FIELDS =
            List.of("skills_normalized", "implied_skills", "skills_detected", "related_skills", "flags");

    static final String F_SKILLS = "Kỹ năng";
    static final String F_SUMMARY = "Tóm tắt";
    static final String F_CERTS = "Chứng chỉ";
    static final String F_EXPERIENCE = "Kinh nghiệm";
    static final String F_EDUCATION = "Học vấn";
    /** Cach CvProfileMapper noi hai phan cua mot dong kinh nghiem / hoc van tren form. */
    static final String JOIN = " — ";

    private static final Pattern SKILL_SPLIT = Pattern.compile("[,;\\n]");
    private static final Pattern BULLET = Pattern.compile("^[-*•·+]+\\s*");

    private CvMatchPayloads() {
    }

    // ------------------------------------------------------------------------------------------- CV

    /**
     * @param extracted   dau ra Module 1 (da parse tu {@code extracted_profile})
     * @param form        truong form -> cac dong (chi truong co mat moi de len ban trich xuat)
     * @param accountEmail email tai khoan: cung ung vien qua moi lan tai CV (candidate_key cua cvmatch)
     * @param location    dia chi ung vien neu co
     */
    public static Map<String, Object> cvPayload(Map<String, Object> extracted, Map<String, List<String>> form,
                                                String accountEmail, String location) {
        Map<String, Object> cv = deepCopy(extracted == null ? Map.of() : extracted);
        KG_FIELDS.forEach(cv::remove);

        Map<String, Object> info = asMap(cv.get("personal_info"));
        if (accountEmail != null && !accountEmail.isBlank()) info.put("email", accountEmail.trim());
        cv.put("personal_info", info);
        if (location != null && !location.isBlank()) cv.put("location", location.trim());

        if (form.containsKey(F_SKILLS)) cv.put("skills", splitSkills(form.get(F_SKILLS)));
        if (form.containsKey(F_SUMMARY)) {
            String s = String.join("\n", clean(form.get(F_SUMMARY)));
            cv.put("objective", s.isBlank() ? null : s);
        }
        if (form.containsKey(F_CERTS)) cv.put("certificates", clean(form.get(F_CERTS)));
        if (form.containsKey(F_EXPERIENCE)) {
            cv.put("experience", mergeItems(asList(cv.get("experience")), clean(form.get(F_EXPERIENCE)),
                    "job_title", "company"));
        }
        if (form.containsKey(F_EDUCATION)) {
            cv.put("education", mergeItems(asList(cv.get("education")), clean(form.get(F_EDUCATION)),
                    "major", "school"));
        }
        return cv;
    }

    /**
     * Form la ban nguoi dung xac nhan: dong nao con thi muc do con. Cung so dong -> ghep theo thu tu, ghi de hai
     * truong hien tren form, GIU ngay thang cua ban trich xuat (form khong co o sua ngay). Khac so dong -> giu muc
     * trich xuat co dong y het, dong moi thanh muc khong co ngay.
     */
    static List<Map<String, Object>> mergeItems(List<Map<String, Object>> extracted, List<String> lines,
                                                String first, String second) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (lines.size() == extracted.size()) {
            for (int i = 0; i < lines.size(); i++) out.add(withLine(extracted.get(i), lines.get(i), first, second));
            return out;
        }
        boolean[] used = new boolean[extracted.size()];
        for (String line : lines) {
            int hit = -1;
            for (int i = 0; i < extracted.size(); i++) {
                if (!used[i] && joinOf(extracted.get(i), first, second).equals(withoutDetail(line).replaceFirst("^— ", ""))) {
                    hit = i;
                    break;
                }
            }
            if (hit >= 0) {
                used[hit] = true;
                out.add(deepCopy(extracted.get(hit)));
            } else {
                out.add(withLine(new LinkedHashMap<>(), line, first, second));
            }
        }
        return out;
    }

    private static Map<String, Object> withLine(Map<String, Object> item, String line, String first, String second) {
        Map<String, Object> m = deepCopy(item);
        line = withoutDetail(line);
        if (line.startsWith(JOIN.strip() + " ")) line = JOIN + line.substring(2);   // "— Công ty": thiếu vế đầu
        int k = line.indexOf(JOIN);
        String a = (k < 0 ? line : line.substring(0, k)).trim();
        String b = k < 0 ? null : line.substring(k + JOIN.length()).trim();
        m.put(first, a.isEmpty() ? null : a);
        if (k >= 0 || !m.containsKey(second)) m.put(second, b == null || b.isEmpty() ? null : b);
        return m;
    }

    /** Bỏ phần chi tiết (thời gian, GPA…) CvProfileMapper thêm sau " | ": chỉ vế "a — b" mới là dữ liệu form. */
    static String withoutDetail(String line) {
        int d = line.indexOf(recruit.demo.service.cv.CvProfileMapper.DETAIL);
        return d < 0 ? line : line.substring(0, d);
    }

    private static String joinOf(Map<String, Object> item, String first, String second) {
        List<String> parts = new ArrayList<>();
        for (String key : List.of(first, second)) {
            Object v = item.get(key);
            if (v != null && !v.toString().isBlank()) parts.add(v.toString().trim());
        }
        return String.join(JOIN, parts);
    }

    static List<String> splitSkills(List<String> lines) {
        LinkedHashSet<String> out = new LinkedHashSet<>();
        for (String line : lines == null ? List.<String>of() : lines) {
            if (line == null) continue;
            for (String part : SKILL_SPLIT.split(line)) {
                String s = part.trim();
                if (!s.isEmpty()) out.add(s);
            }
        }
        return new ArrayList<>(out);
    }

    // ------------------------------------------------------------------------------------------- JD

    public record JobSkillItem(String name, boolean required) {
    }

    /** JD JSON (khong co status: status gui rieng bang PATCH de doi status khong sinh version JD moi). */
    public static Map<String, Object> jdPayload(Integer jobId, String title, String companyIntro, String location,
                                                String employmentType, BigDecimal minYears, String description,
                                                String requirements, String responsibilities,
                                                List<JobSkillItem> skills) {
        Map<String, Object> jd = new LinkedHashMap<>();
        jd.put("jd_id", jdId(jobId));
        jd.put("title", title);
        if (notBlank(companyIntro)) jd.put("company_intro", companyIntro.trim());
        if (notBlank(location)) jd.put("location", location.trim());
        String mode = workMode(employmentType, location);
        if (mode != null) jd.put("work_mode", mode);
        if (minYears != null && minYears.signum() > 0) jd.put("min_years", minYears.doubleValue());
        List<Map<String, Object>> sk = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (JobSkillItem s : skills == null ? List.<JobSkillItem>of() : skills) {
            if (s.name() == null || s.name().isBlank() || !seen.add(s.name().trim().toLowerCase(Locale.ROOT))) continue;
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("name", s.name().trim());
            m.put("required", s.required());
            sk.add(m);
        }
        jd.put("skills", sk);
        jd.put("requirements", lines(requirements));
        List<String> resp = new ArrayList<>(lines(description));
        resp.addAll(lines(responsibilities));
        jd.put("responsibilities", resp);
        return jd;
    }

    public static String jdId(Integer jobId) {
        return JD_PREFIX + jobId;
    }

    public static Integer jobIdOf(String jdId) {
        if (jdId == null || !jdId.startsWith(JD_PREFIX)) return null;
        try {
            return Integer.valueOf(jdId.substring(JD_PREFIX.length()));
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    /** PUBLISHED -> open, DRAFT -> draft, CLOSED -> closed. */
    public static String jdStatus(JobStatus status) {
        if (status == null) return "draft";
        return switch (status) {
            case PUBLISHED -> "open";
            case CLOSED -> "closed";
            default -> "draft";
        };
    }

    static String workMode(String employmentType, String location) {
        String s = ((employmentType == null ? "" : employmentType) + " " + (location == null ? "" : location))
                .toLowerCase(Locale.ROOT);
        if (s.contains("hybrid") || s.contains("kết hợp")) return "hybrid";
        if (s.contains("remote") || s.contains("từ xa")) return "remote";
        if (s.contains("onsite") || s.contains("on-site") || s.contains("tại văn phòng")) return "onsite";
        return null;
    }

    static List<String> lines(String text) {
        List<String> out = new ArrayList<>();
        if (text == null) return out;
        for (String line : text.split("\\R")) {
            String s = BULLET.matcher(line.trim()).replaceFirst("").trim();
            if (!s.isEmpty()) out.add(s);
        }
        return out;
    }

    // ------------------------------------------------------------------------------------------- hash

    /** SHA-256 cua JSON chuan (khoa sap xep moi tang): cung noi dung -> cung hash, bat ke thu tu khoa. */
    public static String contentHash(ObjectMapper mapper, Object payload) {
        try {
            byte[] json = mapper.writeValueAsString(canonical(payload)).getBytes(StandardCharsets.UTF_8);
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(json));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException(ex);
        }
    }

    static Object canonical(Object v) {
        if (v instanceof Map<?, ?> m) {
            TreeMap<String, Object> t = new TreeMap<>();
            m.forEach((k, x) -> t.put(String.valueOf(k), canonical(x)));
            return t;
        }
        if (v instanceof List<?> l) {
            List<Object> out = new ArrayList<>(l.size());
            l.forEach(x -> out.add(canonical(x)));
            return out;
        }
        return v;
    }

    // ------------------------------------------------------------------------------------------- tien ich

    private static boolean notBlank(String s) {
        return s != null && !s.isBlank();
    }

    private static List<String> clean(List<String> lines) {
        List<String> out = new ArrayList<>();
        for (String l : lines == null ? List.<String>of() : lines) {
            if (l != null && !l.isBlank()) out.add(l.trim());
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> asMap(Object o) {
        return o instanceof Map<?, ?> m ? deepCopy((Map<String, Object>) m) : new LinkedHashMap<>();
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> asList(Object o) {
        List<Map<String, Object>> out = new ArrayList<>();
        if (o instanceof List<?> l) {
            for (Object x : l) if (x instanceof Map<?, ?> m) out.add((Map<String, Object>) m);
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    static Map<String, Object> deepCopy(Map<String, Object> m) {
        Map<String, Object> out = new LinkedHashMap<>();
        m.forEach((k, v) -> out.put(k, copyValue(v)));
        return out;
    }

    @SuppressWarnings("unchecked")
    private static Object copyValue(Object v) {
        if (v instanceof Map<?, ?> m) return deepCopy((Map<String, Object>) m);
        if (v instanceof List<?> l) {
            List<Object> out = new ArrayList<>(l.size());
            l.forEach(x -> out.add(copyValue(x)));
            return out;
        }
        return v;
    }
}
