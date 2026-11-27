package recruit.demo.storage;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import recruit.demo.entity.Company;
import recruit.demo.entity.CvData;
import recruit.demo.repository.CompanyRepository;
import recruit.demo.repository.CvDataRepository;
import recruit.demo.service.CvService;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Chuyển file CV PDF và giấy phép công ty đang lưu trên đĩa lên R2 (specs/008-r2-storage, FR-008).
 * Chỉ chạy khi {@code storage.migrate-local=true}; bỏ qua giá trị đã là object key nên chạy lại an toàn.
 * Logo/ảnh bìa cũ không có đường dẫn trong DB nên không migrate được.
 */
@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnProperty(name = "storage.migrate-local", havingValue = "true")
public class LegacyFileMigrationRunner implements ApplicationRunner {

    private final CvDataRepository cvDataRepository;
    private final CompanyRepository companyRepository;
    private final StorageService storageService;

    /** Kết quả một lần chạy. */
    public record Result(int moved, int missing, int failed) {
    }

    @Override
    public void run(ApplicationArguments args) {
        Result r = migrate();
        log.info("Migrate file local -> R2 xong: chuyển {}, thiếu file {}, lỗi {}", r.moved(), r.missing(), r.failed());
    }

    public Result migrate() {
        int moved = 0, missing = 0, failed = 0;

        for (CvData row : cvDataRepository.findAllByField(CvService.FILE_URL)) {
            if (!ObjectKeys.isLegacyPath(row.getValue())) continue;
            Path path = Paths.get(row.getValue()).toAbsolutePath().normalize();
            if (!Files.isRegularFile(path)) {
                missing++;
                log.warn("Không thấy file CV cũ (cv_id={})", row.getCvId());
                continue;
            }
            try {
                String key = ObjectKeys.cv(row.getCandidateId(), row.getCvId());
                storageService.putPrivate(key, Files.readAllBytes(path), "application/pdf");
                row.setValue(key);
                cvDataRepository.save(row);
                moved++;
            } catch (IOException | RuntimeException ex) {
                failed++;
                log.warn("Migrate CV lỗi (cv_id={}): {}", row.getCvId(), ex.getClass().getSimpleName());
            }
        }

        for (Company c : companyRepository.findAll()) {
            if (!ObjectKeys.isLegacyPath(c.getLicenseFileUrl())) continue;
            Path path = Paths.get(c.getLicenseFileUrl()).toAbsolutePath().normalize();
            if (!Files.isRegularFile(path)) {
                missing++;
                log.warn("Không thấy file giấy phép cũ (company_id={})", c.getId());
                continue;
            }
            try {
                String name = c.getLicenseFileName() != null ? c.getLicenseFileName() : path.getFileName().toString();
                String key = ObjectKeys.companyFile(c.getId(), "license", name);
                String type = Files.probeContentType(path);
                storageService.putPrivate(key, Files.readAllBytes(path), type != null ? type : "application/octet-stream");
                c.setLicenseFileUrl(key);
                companyRepository.save(c);
                moved++;
            } catch (IOException | RuntimeException ex) {
                failed++;
                log.warn("Migrate giấy phép lỗi (company_id={}): {}", c.getId(), ex.getClass().getSimpleName());
            }
        }
        return new Result(moved, missing, failed);
    }
}
