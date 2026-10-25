package recruit.demo.extraction.fields;

import recruit.demo.dto.CandidateProfile;
import recruit.demo.extraction.section.SectionContent;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Tách các dự án trong section dự án. Mỗi dự án có phạm vi riêng: tên, vai trò,
 * thời gian, URL, mô tả và công nghệ CHỈ lấy trong chunk của nó.
 */
public class ProjectExtractor {

    private static final Pattern ROLE_HINT = Pattern.compile(
            "(?iu).*(vai trò|role|position|vị trí).*");

    private final SkillDictionaryMatcher skills;

    public ProjectExtractor(SkillDictionaryMatcher skills) {
        this.skills = skills;
    }

    public List<CandidateProfile.PersonalProject> extract(SectionContent projects) {
        List<CandidateProfile.PersonalProject> out = new ArrayList<>();
        if (projects == null) {
            return out;
        }
        List<List<String>> chunks = new ArrayList<>();
        List<String> current = new ArrayList<>();
        for (String rawLine : projects.text().split("\n")) {
            String line = rawLine.strip();
            if (line.isEmpty()) {
                continue;
            }
            if (isProjectHeader(line) && !current.isEmpty()) {
                chunks.add(current);
                current = new ArrayList<>();
            }
            current.add(line);
        }
        if (!current.isEmpty()) {
            chunks.add(current);
        }
        for (List<String> chunk : chunks) {
            out.add(parseProject(chunk));
        }
        return out;
    }

    private boolean isProjectHeader(String line) {
        return RegexFieldExtractor.DATE_RANGE.matcher(line).find()
                || RegexFieldExtractor.YEAR_RANGE.matcher(line).find()
                || RegexFieldExtractor.MONTH_WORD_YEAR_RANGE.matcher(line).find();
    }

    private CandidateProfile.PersonalProject parseProject(List<String> chunk) {
        CandidateProfile.PersonalProject project = new CandidateProfile.PersonalProject();
        project.setDescription(new ArrayList<>());
        project.setTech_stack(new ArrayList<>());
        String joined = String.join("\n", chunk);

        String headerLine = chunk.get(0);
        Matcher range = RegexFieldExtractor.DATE_RANGE.matcher(headerLine);
        Matcher yearRange = RegexFieldExtractor.YEAR_RANGE.matcher(headerLine);
        Matcher monthWordRange = RegexFieldExtractor.MONTH_WORD_YEAR_RANGE.matcher(headerLine);
        if (range.find()) {
            project.setStart_date(range.group(1));
            project.setEnd_date(range.group(2));
        } else if (yearRange.find()) {
            project.setStart_date(yearRange.group(1));
            project.setEnd_date(yearRange.group(2));
        } else if (monthWordRange.find()) {
            project.setStart_date(monthWordRange.group(1));
            project.setEnd_date(monthWordRange.group(2));
        }
        String name = headerLine
                .replaceAll("\\(.*\\)", "")
                .replaceAll("^(dự án|project)\\s*[:\\-]?\\s*", "")
                .strip();
        project.setName(name.isEmpty() ? null : name);

        List<String> descriptions = new ArrayList<>();
        for (int i = 1; i < chunk.size(); i++) {
            String line = chunk.get(i);
            Matcher role = ROLE_HINT.matcher(line);
            if (role.find() && project.getRole() == null) {
                int idx = line.indexOf(':');
                project.setRole(idx >= 0 ? line.substring(idx + 1).strip() : line.strip());
                continue;
            }
            Matcher team = RegexFieldExtractor.TEAM_SIZE.matcher(line);
            if (team.find() && project.getTeam_size() == null) {
                try {
                    project.setTeam_size(Integer.parseInt(team.group(1)));
                } catch (NumberFormatException ignored) {
                }
                continue;
            }
            // URL của project: ưu tiên link github/gitlab, giữ nguyên raw URL.
            for (String url : RegexFieldExtractor.all(RegexFieldExtractor.URL, line)) {
                String low = url.toLowerCase();
                if (low.contains("github.com") || low.contains("gitlab.com")) {
                    if (project.getGithub_url() == null) {
                        project.setGithub_url(url);
                    }
                }
            }
            if (!line.replaceAll("^[-•◦]\\s*", "").isBlank()) {
                descriptions.add(line.replaceAll("^[-•◦]\\s*", "").strip());
            }
        }
        project.setDescription(descriptions);
        project.setTech_stack(skills.match(joined));
        return project;
    }
}
