package recruit.demo.service;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import recruit.demo.config.AppProperties;
import recruit.demo.dto.CvDtos;
import recruit.demo.entity.CandidateProfile;
import recruit.demo.entity.CvData;
import recruit.demo.entity.Role;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.CandidateProfileRepository;
import recruit.demo.repository.CvDataRepository;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class CvService {
    private final recruit.demo.client.IdentityClient identityClient;

    static final String FILE_NAME = "file_name";
    static final String FILE_URL = "file_url";
    static final String PARSING_STATUS = "parsing_status";

    private final CvDataRepository cvDataRepository;
    private final CandidateProfileRepository candidateProfileRepository;
    private final SettingService settingService;
    private final recruit.demo.service.cv.CvExtractionModule extractionModule;
    private final recruit.demo.service.cv.CvProfileMapper profileMapper;
    private final AppProperties appProperties;
    private final org.springframework.context.ApplicationEventPublisher events;

    @Transactional(readOnly = true)
    public CvDtos.CvFormResponse mine() {
        CandidateProfile candidate = requireCandidate();
        return toForm(candidate.getId());
    }

    @Transactional
    public CvDtos.CvFormResponse upload(MultipartFile file) {
        CandidateProfile candidate = requireCandidate();
        if (file == null || file.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "File is required");
        }
        String original = file.getOriginalFilename() != null ? file.getOriginalFilename() : "";
        if (!original.toLowerCase(Locale.ROOT).endsWith(".pdf")) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Chỉ nhận file PDF");
        }

        try {
            // Run inference before committing any file/profile changes. Failure never creates a fake completed CV.
            var extracted = extractionModule.extract(file.getBytes());
            Path uploadRoot = Paths.get(appProperties.getUpload().getPath()).toAbsolutePath().normalize();
            Files.createDirectories(uploadRoot);
            String storedName = UUID.randomUUID() + "_" + original.replaceAll("[^a-zA-Z0-9._-]", "_");
            Path target = uploadRoot.resolve(storedName);
            Files.copy(file.getInputStream(), target);

            put(candidate.getId(), FILE_NAME, original);
            put(candidate.getId(), FILE_URL, target.toString());
            put(candidate.getId(), PARSING_STATUS, "COMPLETED");
            put(candidate.getId(), "extracted_profile", extracted.toString());
            for (var entry : profileMapper.fields(extracted).entrySet()) {
                if (settingService.cvFields().contains(entry.getKey())) replaceLines(candidate.getId(), entry.getKey(), entry.getValue());
            }
            events.publishEvent(new recruit.demo.service.cvmatch.CvMatchEvents.CvChanged(candidate.getId()));
            return toForm(candidate.getId());
        } catch (IOException ex) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "Failed to store file");
        }
    }

    @Transactional
    public CvDtos.CvFormResponse confirm(CvDtos.ConfirmCvRequest request) {
        CandidateProfile candidate = requireCandidate();
        if (value(candidate.getId(), FILE_NAME).isBlank()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Hãy tải CV trước");
        }
        List<String> allowed = settingService.cvFields();
        if (request == null || request.fields() == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Thiếu dữ liệu hồ sơ");
        }
        for (CvDtos.FieldValue item : request.fields()) {
            if (item == null || item.field() == null || item.field().isBlank()) {
                continue;
            }
            String field = item.field().trim();
            if (!allowed.contains(field)) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "Field không nằm trong cấu hình CV_FIELD: " + field);
            }
            List<String> lines = linesOf(item.values());
            replaceLines(candidate.getId(), field, lines);
            syncProfile(candidate, field, lines);
        }
        put(candidate.getId(), PARSING_STATUS, "COMPLETED");
        events.publishEvent(new recruit.demo.service.cvmatch.CvMatchEvents.CvChanged(candidate.getId()));
        return toForm(candidate.getId());
    }

    private void syncProfile(CandidateProfile candidate, String field, List<String> lines) {
        String first = lines.isEmpty() ? "" : lines.get(0);
        if ("Họ tên".equals(field) && !first.isBlank()) {
            identityClient.update(candidate.getUserId(), first, null);
        } else if ("Điện thoại".equals(field)) {
            identityClient.update(candidate.getUserId(), null, first);
        } else if ("Tóm tắt".equals(field)) {
            candidate.setSummary(String.join("\n", lines));
            candidateProfileRepository.save(candidate);
        }
    }

    private CvDtos.CvFormResponse toForm(Integer candidateId) {
        List<CvDtos.FieldValue> fields = new ArrayList<>();
        for (String field : settingService.cvFields()) {
            fields.add(new CvDtos.FieldValue(field, lines(candidateId, field)));
        }
        String status = value(candidateId, PARSING_STATUS);
        String fileName = value(candidateId, FILE_NAME);
        boolean analyzed = "COMPLETED".equals(status) && !fileName.isBlank();
        return new CvDtos.CvFormResponse(
                fileName.isBlank() ? null : fileName,
                status.isBlank() ? null : status,
                analyzed,
                fields
        );
    }

    private List<String> linesOf(List<String> raw) {
        List<String> lines = new ArrayList<>();
        if (raw == null) {
            return lines;
        }
        for (String item : raw) {
            if (item == null) {
                continue;
            }
            for (String line : item.split("\\R")) {
                String trimmed = line.trim();
                if (!trimmed.isEmpty()) {
                    lines.add(trimmed);
                }
            }
        }
        return lines;
    }

    private void replaceLines(Integer candidateId, String field, List<String> lines) {
        List<CvData> rows = cvDataRepository.findByCandidateIdAndFieldOrderByIdAsc(candidateId, field);
        if (!rows.isEmpty()) {
            cvDataRepository.deleteAll(rows);
            cvDataRepository.flush();
        }
        for (String line : lines) {
            cvDataRepository.save(CvData.builder()
                    .candidateId(candidateId)
                    .field(field)
                    .value(line)
                    .build());
        }
    }

    private List<String> lines(Integer candidateId, String field) {
        List<String> lines = new ArrayList<>();
        for (CvData row : cvDataRepository.findByCandidateIdAndFieldOrderByIdAsc(candidateId, field)) {
            if (row.getValue() == null) {
                continue;
            }
            for (String line : row.getValue().split("\\R")) {
                String trimmed = line.trim();
                if (!trimmed.isEmpty()) {
                    lines.add(trimmed);
                }
            }
        }
        return lines;
    }

    private void put(Integer candidateId, String field, String stored) {
        List<CvData> rows = cvDataRepository.findByCandidateIdAndFieldOrderByIdAsc(candidateId, field);
        if (rows.isEmpty()) {
            cvDataRepository.save(CvData.builder()
                    .candidateId(candidateId)
                    .field(field)
                    .value(stored)
                    .build());
            return;
        }
        CvData first = rows.get(0);
        first.setValue(stored);
        cvDataRepository.save(first);
        if (rows.size() > 1) {
            cvDataRepository.deleteAll(rows.subList(1, rows.size()));
        }
    }

    private String value(Integer candidateId, String field) {
        return cvDataRepository.findByCandidateIdAndFieldOrderByIdAsc(candidateId, field).stream()
                .map(CvData::getValue)
                .filter(item -> item != null && !item.isBlank())
                .findFirst()
                .orElse("");
    }

    private CandidateProfile requireCandidate() {
        SecurityUtils.requireRole(Role.CANDIDATE);
        UserPrincipal principal = SecurityUtils.currentUser();
        return candidateProfileRepository.findByUserId(principal.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.BAD_REQUEST, "Candidate profile not found"));
    }
}
