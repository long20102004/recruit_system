package recruit.demo.cvtemplate;

import lombok.RequiredArgsConstructor;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import recruit.demo.cvtemplate.CvTemplateDtos.AdminCvTemplateDto;
import recruit.demo.cvtemplate.CvTemplateDtos.CreateConfigTemplateRequest;
import recruit.demo.cvtemplate.CvTemplateDtos.UpdateConfigTemplateRequest;
import recruit.demo.dto.FileLinkDto;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.CvDocumentRepository;
import recruit.demo.security.UserPrincipal;
import recruit.demo.storage.ObjectKeys;
import recruit.demo.storage.StorageService;

import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Nghiệp vụ quản trị mẫu CV (CONFIG & DOCX) cho Admin. */
@Service
@RequiredArgsConstructor
public class AdminCvTemplateService {

    private static final String HARVARD_SAMPLE_PATH = "cv-templates/harvard-sample.docx";
    private static final String DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

    private final CvTemplateRepository cvTemplateRepository;
    private final CvDocumentRepository cvDocumentRepository;
    private final CvRenderService cvRenderService;
    private final DocxTemplateValidator docxTemplateValidator;
    private final StorageService storageService;

    @Transactional(readOnly = true)
    public List<AdminCvTemplateDto> listAll() {
        return cvTemplateRepository.findAllByOrderByDefaultTemplateDescIdAsc().stream()
                .map(this::toAdminDto)
                .toList();
    }

    public CvTemplateOptions.OptionsResponse options() {
        return CvTemplateOptions.optionsResponse();
    }

    public byte[] loadDocxSample() {
        ClassPathResource resource = new ClassPathResource(HARVARD_SAMPLE_PATH);
        if (!resource.exists()) {
            throw new ApiException(HttpStatus.NOT_FOUND, "Không tìm thấy file Word mẫu Harvard");
        }
        try (InputStream is = resource.getInputStream()) {
            return is.readAllBytes();
        } catch (IOException ex) {
            throw new ApiException(HttpStatus.INTERNAL_SERVER_ERROR, "Không đọc được file Word mẫu Harvard");
        }
    }

    @Transactional
    public AdminCvTemplateDto createConfig(CreateConfigTemplateRequest request) {
        if (request == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Dữ liệu tạo mẫu không được để trống");
        }
        String name = validateName(request.getName(), null);
        CvTemplateConfig config = validateAndCopyConfig(request.getConfig());

        byte[] pdfBytes = cvRenderService.renderConfigPdf(config, SampleCvProfile.create(), SampleCvProfile.SAMPLE_TITLE);
        byte[] pngBytes = cvRenderService.renderFirstPagePng(pdfBytes);

        CvTemplate entity = CvTemplate.builder()
                .name(name)
                .type(CvTemplateType.CONFIG)
                .status(CvTemplateStatus.ACTIVE)
                .defaultTemplate(false)
                .config(config)
                .createdBy(currentUserIdOrNull())
                .build();
        entity = cvTemplateRepository.saveAndFlush(entity);

        String thumbKey = ObjectKeys.cvTemplateThumbnail(entity.getId());
        String pdfKey = ObjectKeys.cvTemplatePreviewPdf(entity.getId());
        uploadWithRollbackCleanup(List.of(
                new UploadSpec(thumbKey, pngBytes, "image/png"),
                new UploadSpec(pdfKey, pdfBytes, "application/pdf")
        ));

        entity.setThumbnailKey(thumbKey);
        entity.setPreviewPdfKey(pdfKey);
        entity = cvTemplateRepository.save(entity);
        return toAdminDto(entity);
    }

    @Transactional
    public AdminCvTemplateDto createDocx(MultipartFile file, String rawName) {
        String name = validateName(rawName, null);
        byte[] docxBytes = docxTemplateValidator.validate(file);
        byte[] pdfBytes = cvRenderService.renderDocxPdf(docxBytes, SampleCvProfile.create(), SampleCvProfile.SAMPLE_TITLE);
        byte[] pngBytes = cvRenderService.renderFirstPagePng(pdfBytes);

        CvTemplate entity = CvTemplate.builder()
                .name(name)
                .type(CvTemplateType.DOCX)
                .status(CvTemplateStatus.ACTIVE)
                .defaultTemplate(false)
                .createdBy(currentUserIdOrNull())
                .build();
        entity = cvTemplateRepository.saveAndFlush(entity);

        String docxKey = ObjectKeys.cvTemplateDocx(entity.getId());
        String pdfKey = ObjectKeys.cvTemplatePreviewPdf(entity.getId());
        String thumbKey = ObjectKeys.cvTemplateThumbnail(entity.getId());
        uploadWithRollbackCleanup(List.of(
                new UploadSpec(docxKey, docxBytes, DOCX_MIME),
                new UploadSpec(pdfKey, pdfBytes, "application/pdf"),
                new UploadSpec(thumbKey, pngBytes, "image/png")
        ));

        entity.setDocxKey(docxKey);
        entity.setPreviewPdfKey(pdfKey);
        entity.setThumbnailKey(thumbKey);
        entity = cvTemplateRepository.save(entity);
        return toAdminDto(entity);
    }

    @Transactional
    public AdminCvTemplateDto updateConfig(Integer id, UpdateConfigTemplateRequest request) {
        if (request == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Dữ liệu cập nhật không được để trống");
        }
        CvTemplate entity = findOrThrow(id);
        if (entity.getType() != CvTemplateType.CONFIG) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Mẫu Word không hỗ trợ cập nhật cấu hình");
        }
        String name = validateName(request.getName(), id);
        CvTemplateConfig config = validateAndCopyConfig(request.getConfig());

        byte[] pdfBytes = cvRenderService.renderConfigPdf(config, SampleCvProfile.create(), SampleCvProfile.SAMPLE_TITLE);
        byte[] pngBytes = cvRenderService.renderFirstPagePng(pdfBytes);

        String newThumbKey = ObjectKeys.cvTemplateThumbnail(id);
        String newPdfKey = ObjectKeys.cvTemplatePreviewPdf(id);
        uploadWithRollbackCleanup(List.of(
                new UploadSpec(newThumbKey, pngBytes, "image/png"),
                new UploadSpec(newPdfKey, pdfBytes, "application/pdf")
        ));

        String oldThumbKey = entity.getThumbnailKey();
        String oldPdfKey = entity.getPreviewPdfKey();

        entity.setName(name);
        entity.setConfig(config);
        entity.setThumbnailKey(newThumbKey);
        entity.setPreviewPdfKey(newPdfKey);
        entity = cvTemplateRepository.saveAndFlush(entity);

        deleteKeysQuietly(oldThumbKey, oldPdfKey);
        return toAdminDto(entity);
    }

    @Transactional
    public AdminCvTemplateDto replaceDocx(Integer id, MultipartFile file) {
        CvTemplate entity = findOrThrow(id);
        if (entity.getType() != CvTemplateType.DOCX) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Chỉ mẫu Word mới thay được file .docx");
        }
        byte[] docxBytes = docxTemplateValidator.validate(file);
        byte[] pdfBytes = cvRenderService.renderDocxPdf(docxBytes, SampleCvProfile.create(), SampleCvProfile.SAMPLE_TITLE);
        byte[] pngBytes = cvRenderService.renderFirstPagePng(pdfBytes);

        String newDocxKey = ObjectKeys.cvTemplateDocx(id);
        String newPdfKey = ObjectKeys.cvTemplatePreviewPdf(id);
        String newThumbKey = ObjectKeys.cvTemplateThumbnail(id);
        uploadWithRollbackCleanup(List.of(
                new UploadSpec(newDocxKey, docxBytes, DOCX_MIME),
                new UploadSpec(newPdfKey, pdfBytes, "application/pdf"),
                new UploadSpec(newThumbKey, pngBytes, "image/png")
        ));

        String oldDocxKey = entity.getDocxKey();
        String oldPdfKey = entity.getPreviewPdfKey();
        String oldThumbKey = entity.getThumbnailKey();

        entity.setDocxKey(newDocxKey);
        entity.setPreviewPdfKey(newPdfKey);
        entity.setThumbnailKey(newThumbKey);
        entity = cvTemplateRepository.saveAndFlush(entity);

        deleteKeysQuietly(oldDocxKey, oldPdfKey, oldThumbKey);
        return toAdminDto(entity);
    }

    @Transactional
    public AdminCvTemplateDto updateStatus(Integer id, CvTemplateStatus status) {
        if (status == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Trạng thái không được để trống");
        }
        CvTemplate entity = findOrThrow(id);
        if (entity.isDefaultTemplate() && status == CvTemplateStatus.HIDDEN) {
            throw new ApiException(HttpStatus.CONFLICT, "Không thể ẩn mẫu mặc định");
        }
        entity.setStatus(status);
        entity = cvTemplateRepository.save(entity);
        return toAdminDto(entity);
    }

    @Transactional
    public AdminCvTemplateDto setDefault(Integer id) {
        CvTemplate target = findOrThrow(id);
        if (target.getStatus() != CvTemplateStatus.ACTIVE) {
            throw new ApiException(HttpStatus.CONFLICT, "Chỉ có thể đặt mẫu đang hoạt động làm mặc định");
        }
        cvTemplateRepository.findFirstByDefaultTemplateTrue().ifPresent(prev -> {
            if (!prev.getId().equals(id)) {
                prev.setDefaultTemplate(false);
                cvTemplateRepository.saveAndFlush(prev);
            }
        });
        target.setDefaultTemplate(true);
        target = cvTemplateRepository.save(target);
        return toAdminDto(target);
    }

    @Transactional
    public void delete(Integer id) {
        CvTemplate entity = findOrThrow(id);
        if (entity.isDefaultTemplate()) {
            throw new ApiException(HttpStatus.CONFLICT, "Không thể xoá mẫu mặc định");
        }
        long usedCount = cvDocumentRepository.countByTemplateId(id);
        if (usedCount > 0) {
            throw new ApiException(HttpStatus.CONFLICT, "Đang có " + usedCount + " CV dùng mẫu này, chỉ có thể ẩn");
        }
        String docxKey = entity.getDocxKey();
        String previewPdfKey = entity.getPreviewPdfKey();
        String thumbnailKey = entity.getThumbnailKey();

        cvTemplateRepository.delete(entity);
        cvTemplateRepository.flush();

        deleteKeysQuietly(docxKey, previewPdfKey, thumbnailKey);
    }

    public String previewConfigHtml(CvTemplateConfig config) {
        CvTemplateConfig validated = validateAndCopyConfig(config);
        return cvRenderService.renderHtml(validated, SampleCvProfile.create(), SampleCvProfile.SAMPLE_TITLE);
    }

    @Transactional
    public FileLinkDto previewPdf(Integer id) {
        CvTemplate entity = findOrThrow(id);
        if (entity.getPreviewPdfKey() == null || entity.getPreviewPdfKey().isBlank()) {
            byte[] pdfBytes = cvRenderService.renderPdf(entity, SampleCvProfile.create(), SampleCvProfile.SAMPLE_TITLE);
            String pdfKey = ObjectKeys.cvTemplatePreviewPdf(entity.getId());
            List<UploadSpec> uploads = new ArrayList<>();
            uploads.add(new UploadSpec(pdfKey, pdfBytes, "application/pdf"));

            String thumbKey = entity.getThumbnailKey();
            if (thumbKey == null || thumbKey.isBlank()) {
                byte[] pngBytes = cvRenderService.renderFirstPagePng(pdfBytes);
                thumbKey = ObjectKeys.cvTemplateThumbnail(entity.getId());
                uploads.add(new UploadSpec(thumbKey, pngBytes, "image/png"));
            }
            uploadWithRollbackCleanup(uploads);
            entity.setPreviewPdfKey(pdfKey);
            entity.setThumbnailKey(thumbKey);
            cvTemplateRepository.save(entity);
        }
        return storageService.presignGet(entity.getPreviewPdfKey(), safePdfFilename(entity.getName()), true);
    }

    private CvTemplate findOrThrow(Integer id) {
        return cvTemplateRepository.findById(id)
                .orElseThrow(() -> new ApiException(HttpStatus.NOT_FOUND, "Không tìm thấy mẫu CV"));
    }

    private String validateName(String rawName, Integer excludeId) {
        if (rawName == null || rawName.isBlank()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Tên mẫu không được để trống");
        }
        String trimmed = rawName.trim();
        if (trimmed.length() > 80) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Tên mẫu tối đa 80 ký tự");
        }
        boolean exists = excludeId == null
                ? cvTemplateRepository.existsByNameIgnoreCase(trimmed)
                : cvTemplateRepository.existsByNameIgnoreCaseAndIdNot(trimmed, excludeId);
        if (exists) {
            throw new ApiException(HttpStatus.CONFLICT, "Tên mẫu CV đã tồn tại");
        }
        return trimmed;
    }

    private CvTemplateConfig validateAndCopyConfig(CvTemplateConfig config) {
        if (config == null) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Cấu hình mẫu không được để trống");
        }
        requireInSet(config.getLayout(), CvTemplateOptions.VALID_LAYOUTS, "Bố cục");
        requireInSet(config.getFont(), CvTemplateOptions.VALID_FONTS, "Font chữ");
        requireInSet(config.getAccent(), CvTemplateOptions.VALID_ACCENTS, "Màu nhấn");
        requireInSet(config.getBackground(), CvTemplateOptions.VALID_BACKGROUNDS, "Màu nền");
        requireInSet(config.getHeader(), CvTemplateOptions.VALID_HEADERS, "Căn lề phần đầu");
        requireInSet(config.getHeading(), CvTemplateOptions.VALID_HEADINGS, "Kiểu tiêu đề mục");
        requireInSet(config.getDates(), CvTemplateOptions.VALID_DATES, "Vị trí thời gian");
        requireInSet(config.getDensity(), CvTemplateOptions.VALID_DENSITIES, "Độ dày đặc");
        requireInSet(config.getMargin(), CvTemplateOptions.VALID_MARGINS, "Lề trang");

        List<String> rawSections = config.getSections();
        if (rawSections == null || rawSections.isEmpty()) {
            throw new ApiException(HttpStatus.BAD_REQUEST, "Phải chọn ít nhất một mục hiển thị");
        }
        List<String> cleanedSections = new ArrayList<>(rawSections.size());
        Set<String> seen = new HashSet<>();
        for (String sec : rawSections) {
            if (sec == null || !CvTemplateOptions.VALID_SECTIONS.contains(sec)) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "Mục hiển thị không hợp lệ: " + sec);
            }
            if (!seen.add(sec)) {
                throw new ApiException(HttpStatus.BAD_REQUEST, "Mục hiển thị bị trùng: " + sec);
            }
            cleanedSections.add(sec);
        }

        return CvTemplateConfig.builder()
                .layout(config.getLayout())
                .font(config.getFont())
                .accent(config.getAccent())
                .background(config.getBackground())
                .header(config.getHeader())
                .heading(config.getHeading())
                .dates(config.getDates())
                .density(config.getDensity())
                .margin(config.getMargin())
                .sections(cleanedSections)
                .build();
    }

    private static void requireInSet(String value, Set<String> allowed, String label) {
        if (value == null || !allowed.contains(value)) {
            throw new ApiException(HttpStatus.BAD_REQUEST, label + " không hợp lệ: " + value);
        }
    }

    private AdminCvTemplateDto toAdminDto(CvTemplate entity) {
        long usedCount = cvDocumentRepository.countByTemplateId(entity.getId());
        String thumbUrl = null;
        if (entity.getThumbnailKey() != null && !entity.getThumbnailKey().isBlank()) {
            thumbUrl = storageService.presignGet(
                    entity.getThumbnailKey(),
                    "template-" + entity.getId() + ".png",
                    true
            ).getUrl();
        }
        return AdminCvTemplateDto.builder()
                .id(entity.getId())
                .name(entity.getName())
                .type(entity.getType())
                .status(entity.getStatus())
                .defaultTemplate(entity.isDefaultTemplate())
                .config(entity.getConfig())
                .usedCount(usedCount)
                .thumbnailUrl(thumbUrl)
                .hasPreviewPdf(entity.getPreviewPdfKey() != null && !entity.getPreviewPdfKey().isBlank())
                .createdAt(entity.getCreatedAt())
                .updatedAt(entity.getUpdatedAt())
                .build();
    }

    private void uploadWithRollbackCleanup(List<UploadSpec> specs) {
        List<String> uploadedKeys = new ArrayList<>();
        try {
            for (UploadSpec spec : specs) {
                storageService.putPrivate(spec.key(), spec.content(), spec.contentType());
                uploadedKeys.add(spec.key());
            }
        } catch (RuntimeException ex) {
            for (String key : uploadedKeys) {
                storageService.deletePrivateQuietly(key);
            }
            throw ex;
        }
    }

    private void deleteKeysQuietly(String... keys) {
        if (keys == null) return;
        for (String key : keys) {
            if (key != null && !key.isBlank()) {
                storageService.deletePrivateQuietly(key);
            }
        }
    }

    private static String safePdfFilename(String templateName) {
        String base = templateName == null || templateName.isBlank()
                ? "cv-template"
                : templateName.trim().replaceAll("[^\\p{L}0-9._-]+", "-");
        return base + "-preview.pdf";
    }

    private static Integer currentUserIdOrNull() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof UserPrincipal principal) {
            return principal.getId();
        }
        return null;
    }

    private record UploadSpec(String key, byte[] content, String contentType) {}
}
