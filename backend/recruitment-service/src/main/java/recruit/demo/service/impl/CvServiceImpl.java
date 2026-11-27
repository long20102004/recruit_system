package recruit.demo.service.impl;

import recruit.demo.service.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import recruit.demo.cvtemplate.CvRenderService;
import recruit.demo.cvtemplate.CvTemplate;
import recruit.demo.cvtemplate.CvTemplateRepository;
import recruit.demo.cvtemplate.CvTemplateStatus;
import recruit.demo.cvtemplate.CvTemplateType;
import recruit.demo.dto.CandidateProfileDto;
import recruit.demo.dto.ConfirmCvRequest;
import recruit.demo.dto.CvDocumentDtos.CvDocumentDto;
import recruit.demo.dto.CvDocumentDtos.CvUploadResponse;
import recruit.demo.dto.CvFieldValue;
import recruit.demo.dto.CvFormResponse;
import recruit.demo.dto.CvTemplateSelectionDtos.CvPreviewRequest;
import recruit.demo.dto.CvTemplateSelectionDtos.CvPreviewResult;
import recruit.demo.dto.FileLinkDto;
import recruit.demo.entity.CandidateProfile;
import recruit.demo.entity.CvData;
import recruit.demo.entity.CvDocument;
import recruit.demo.enums.ApplicationStatus;
import recruit.demo.enums.NotificationType;
import recruit.demo.exception.ApiException;
import recruit.demo.messaging.NotificationConstants;
import recruit.demo.messaging.OutboxWriter;
import recruit.demo.repository.CandidateProfileRepository;
import recruit.demo.repository.CvDataRepository;
import recruit.demo.repository.CvDocumentRepository;
import recruit.demo.repository.JobApplicationRepository;
import recruit.demo.security.SecurityUtils;
import recruit.demo.security.UserPrincipal;
import recruit.demo.storage.ObjectKeys;
import recruit.demo.storage.StorageService;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

@Slf4j
@Service
@RequiredArgsConstructor
public class CvServiceImpl implements CvService {
    /** Đơn ở các trạng thái này chưa kết thúc: CV gắn với đơn không xoá được. */
    static final List<ApplicationStatus> ACTIVE_APPLICATION =
            List.of(ApplicationStatus.SUBMITTED, ApplicationStatus.REVIEWING, ApplicationStatus.INTERVIEW);
    private static final int MAX_TITLE = 120;

    private final recruit.demo.client.IdentityClient identityClient;
    private final CvDataRepository cvDataRepository;
    private final CandidateProfileRepository candidateProfileRepository;
    private final SettingService settingService;
    private final recruit.demo.service.cv.CvExtractionModule extractionModule;
    private final recruit.demo.service.cv.CvProfileMapper profileMapper;
    private final StorageService storageService;
    private final org.springframework.context.ApplicationEventPublisher events;
    private final tools.jackson.databind.ObjectMapper objectMapper;
    private final CvDocumentRepository cvDocumentRepository;
    private final JobApplicationRepository applicationRepository;
    private final ObjectProvider<OutboxWriter> outboxWriter;
    private final CvTemplateRepository cvTemplateRepository;
    private final CvRenderService cvRenderService;

    @Transactional(readOnly = true)
    public CvFormResponse mine(Integer cvId) {
        CandidateProfile candidate = requireCandidate();
        CvDocument doc = cvId == null ? mainCv(candidate.getId()).orElse(null) : requireOwned(candidate, cvId);
        return toForm(doc);
    }

    /**
     * API cũ một CV: ghi vào CV chính (chưa có thì tạo CV đầu tiên) và trả profile AI đọc được (cùng DTO với
     * /analyze-pdf). Form chỉnh sửa vẫn lấy qua {@link #mine(Integer)}.
     */
    @Transactional
    public recruit.demo.dto.CandidateProfileDto upload(MultipartFile file) {
        CandidateProfile candidate = requireCandidate();
        return store(candidate, mainCv(candidate.getId()).orElse(null), file, null).getProfile();
    }

    @Transactional
    public CvUploadResponse uploadNew(MultipartFile file, String title) {
        CandidateProfile candidate = requireCandidate();
        if (cvDocumentRepository.countByCandidateId(candidate.getId()) >= MAX_CVS) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Mỗi ứng viên chỉ có tối đa " + MAX_CVS + " CV");
        }
        return store(candidate, null, file, title == null || title.isBlank() ? null : cleanTitle(title));
    }

    /** Tạo CV từ đầu (C04): CV trống không có file, nội dung lưu qua confirm. */
    @Transactional
    public CvDocumentDto createBlank(String title) {
        return createBlank(title, null);
    }

    @Transactional
    public CvDocumentDto createBlank(String title, Integer templateId) {
        CandidateProfile candidate = requireCandidate();
        long count = cvDocumentRepository.countByCandidateId(candidate.getId());
        if (count >= MAX_CVS) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Mỗi ứng viên chỉ có tối đa " + MAX_CVS + " CV");
        }
        Integer resolvedTemplateId;
        if (templateId != null) {
            CvTemplate template = cvTemplateRepository.findById(templateId)
                    .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Không tìm thấy mẫu CV"));
            if (template.getStatus() != CvTemplateStatus.ACTIVE) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "Mẫu CV không khả dụng");
            }
            resolvedTemplateId = template.getId();
        } else {
            resolvedTemplateId = cvTemplateRepository.findFirstByDefaultTemplateTrue()
                    .map(CvTemplate::getId)
                    .orElse(null);
        }
        CvDocument doc = cvDocumentRepository.save(CvDocument.builder()
                .candidateId(candidate.getId())
                .title(title == null || title.isBlank() ? null : cleanTitle(title))
                .main(count == 0)
                .templateId(resolvedTemplateId)
                .build());
        touch(doc);
        return toDto(doc, activeCvIds(candidate.getId()));
    }

    @Transactional
    public CvDocumentDto setTemplate(Integer cvId, Integer templateId) {
        CandidateProfile candidate = requireCandidate();
        CvDocument doc = requireOwned(candidate, cvId);
        if (templateId == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Vui lòng chọn mẫu CV");
        }
        CvTemplate template = cvTemplateRepository.findById(templateId)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Không tìm thấy mẫu CV"));
        if (template.getStatus() != CvTemplateStatus.ACTIVE && !Objects.equals(doc.getTemplateId(), templateId)) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Mẫu CV đã bị ẩn");
        }
        doc.setTemplateId(templateId);
        touch(doc);
        return toDto(doc, activeCvIds(candidate.getId()));
    }

    @Transactional(readOnly = true)
    public CvPreviewResult preview(CvPreviewRequest request) {
        CandidateProfile candidate = requireCandidate();
        Integer templateId = request != null ? request.getTemplateId() : null;
        CvTemplate template;
        if (templateId != null) {
            template = cvTemplateRepository.findById(templateId)
                    .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Không tìm thấy mẫu CV"));
            if (template.getStatus() != CvTemplateStatus.ACTIVE) {
                boolean usedByCandidate = cvDocumentRepository
                        .findByCandidateIdOrderByMainDescUpdatedAtDesc(candidate.getId())
                        .stream()
                        .anyMatch(d -> Objects.equals(d.getTemplateId(), template.getId()));
                if (!usedByCandidate) {
                    throw new ApiException(HttpStatus.BAD_REQUEST, "Mẫu CV không khả dụng");
                }
            }
        } else {
            template = cvTemplateRepository.findFirstByDefaultTemplateTrue()
                    .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Chưa có mẫu CV mặc định"));
        }

        CandidateProfileDto profile = request != null && request.getProfile() != null
                ? request.getProfile()
                : new CandidateProfileDto();
        String title = request != null ? request.getTitle() : null;

        if (template.getType() == CvTemplateType.DOCX) {
            if (template.getDocxKey() == null || template.getDocxKey().isBlank()) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "Mẫu DOCX chưa có tệp nguồn");
            }
            byte[] docxBytes = storageService.getPrivate(template.getDocxKey());
            byte[] pdfBytes = cvRenderService.renderDocxPdf(docxBytes, profile, title);
            String key = ObjectKeys.cvPreviewTempPdf(candidate.getId());
            storageService.putPrivate(key, pdfBytes, "application/pdf");
            return CvPreviewResult.builder()
                    .pdfLink(storageService.presignGet(key, "cv-preview.pdf", true))
                    .build();
        }

        String html = cvRenderService.renderHtml(template.getConfig(), profile, title);
        return CvPreviewResult.builder().html(html).build();
    }

    @Transactional
    public FileLinkDto generatePdf(Integer cvId) {
        CandidateProfile candidate = requireCandidate();
        CvDocument doc = requireOwned(candidate, cvId);
        CvTemplate template = resolveTemplateForDocument(doc);
        CandidateProfileDto profile = toForm(doc).getProfile();
        byte[] pdfBytes = renderTemplatePdf(template, profile, doc.getTitle());

        String oldKey = doc.getGeneratedPdfKey();
        String newKey = ObjectKeys.cvGeneratedPdf(candidate.getId(), doc.getId());
        storageService.putPrivate(newKey, pdfBytes, "application/pdf");
        doc.setGeneratedPdfKey(newKey);
        doc.setGeneratedAt(LocalDateTime.now());
        cvDocumentRepository.save(doc);
        if (oldKey != null && !oldKey.isBlank() && !oldKey.equals(newKey)) {
            storageService.deletePrivateQuietly(oldKey);
        }
        return storageService.presignGet(newKey, generatedDownloadName(doc), true);
    }

    @Transactional
    public CvUploadResponse reupload(Integer cvId, MultipartFile file) {
        CandidateProfile candidate = requireCandidate();
        return store(candidate, requireOwned(candidate, cvId), file, null);
    }

    /** Trích xuất rồi ghi file + kết quả vào doc; doc = null thì tạo CV mới (CV đầu tiên thành CV chính). */
    private CvUploadResponse store(CandidateProfile candidate, CvDocument doc, MultipartFile file, String title) {
        if (file == null || file.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "File is required");
        }
        String original = file.getOriginalFilename() != null ? file.getOriginalFilename() : "";
        var type = recruit.demo.service.cv.CvFileType.fromFileName(original)
                .orElseThrow(() -> new ApiException(HttpStatus.BAD_REQUEST, "Chỉ nhận file PDF hoặc DOCX"));

        try {
            // Run inference before committing any file/profile changes. Failure never creates a fake completed CV.
            byte[] bytes = file.getBytes();
            var extracted = extractionModule.extract(bytes, type);

            String previousKey = null;
            if (doc == null) {
                boolean first = cvDocumentRepository.countByCandidateId(candidate.getId()) == 0;
                doc = cvDocumentRepository.save(CvDocument.builder()
                        .candidateId(candidate.getId()).title(title).main(first).build());
            } else {
                previousKey = value(doc.getId(), FILE_URL);
                touch(doc);
            }
            // Lỗi upload ném ApiException -> transaction rollback, không có CV "có file" giả.
            String key = ObjectKeys.cv(candidate.getId(), doc.getId(), type.getExtension());
            storageService.putPrivate(key, bytes, type.getContentType());
            put(doc, FILE_NAME, original);
            put(doc, FILE_URL, key);
            if (previousKey != null && !previousKey.equals(key)) storageService.deletePrivateQuietly(previousKey);
            put(doc, PARSING_STATUS, "COMPLETED");
            put(doc, PROFILE_JSON, extracted.toString());
            for (var entry : profileMapper.fields(extracted).entrySet()) {
                if (settingService.cvFields().contains(entry.getKey())) replaceLines(doc, entry.getKey(), entry.getValue());
            }
            if (doc.isMain()) publishChanged(candidate);
            NotificationOutbox.publish(
                    outboxWriter,
                    NotificationConstants.RK_CV_PROCESSED,
                    NotificationType.CV_PROCESSED,
                    List.of(candidate.getUserId()),
                    "AI đã xử lý xong CV",
                    original,
                    "/candidate/cv?cvId=" + doc.getId(),
                    java.util.Map.of("cvId", doc.getId()));
            return CvUploadResponse.builder()
                    .cvId(doc.getId())
                    .profile(objectMapper.treeToValue(extracted, recruit.demo.dto.CandidateProfileDto.class))
                    .build();
        } catch (IOException ex) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "Failed to store file");
        }
    }

    @Transactional
    public CvFormResponse confirm(Integer cvId, ConfirmCvRequest request) {
        CandidateProfile candidate = requireCandidate();
        CvDocument doc = cvId == null ? mainCv(candidate.getId()).orElse(null) : requireOwned(candidate, cvId);
        // CV tạo từ form (C04) không có file: vẫn lưu được nội dung.
        if (doc == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Hãy tải lên hoặc tạo CV trước");
        }
        List<String> allowed = settingService.cvFields();
        if (request == null || (request.getFields() == null && request.getProfile() == null)) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Thiếu dữ liệu hồ sơ");
        }
        if (request.getProfile() != null) {
            applyProfile(candidate, doc, request.getProfile(), allowed);
        }
        for (CvFieldValue item : request.getFields() == null ? List.<CvFieldValue>of() : request.getFields()) {
            if (item == null || item.getField() == null || item.getField().isBlank()) {
                continue;
            }
            String field = item.getField().trim();
            if (!allowed.contains(field)) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "Field không nằm trong cấu hình CV_FIELD: " + field);
            }
            List<String> lines = linesOf(item.getValues());
            replaceLines(doc, field, lines);
            syncProfile(candidate, doc, field, lines);
        }
        put(doc, PARSING_STATUS, "COMPLETED");
        touch(doc);
        if (doc.isMain()) publishChanged(candidate);

        String pdfError = null;
        if (value(doc.getId(), FILE_URL).isBlank()) {
            Optional<CvTemplate> templateOpt = resolveOptionalTemplateForDocument(doc);
            if (templateOpt.isPresent()) {
                try {
                    CandidateProfileDto profileForPdf = storedProfile(doc.getId());
                    if (profileForPdf == null && request.getProfile() != null) {
                        profileForPdf = request.getProfile();
                    }
                    byte[] pdfBytes = renderTemplatePdf(templateOpt.get(), profileForPdf, doc.getTitle());
                    String oldKey = doc.getGeneratedPdfKey();
                    String newKey = ObjectKeys.cvGeneratedPdf(candidate.getId(), doc.getId());
                    storageService.putPrivate(newKey, pdfBytes, "application/pdf");
                    doc.setGeneratedPdfKey(newKey);
                    doc.setGeneratedAt(LocalDateTime.now());
                    cvDocumentRepository.save(doc);
                    if (oldKey != null && !oldKey.isBlank() && !oldKey.equals(newKey)) {
                        storageService.deletePrivateQuietly(oldKey);
                    }
                } catch (RuntimeException ex) {
                    log.warn("Không thể sinh PDF cho cvId={}: {}", doc.getId(), ex.getMessage());
                    pdfError = ex.getMessage() != null && !ex.getMessage().isBlank()
                            ? ex.getMessage()
                            : "Không thể sinh file PDF";
                }
            }
        }
        CvFormResponse form = toForm(doc);
        form.setPdfError(pdfError);
        return form;
    }

    @Transactional(readOnly = true)
    public List<CvDocumentDto> documents() {
        return documents(requireCandidate());
    }

    @Transactional
    public CvDocumentDto rename(Integer cvId, String title) {
        CandidateProfile candidate = requireCandidate();
        CvDocument doc = requireOwned(candidate, cvId);
        doc.setTitle(cleanTitle(title));
        cvDocumentRepository.save(doc);
        return toDto(doc, activeCvIds(candidate.getId()));
    }

    @Transactional
    public List<CvDocumentDto> setMain(Integer cvId) {
        CandidateProfile candidate = requireCandidate();
        CvDocument target = requireOwned(candidate, cvId);
        if (!target.isMain()) {
            List<CvDocument> all = cvDocumentRepository.findByCandidateIdOrderByMainDescUpdatedAtDesc(candidate.getId());
            // Bỏ cờ cũ trước rồi mới đặt cờ mới để không lúc nào có 2 CV chính.
            for (CvDocument doc : all) {
                if (doc.isMain()) {
                    doc.setMain(false);
                    cvDocumentRepository.save(doc);
                }
            }
            cvDocumentRepository.flush();
            target.setMain(true);
            cvDocumentRepository.save(target);
            cvDocumentRepository.flush();
            publishChanged(candidate);
        }
        return documents(candidate);
    }

    @Transactional
    public void delete(Integer cvId) {
        CandidateProfile candidate = requireCandidate();
        CvDocument doc = requireOwned(candidate, cvId);
        if (activeCvIds(candidate.getId()).contains(doc.getId())) {
            throw new ApiException(HttpStatus.CONFLICT,
                    "Không thể xoá CV đang đính kèm trong đơn ứng tuyển chưa kết thúc.");
        }
        String fileUrl = value(doc.getId(), FILE_URL);
        String generatedPdfKey = doc.getGeneratedPdfKey();
        cvDataRepository.deleteAll(cvDataRepository.findByCvId(doc.getId()));
        cvDocumentRepository.delete(doc);
        cvDocumentRepository.flush();
        if (doc.isMain()) {
            // CV cập nhật gần nhất còn lại thành CV chính.
            cvDocumentRepository.findByCandidateIdOrderByMainDescUpdatedAtDesc(candidate.getId()).stream()
                    .findFirst()
                    .ifPresent(next -> {
                        next.setMain(true);
                        cvDocumentRepository.save(next);
                    });
            publishChanged(candidate);
        }
        storageService.deletePrivateQuietly(fileUrl);
        if (generatedPdfKey != null && !generatedPdfKey.isBlank()) {
            storageService.deletePrivateQuietly(generatedPdfKey);
        }
    }

    @Transactional(readOnly = true)
    public FileLinkDto file(Integer cvId) {
        CandidateProfile candidate = requireCandidate();
        CvDocument doc = requireOwned(candidate, cvId);
        String key = value(doc.getId(), FILE_URL);
        if (!key.isBlank()) {
            if (!ObjectKeys.isObjectKey(key)) {
                throw new ApiException(HttpStatus.NOT_FOUND, "Tệp CV chưa được chuyển lên kho lưu trữ, vui lòng tải lại CV.");
            }
            String fileName = value(doc.getId(), FILE_NAME);
            return storageService.presignGet(key, fileName.isBlank() ? "cv.pdf" : fileName, false);
        }
        String generatedKey = doc.getGeneratedPdfKey();
        if (generatedKey != null && !generatedKey.isBlank() && ObjectKeys.isObjectKey(generatedKey)) {
            return storageService.presignGet(generatedKey, generatedDownloadName(doc), false);
        }
        throw new ApiException(HttpStatus.NOT_FOUND, "CV chưa có tệp đính kèm.");
    }

    /**
     * Gộp hồ sơ người dùng sửa vào JSON đã lưu (giữ các khoá ngoài CandidateProfile như implied_skills của KG),
     * rồi ghi lại các field dùng cho matching và đồng bộ họ tên / SĐT / tóm tắt như khi sửa từng field.
     */
    private void applyProfile(CandidateProfile candidate, CvDocument doc,
                              recruit.demo.dto.CandidateProfileDto profile, List<String> allowed) {
        tools.jackson.databind.node.ObjectNode merged;
        String stored = value(doc.getId(), PROFILE_JSON);
        try {
            var base = stored.isBlank() ? null : objectMapper.readTree(stored);
            merged = base instanceof tools.jackson.databind.node.ObjectNode obj ? obj : objectMapper.createObjectNode();
        } catch (RuntimeException ex) {
            merged = objectMapper.createObjectNode();
        }
        tools.jackson.databind.JsonNode edited = objectMapper.valueToTree(profile);
        for (var entry : edited.properties()) merged.set(entry.getKey(), entry.getValue());
        put(doc, PROFILE_JSON, merged.toString());
        for (var entry : profileMapper.fields(merged).entrySet()) {
            if (!allowed.contains(entry.getKey())) continue;
            replaceLines(doc, entry.getKey(), entry.getValue());
            syncProfile(candidate, doc, entry.getKey(), entry.getValue());
        }
    }

    /** Chỉ CV chính mới đồng bộ họ tên / SĐT / tóm tắt sang tài khoản và hồ sơ ứng viên. */
    private void syncProfile(CandidateProfile candidate, CvDocument doc, String field, List<String> lines) {
        if (!doc.isMain()) return;
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

    private CvFormResponse toForm(CvDocument doc) {
        List<CvFieldValue> fields = new ArrayList<>();
        for (String field : settingService.cvFields()) {
            fields.add(new CvFieldValue(field, doc == null ? List.of() : lines(doc.getId(), field)));
        }
        if (doc == null) {
            return CvFormResponse.builder().fields(fields).build();
        }
        String status = value(doc.getId(), PARSING_STATUS);
        String fileName = value(doc.getId(), FILE_NAME);
        // Sẵn sàng dùng (ứng tuyển, matching): đã có nội dung, kể cả CV tạo từ form/mẫu không có file gốc.
        boolean analyzed = "COMPLETED".equals(status);
        boolean hasGeneratedPdf = doc.getGeneratedPdfKey() != null && !doc.getGeneratedPdfKey().isBlank();
        return CvFormResponse.builder()
                .cvId(doc.getId())
                .title(titleOf(doc, fileName))
                .main(doc.isMain())
                .fileName(fileName.isBlank() ? null : fileName)
                .parsingStatus(status.isBlank() ? null : status)
                .analyzed(analyzed)
                .fields(fields)
                .profile(storedProfile(doc.getId()))
                .templateId(doc.getTemplateId())
                .hasGeneratedPdf(hasGeneratedPdf)
                .build();
    }

    private List<CvDocumentDto> documents(CandidateProfile candidate) {
        Set<Integer> active = activeCvIds(candidate.getId());
        return cvDocumentRepository.findByCandidateIdOrderByMainDescUpdatedAtDesc(candidate.getId()).stream()
                .map(doc -> toDto(doc, active))
                .toList();
    }

    private CvDocumentDto toDto(CvDocument doc, Set<Integer> activeCvIds) {
        String fileName = value(doc.getId(), FILE_NAME);
        String status = value(doc.getId(), PARSING_STATUS);
        boolean hasGeneratedPdf = doc.getGeneratedPdfKey() != null && !doc.getGeneratedPdfKey().isBlank();
        return CvDocumentDto.builder()
                .id(doc.getId())
                .title(titleOf(doc, fileName))
                .fileName(fileName.isBlank() ? null : fileName)
                .main(doc.isMain())
                .parsingStatus(status.isBlank() ? null : status)
                .analyzed("COMPLETED".equals(status))
                .skills(lines(doc.getId(), SKILLS))
                .updatedAt(doc.getUpdatedAt())
                .inActiveApplication(activeCvIds.contains(doc.getId()))
                .templateId(doc.getTemplateId())
                .hasGeneratedPdf(hasGeneratedPdf)
                .build();
    }

    private CvTemplate resolveTemplateForDocument(CvDocument doc) {
        if (doc.getTemplateId() != null) {
            return cvTemplateRepository.findById(doc.getTemplateId())
                    .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Không tìm thấy mẫu CV"));
        }
        return cvTemplateRepository.findFirstByDefaultTemplateTrue()
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Chưa có mẫu CV mặc định"));
    }

    private Optional<CvTemplate> resolveOptionalTemplateForDocument(CvDocument doc) {
        if (doc.getTemplateId() != null) {
            return cvTemplateRepository.findById(doc.getTemplateId());
        }
        return cvTemplateRepository.findFirstByDefaultTemplateTrue();
    }

    private byte[] renderTemplatePdf(CvTemplate template, CandidateProfileDto profile, String title) {
        CandidateProfileDto safeProfile = profile != null ? profile : new CandidateProfileDto();
        if (template.getType() == CvTemplateType.DOCX) {
            if (template.getDocxKey() == null || template.getDocxKey().isBlank()) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "Mẫu DOCX chưa có tệp nguồn");
            }
            byte[] docxBytes = storageService.getPrivate(template.getDocxKey());
            return cvRenderService.renderDocxPdf(docxBytes, safeProfile, title);
        }
        return cvRenderService.renderPdf(template, safeProfile, title);
    }

    private String generatedDownloadName(CvDocument doc) {
        String t = doc.getTitle();
        if (t == null || t.isBlank()) {
            return "cv.pdf";
        }
        String clean = t.trim().replaceAll("[\\\\/:*?\"<>|]+", "_");
        if (clean.isEmpty()) {
            return "cv.pdf";
        }
        return clean.toLowerCase(Locale.ROOT).endsWith(".pdf") ? clean : clean + ".pdf";
    }

    /** Tên hiển thị: tên ứng viên đặt, không có thì tên file bỏ đuôi. */
    private String titleOf(CvDocument doc, String fileName) {
        if (doc.getTitle() != null && !doc.getTitle().isBlank()) return doc.getTitle();
        if (fileName.isBlank()) return "CV tạo từ form #" + doc.getId();
        int dot = fileName.lastIndexOf('.');
        return dot > 0 ? fileName.substring(0, dot) : fileName;
    }

    private String cleanTitle(String title) {
        String trimmed = title == null ? "" : title.trim();
        if (trimmed.isEmpty() || trimmed.length() > MAX_TITLE) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Tên CV phải từ 1 đến " + MAX_TITLE + " ký tự");
        }
        return trimmed;
    }

    private Set<Integer> activeCvIds(Integer candidateId) {
        return new HashSet<>(applicationRepository.findCvIdsByCandidateIdAndStatusIn(candidateId, ACTIVE_APPLICATION));
    }

    private void publishChanged(CandidateProfile candidate) {
        events.publishEvent(new recruit.demo.service.cvmatch.CvMatchEvents.CvChanged(candidate.getId()));
    }

    /** Nội dung CV nằm ở cv_data nên phải tự cập nhật thời điểm sửa của CV. */
    private void touch(CvDocument doc) {
        doc.setUpdatedAt(LocalDateTime.now());
        cvDocumentRepository.save(doc);
    }


    private recruit.demo.dto.CandidateProfileDto storedProfile(Integer cvId) {
        String stored = value(cvId, PROFILE_JSON);
        if (stored.isBlank()) return null;
        try {
            return objectMapper.readValue(stored, recruit.demo.dto.CandidateProfileDto.class);
        } catch (RuntimeException ex) {
            return null;
        }
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

    private void replaceLines(CvDocument doc, String field, List<String> lines) {
        List<CvData> rows = cvDataRepository.findByCvIdAndFieldOrderByIdAsc(doc.getId(), field);
        if (!rows.isEmpty()) {
            cvDataRepository.deleteAll(rows);
            cvDataRepository.flush();
        }
        for (String line : lines) {
            cvDataRepository.save(row(doc, field, line));
        }
    }

    private List<String> lines(Integer cvId, String field) {
        List<String> lines = new ArrayList<>();
        for (CvData row : cvDataRepository.findByCvIdAndFieldOrderByIdAsc(cvId, field)) {
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

    private void put(CvDocument doc, String field, String stored) {
        List<CvData> rows = cvDataRepository.findByCvIdAndFieldOrderByIdAsc(doc.getId(), field);
        if (rows.isEmpty()) {
            cvDataRepository.save(row(doc, field, stored));
            return;
        }
        CvData first = rows.get(0);
        first.setValue(stored);
        cvDataRepository.save(first);
        if (rows.size() > 1) {
            cvDataRepository.deleteAll(rows.subList(1, rows.size()));
        }
    }

    private CvData row(CvDocument doc, String field, String value) {
        return CvData.builder()
                .candidateId(doc.getCandidateId())
                .cvId(doc.getId())
                .field(field)
                .value(value)
                .build();
    }

    private String value(Integer cvId, String field) {
        return cvDataRepository.findByCvIdAndFieldOrderByIdAsc(cvId, field).stream()
                .map(CvData::getValue)
                .filter(item -> item != null && !item.isBlank())
                .findFirst()
                .orElse("");
    }

    private Optional<CvDocument> mainCv(Integer candidateId) {
        return cvDocumentRepository.findFirstByCandidateIdAndMainTrue(candidateId);
    }

    /** CV không thuộc ứng viên trả 404 như không tồn tại (không lộ CV của người khác). */
    private CvDocument requireOwned(CandidateProfile candidate, Integer cvId) {
        if (cvId == null) throw new ApiException(HttpStatus.NOT_FOUND, "Không tìm thấy CV");
        return cvDocumentRepository.findByIdAndCandidateId(cvId, candidate.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Không tìm thấy CV"));
    }

    private CandidateProfile requireCandidate() {
        UserPrincipal principal = SecurityUtils.currentUser();
        return candidateProfileRepository.findByUserId(principal.getId())
                .orElseThrow(() -> new ApiException(HttpStatus.BAD_REQUEST, "Candidate profile not found"));
    }
}
