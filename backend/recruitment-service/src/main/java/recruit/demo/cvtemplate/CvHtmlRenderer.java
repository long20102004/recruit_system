package recruit.demo.cvtemplate;

import lombok.Builder;
import lombok.Getter;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;
import org.thymeleaf.context.Context;
import org.thymeleaf.spring6.SpringTemplateEngine;
import org.thymeleaf.templatemode.TemplateMode;
import org.thymeleaf.templateresolver.ClassLoaderTemplateResolver;
import recruit.demo.dto.CandidateProfileDto;
import recruit.demo.dto.CandidateProfileDto.Education;
import recruit.demo.dto.CandidateProfileDto.Experience;
import recruit.demo.dto.CandidateProfileDto.Language;
import recruit.demo.dto.CandidateProfileDto.PersonalInfo;
import recruit.demo.dto.CandidateProfileDto.PersonalProject;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Render mẫu CONFIG bằng Thymeleaf (TemplateMode.XML để đảm bảo XHTML chuẩn cho Flying Saucer).
 * Mọi dữ liệu người dùng đều đi qua {@code th:text} để tự động escape HTML/XSS.
 */
@Component
public class CvHtmlRenderer {

    private static final List<String> DEFAULT_SECTIONS = List.of(
            "info", "education", "experience", "projects",
            "honours", "skills", "languages", "certificates"
    );
    private static final Set<String> SIDEBAR_SECTIONS = Set.of("skills", "languages", "certificates", "honours");
    private static final Set<String> MAIN_SECTIONS = Set.of("objective", "experience", "projects", "education");
    private static final Set<String> SERIF_FONTS = Set.of("Tinos", "EB Garamond", "Noto Serif");

    private static final Map<String, List<FontFaceSpec>> FONT_SPECS = Map.of(
            "Tinos", List.of(
                    new FontFaceSpec("fonts/Tinos-Regular.ttf", "normal", "normal"),
                    new FontFaceSpec("fonts/Tinos-Bold.ttf", "bold", "normal"),
                    new FontFaceSpec("fonts/Tinos-Italic.ttf", "normal", "italic")
            ),
            "Be Vietnam Pro", List.of(
                    new FontFaceSpec("fonts/BeVietnamPro-Regular.ttf", "normal", "normal"),
                    new FontFaceSpec("fonts/BeVietnamPro-Bold.ttf", "bold", "normal"),
                    new FontFaceSpec("fonts/BeVietnamPro-Italic.ttf", "normal", "italic")
            ),
            "Inter", List.of(
                    new FontFaceSpec("fonts/Inter-Regular.ttf", "normal", "normal"),
                    new FontFaceSpec("fonts/Inter-Bold.ttf", "bold", "normal")
            ),
            "EB Garamond", List.of(
                    new FontFaceSpec("fonts/EBGaramond-Regular.ttf", "normal", "normal"),
                    new FontFaceSpec("fonts/EBGaramond-Bold.ttf", "bold", "normal"),
                    new FontFaceSpec("fonts/EBGaramond-Italic.ttf", "normal", "italic")
            ),
            "Noto Serif", List.of(
                    new FontFaceSpec("fonts/NotoSerif-Regular.ttf", "normal", "normal"),
                    new FontFaceSpec("fonts/NotoSerif-Bold.ttf", "bold", "normal"),
                    new FontFaceSpec("fonts/NotoSerif-Italic.ttf", "normal", "italic")
            )
    );

    private final SpringTemplateEngine templateEngine;
    private final Map<String, String> fontFaceCssCache = new ConcurrentHashMap<>();

    public CvHtmlRenderer() {
        ClassLoaderTemplateResolver resolver = new ClassLoaderTemplateResolver();
        resolver.setPrefix("templates/cv/");
        resolver.setSuffix(".html");
        resolver.setTemplateMode(TemplateMode.XML);
        resolver.setCharacterEncoding(StandardCharsets.UTF_8.name());
        resolver.setCacheable(true);

        SpringTemplateEngine engine = new SpringTemplateEngine();
        engine.setTemplateResolver(resolver);
        this.templateEngine = engine;
    }

    public String renderHtmlForIframe(CvTemplateConfig config, CandidateProfileDto profile, String cvTitle) {
        return render(config, profile, cvTitle, true);
    }

    public String renderHtmlForPdf(CvTemplateConfig config, CandidateProfileDto profile, String cvTitle) {
        return render(config, profile, cvTitle, false);
    }

    private String render(CvTemplateConfig rawConfig, CandidateProfileDto profile, String cvTitle, boolean forIframe) {
        CvTemplateConfig config = normalizeConfig(rawConfig);
        CvViewModel viewModel = buildViewModel(profile, cvTitle);

        List<String> sections = config.getSections();
        boolean showInfo = sections.contains("info");
        List<String> sidebarSections = sections.stream().filter(SIDEBAR_SECTIONS::contains).toList();
        List<String> mainSections = sections.stream().filter(MAIN_SECTIONS::contains).toList();

        Context ctx = new Context(Locale.forLanguageTag("vi-VN"));
        ctx.setVariable("pageTitle", viewModel.fullName != null ? viewModel.fullName : "CV");
        ctx.setVariable("config", config);
        ctx.setVariable("cv", viewModel);
        ctx.setVariable("sections", sections);
        ctx.setVariable("showInfo", showInfo);
        ctx.setVariable("sidebarSections", sidebarSections);
        ctx.setVariable("mainSections", mainSections);
        ctx.setVariable("pageClasses", "cv-page heading-" + config.getHeading() + " density-" + config.getDensity());
        ctx.setVariable("dynamicCss", buildDynamicCss(config, forIframe));

        String templateName = "TWO_COLUMN".equals(config.getLayout()) ? "two-column" : "one-column";
        return templateEngine.process(templateName, ctx);
    }

    public static CvTemplateConfig normalizeConfig(CvTemplateConfig raw) {
        CvTemplateConfig src = raw == null ? new CvTemplateConfig() : raw;
        List<String> sections = src.getSections() == null ? List.of() : src.getSections().stream()
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(CvTemplateOptions.VALID_SECTIONS::contains)
                .distinct()
                .toList();
        if (sections.isEmpty()) {
            sections = DEFAULT_SECTIONS;
        }
        return CvTemplateConfig.builder()
                .layout(validOr(src.getLayout(), CvTemplateOptions.VALID_LAYOUTS, "ONE_COLUMN"))
                .font(validOr(src.getFont(), CvTemplateOptions.VALID_FONTS, "Tinos"))
                .accent(validOr(src.getAccent(), CvTemplateOptions.VALID_ACCENTS, "#1f1d1a"))
                .background(validOr(src.getBackground(), CvTemplateOptions.VALID_BACKGROUNDS, "#ffffff"))
                .header(validOr(src.getHeader(), CvTemplateOptions.VALID_HEADERS, "CENTER"))
                .heading(validOr(src.getHeading(), CvTemplateOptions.VALID_HEADINGS, "UPPERCASE_RULE"))
                .dates(validOr(src.getDates(), CvTemplateOptions.VALID_DATES, "RIGHT_INLINE"))
                .density(validOr(src.getDensity(), CvTemplateOptions.VALID_DENSITIES, "COMPACT"))
                .margin(validOr(src.getMargin(), CvTemplateOptions.VALID_MARGINS, "NORMAL"))
                .sections(sections)
                .build();
    }

    private static String validOr(String val, Set<String> allowed, String fallback) {
        if (val != null && allowed.contains(val)) {
            return val;
        }
        return fallback;
    }

    private String buildDynamicCss(CvTemplateConfig config, boolean forIframe) {
        String marginMm = switch (config.getMargin()) {
            case "NARROW" -> "10mm";
            case "WIDE" -> "18mm";
            default -> "14mm";
        };
        String fontFamily = "'" + config.getFont() + "', "
                + (SERIF_FONTS.contains(config.getFont()) ? "Georgia, serif" : "Arial, Helvetica, sans-serif");
        String accent = config.getAccent();
        String background = config.getBackground();

        StringBuilder css = new StringBuilder();
        if (forIframe) {
            css.append(fontFaceCss(config.getFont()));
            css.append("body { font-family: ").append(fontFamily)
                    .append("; background-color: #eceff4; color: #1f1d1a; padding: 16px; }\n");
            css.append(".cv-page { background-color: ").append(background)
                    .append("; max-width: 210mm; min-height: 297mm; margin: 0 auto; padding: ")
                    .append(marginMm)
                    .append("; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08); }\n");
        } else {
            css.append("@page { size: A4 portrait; margin: ").append(marginMm)
                    .append("; background-color: ").append(background).append("; }\n");
            css.append("body { font-family: ").append(fontFamily)
                    .append("; background-color: ").append(background)
                    .append("; color: #1f1d1a; }\n");
            css.append(".cv-page { background-color: ").append(background).append("; }\n");
        }

        css.append(".cv-name { color: ").append(accent).append("; }\n");
        css.append(".heading-UPPERCASE_RULE .section-title { color: ").append(accent)
                .append("; border-bottom: 1.2pt solid ").append(accent).append("; }\n");
        css.append(".heading-ACCENT .section-title { color: ").append(accent)
                .append("; border-left: 3pt solid ").append(accent).append("; padding-left: 7px; }\n");
        css.append(".heading-PLAIN .section-title { color: ").append(accent).append("; }\n");

        return css.toString();
    }

    private String fontFaceCss(String fontFamily) {
        return fontFaceCssCache.computeIfAbsent(fontFamily, family -> {
            List<FontFaceSpec> specs = FONT_SPECS.get(family);
            if (specs == null) {
                return "";
            }
            StringBuilder sb = new StringBuilder();
            for (FontFaceSpec spec : specs) {
                ClassPathResource res = new ClassPathResource(spec.classpath());
                if (!res.exists()) {
                    continue;
                }
                try (InputStream is = res.getInputStream()) {
                    String base64 = Base64.getEncoder().encodeToString(is.readAllBytes());
                    sb.append("@font-face { font-family: '").append(family).append("'; ")
                            .append("src: url(data:font/ttf;base64,").append(base64).append(") format('truetype'); ")
                            .append("font-weight: ").append(spec.weight()).append("; ")
                            .append("font-style: ").append(spec.style()).append("; }\n");
                } catch (IOException ignored) {
                    // Fallback sang font hệ thống nếu không đọc được file font
                }
            }
            return sb.toString();
        });
    }

    private static CvViewModel buildViewModel(CandidateProfileDto profile, String cvTitle) {
        CandidateProfileDto p = profile == null ? new CandidateProfileDto() : profile;
        PersonalInfo info = p.getPersonal_info();

        String fullName = info != null ? blankToNull(info.getFull_name()) : null;
        String title = blankToNull(cvTitle);

        List<String> contacts = new ArrayList<>();
        if (info != null) {
            addIfNotBlank(contacts, info.getEmail());
            addIfNotBlank(contacts, info.getPhone());
            addIfNotBlank(contacts, info.getGithub_url());
        }
        String contactLine = contacts.isEmpty() ? null : String.join("  |  ", contacts);

        List<EduItem> edus = safeList(p.getEducation()).stream()
                .filter(Objects::nonNull)
                .map(CvHtmlRenderer::toEduItem)
                .filter(e -> e.school != null || e.detailLine != null)
                .toList();

        List<ExpItem> exps = safeList(p.getExperience()).stream()
                .filter(Objects::nonNull)
                .map(CvHtmlRenderer::toExpItem)
                .filter(e -> e.jobTitle != null || e.companyLine != null || !e.bullets.isEmpty())
                .toList();

        List<ProjItem> projs = safeList(p.getPersonal_projects()).stream()
                .filter(Objects::nonNull)
                .map(CvHtmlRenderer::toProjItem)
                .filter(pr -> pr.name != null || pr.metaLine != null || !pr.bullets.isEmpty())
                .toList();

        List<String> skills = cleanStrings(p.getSkills());
        String skillsText = skills.isEmpty() ? null : String.join(", ", skills);
        List<String> certificates = cleanStrings(p.getCertificates());
        List<String> honours = cleanStrings(p.getHonours());
        List<LangItem> languages = safeList(p.getLanguages()).stream()
                .filter(Objects::nonNull)
                .map(CvHtmlRenderer::toLangItem)
                .filter(Objects::nonNull)
                .toList();

        return CvViewModel.builder()
                .fullName(fullName)
                .title(title)
                .contactLine(contactLine)
                .objective(blankToNull(p.getObjective()))
                .education(edus)
                .experience(exps)
                .projects(projs)
                .skills(skills)
                .skillsText(skillsText)
                .certificates(certificates)
                .honours(honours)
                .languages(languages)
                .build();
    }

    private static EduItem toEduItem(Education e) {
        String school = blankToNull(e.getSchool());
        String major = blankToNull(e.getMajor());
        String gpa = blankToNull(e.getGpa());
        List<String> details = new ArrayList<>();
        if (major != null) details.add(major);
        if (gpa != null) details.add("GPA: " + gpa);
        return EduItem.builder()
                .school(school != null ? school : "")
                .location(blankToNull(e.getLocation()))
                .period(formatYearRange(e.getStart_year(), e.getEnd_year()))
                .detailLine(details.isEmpty() ? null : String.join(" | ", details))
                .build();
    }

    private static ExpItem toExpItem(Experience e) {
        List<String> companyParts = new ArrayList<>();
        addIfNotBlank(companyParts, e.getCompany());
        addIfNotBlank(companyParts, e.getLocation());
        return ExpItem.builder()
                .jobTitle(blankToNull(e.getJob_title()) != null ? e.getJob_title().trim() : "")
                .companyLine(companyParts.isEmpty() ? null : String.join(", ", companyParts))
                .period(formatDateRange(e.getStart_date(), e.getEnd_date()))
                .bullets(cleanStrings(e.getDescription()))
                .build();
    }

    private static ProjItem toProjItem(PersonalProject pr) {
        List<String> meta = new ArrayList<>();
        if (pr.getTeam_size() != null && pr.getTeam_size() > 0) {
            meta.add("Quy mô: " + pr.getTeam_size() + " thành viên");
        }
        List<String> tech = cleanStrings(pr.getTech_stack());
        if (!tech.isEmpty()) {
            meta.add("Công nghệ: " + String.join(", ", tech));
        }
        if (blankToNull(pr.getGithub_url()) != null) {
            meta.add(pr.getGithub_url().trim());
        }
        return ProjItem.builder()
                .name(blankToNull(pr.getName()) != null ? pr.getName().trim() : "")
                .role(blankToNull(pr.getRole()))
                .period(formatDateRange(pr.getStart_date(), pr.getEnd_date()))
                .metaLine(meta.isEmpty() ? null : String.join(" | ", meta))
                .bullets(cleanStrings(pr.getDescription()))
                .build();
    }

    private static LangItem toLangItem(Language l) {
        String lang = blankToNull(l.getLanguage());
        if (lang == null) return null;
        String note = blankToNull(l.getNote());
        return new LangItem(note != null ? lang + ": " + note : lang);
    }

    private static String formatYearRange(Integer start, Integer end) {
        if (start == null && end == null) return null;
        if (start != null && end != null) return start + " - " + end;
        return start != null ? String.valueOf(start) : String.valueOf(end);
    }

    private static String formatDateRange(String start, String end) {
        String s = blankToNull(start);
        String e = blankToNull(end);
        if (s == null && e == null) return null;
        if (s != null && e != null) return s + " - " + e;
        return s != null ? s : e;
    }

    private static List<String> cleanStrings(List<String> items) {
        return safeList(items).stream()
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .toList();
    }

    private static <T> List<T> safeList(List<T> items) {
        return items == null ? List.of() : items;
    }

    private static void addIfNotBlank(List<String> target, String value) {
        String trimmed = blankToNull(value);
        if (trimmed != null) {
            target.add(trimmed);
        }
    }

    private static String blankToNull(String value) {
        if (value == null) return null;
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private record FontFaceSpec(String classpath, String weight, String style) {}

    @Getter
    @Builder
    public static class CvViewModel {
        private final String fullName;
        private final String title;
        private final String contactLine;
        private final String objective;
        private final List<EduItem> education;
        private final List<ExpItem> experience;
        private final List<ProjItem> projects;
        private final List<String> skills;
        private final String skillsText;
        private final List<String> certificates;
        private final List<String> honours;
        private final List<LangItem> languages;
    }

    @Getter
    @Builder
    public static class EduItem {
        private final String school;
        private final String location;
        private final String period;
        private final String detailLine;
    }

    @Getter
    @Builder
    public static class ExpItem {
        private final String jobTitle;
        private final String companyLine;
        private final String period;
        private final List<String> bullets;
    }

    @Getter
    @Builder
    public static class ProjItem {
        private final String name;
        private final String role;
        private final String period;
        private final String metaLine;
        private final List<String> bullets;
    }

    @Getter
    public static class LangItem {
        private final String displayLine;

        public LangItem(String displayLine) {
            this.displayLine = displayLine;
        }
    }
}
