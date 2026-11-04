package recruit.demo.dto;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class CandidateProfile {
    private PersonalInfo personal_info;
    private String objective;

    @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
    private List<Education> education;

    @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
    private List<Experience> experience;

    @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
    private List<PersonalProject> personal_projects;

    @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
    private List<String> skills;

    @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
    private List<String> certificates;

    @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
    @JsonAlias({"honors", "honours"})
    private List<String> honours;

    @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
    private List<Language> languages;

    // --- KG enrichment from ai-service (feature 005); absent/null for rule-based extraction ---
    @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
    private List<NormalizedSkill> skills_normalized;
    @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
    private List<ImpliedSkill> implied_skills;
    @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
    private List<Flag> flags;

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class PersonalInfo {
        private String full_name;
        private String email;
        private String phone;
        private String github_url;
    }

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Education {
        private String school;
        private String major;
        private Integer start_year;
        private Integer end_year;
        private String gpa;
        /** KB-normalised school (open set: null when not in the KB). */
        private NormalizedRef school_normalized;

        public void setStart_year(Object val) {
            this.start_year = parseIntegerSafely(val);
        }

        public void setEnd_year(Object val) {
            this.end_year = parseIntegerSafely(val);
        }
    }

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Experience {
        private String company;
        private String job_title;
        private String start_date;
        private String end_date;

        @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
        private List<String> description;

        public void setDescription(Object val) {
            this.description = parseListStringSafely(val);
        }
    }

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class PersonalProject {
        private String name;
        private String role;
        private Integer team_size;
        private String start_date;
        private String end_date;
        private String github_url;

        @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
        private List<String> description;

        @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
        private List<String> tech_stack;

        public void setTeam_size(Object val) {
            this.team_size = parseIntegerSafely(val);
        }

        public void setDescription(Object val) {
            this.description = parseListStringSafely(val);
        }

        public void setTech_stack(Object val) {
            this.tech_stack = parseListStringSafely(val);
        }
    }

    /** A raw skill linked to a KB skill (id/name/category null when method = "unlinked"). */
    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class NormalizedSkill {
        private String raw;
        private Integer id;
        private String name;
        private String category;
        private String method;
    }

    /** A skill implied by listed skills via KB relations; never part of {@code skills}. */
    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ImpliedSkill {
        private Integer id;
        private String name;
        private String category;
        @JsonFormat(with = JsonFormat.Feature.ACCEPT_SINGLE_VALUE_AS_ARRAY)
        private List<Via> via;
    }

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Via {
        private String from;
        private String rel;
    }

    /** Advisory warning for human confirmation (codes/counts only, no CV values). */
    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Flag {
        private String code;
        private Integer count;
        private String field;
    }

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class NormalizedRef {
        private Integer id;
        private String name;
    }

    @Data
    @NoArgsConstructor
    @AllArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Language {
        private String language;
        private String note;

        public Language(String language) {
            this.language = language;
        }

        @JsonCreator
        public static Language fromValue(Object obj) {
            if (obj == null) return null;
            if (obj instanceof String) {
                return new Language((String) obj);
            }
            if (obj instanceof Map) {
                Map<?, ?> map = (Map<?, ?>) obj;
                Language lang = new Language();
                lang.setLanguage(map.get("language") != null ? map.get("language").toString() : null);
                lang.setNote(map.get("note") != null ? map.get("note").toString() : null);
                return lang;
            }
            return new Language(obj.toString());
        }
    }

    private static Integer parseIntegerSafely(Object val) {
        if (val == null) return null;
        if (val instanceof Number) return ((Number) val).intValue();
        try {
            String str = val.toString().trim();
            Matcher m = Pattern.compile("\\d+").matcher(str);
            if (m.find()) {
                return Integer.parseInt(m.group());
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    @SuppressWarnings("unchecked")
    private static List<String> parseListStringSafely(Object val) {
        if (val == null) return null;
        if (val instanceof List) {
            return ((List<?>) val).stream()
                    .filter(Objects::nonNull)
                    .map(Object::toString)
                    .toList();
        }
        return List.of(val.toString());
    }
}
