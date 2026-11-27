package recruit.demo.cvtemplate;

import recruit.demo.dto.CandidateProfileDto;
import recruit.demo.dto.CandidateProfileDto.Education;
import recruit.demo.dto.CandidateProfileDto.Experience;
import recruit.demo.dto.CandidateProfileDto.Language;
import recruit.demo.dto.CandidateProfileDto.PersonalInfo;
import recruit.demo.dto.CandidateProfileDto.PersonalProject;

import java.util.List;

/** Dữ liệu hồ sơ mẫu tiếng Việt dùng để xem trước và điền thử mẫu CV (CONFIG & DOCX). */
public final class SampleCvProfile {

    public static final String SAMPLE_TITLE = "Kỹ sư Phần mềm Backend";

    private SampleCvProfile() {
    }

    public static CandidateProfileDto create() {
        CandidateProfileDto dto = new CandidateProfileDto();

        PersonalInfo info = new PersonalInfo();
        info.setFull_name("Nguyễn Văn Học");
        info.setEmail("hoc.nguyen@hirelens.vn");
        info.setPhone("0912 345 678");
        info.setGithub_url("https://github.com/nguyenvanhoc");
        dto.setPersonal_info(info);

        dto.setObjective(
                "Kỹ sư phần mềm Backend với hơn 3 năm kinh nghiệm phát triển hệ thống microservices "
                        + "bằng Java và Spring Boot, tối ưu truy vấn MySQL và tích hợp dịch vụ AI tìm kiếm ngữ nghĩa."
        );

        Education edu = new Education();
        edu.setSchool("Học viện Công nghệ Bưu chính Viễn thông");
        edu.setMajor("Kỹ thuật Phần mềm");
        edu.setLocation("Hà Nội");
        edu.setStart_year(2019);
        edu.setEnd_year(2023);
        edu.setGpa("3.65 / 4.0");
        dto.setEducation(List.of(edu));

        Experience exp1 = new Experience();
        exp1.setCompany("Công ty Công nghệ HireLens");
        exp1.setJob_title("Kỹ sư Phần mềm Backend");
        exp1.setLocation("Hà Nội");
        exp1.setStart_date("06/2023");
        exp1.setEnd_date("Hiện tại");
        exp1.setDescription(List.of(
                "Thiết kế và vận hành 5 microservices với Spring Boot, RabbitMQ và Redis.",
                "Tối ưu truy vấn tìm kiếm việc làm giúp giảm 42% thời gian phản hồi API."
        ));

        Experience exp2 = new Experience();
        exp2.setCompany("FPT Software");
        exp2.setJob_title("Thực tập sinh Java Backend");
        exp2.setLocation("Hà Nội");
        exp2.setStart_date("06/2022");
        exp2.setEnd_date("03/2023");
        exp2.setDescription(List.of(
                "Phát triển REST API quản lý hồ sơ ứng viên và viết unit test đạt 85% coverage."
        ));
        dto.setExperience(List.of(exp1, exp2));

        PersonalProject proj = new PersonalProject();
        proj.setName("Hệ thống Ghép CV Thông minh");
        proj.setRole("Trưởng nhóm Backend");
        proj.setTeam_size(4);
        proj.setStart_date("01/2024");
        proj.setEnd_date("06/2024");
        proj.setGithub_url("https://github.com/nguyenvanhoc/cv-matcher");
        proj.setTech_stack(List.of("Java 17", "Spring Boot", "MySQL", "Redis"));
        proj.setDescription(List.of(
                "Xây dựng pipeline trích xuất PDF/DOCX và tính điểm phù hợp giữa CV với tin tuyển dụng."
        ));
        dto.setPersonal_projects(List.of(proj));

        dto.setSkills(List.of("Java", "Spring Boot", "MySQL", "Redis", "RabbitMQ", "Docker", "REST API", "Git"));
        dto.setCertificates(List.of(
                "AWS Certified Developer – Associate (2024)",
                "Oracle Certified Professional: Java SE 17"
        ));
        dto.setHonours(List.of(
                "Giải Nhì Olympic Tin học Sinh viên Toàn quốc (2022)",
                "Học bổng Khuyến khích Học tập 6 kỳ liên tiếp"
        ));
        dto.setLanguages(List.of(
                new Language("Tiếng Anh", "IELTS 7.0 — Đọc hiểu tài liệu & giao tiếp kỹ thuật"),
                new Language("Tiếng Nhật", "JLPT N3")
        ));

        return dto;
    }
}
