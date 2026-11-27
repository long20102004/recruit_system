package recruit.demo.service.impl;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import recruit.demo.client.IdentityClient;
import recruit.demo.cvtemplate.CvRenderService;
import recruit.demo.cvtemplate.CvTemplate;
import recruit.demo.cvtemplate.CvTemplateConfig;
import recruit.demo.cvtemplate.CvTemplateRepository;
import recruit.demo.cvtemplate.CvTemplateStatus;
import recruit.demo.cvtemplate.CvTemplateType;
import recruit.demo.dto.CvTemplateSelectionDtos.CvPreviewRequest;
import recruit.demo.dto.FileLinkDto;
import recruit.demo.storage.StorageService;
import recruit.demo.dto.CandidateProfileDto;
import recruit.demo.dto.ConfirmCvRequest;
import recruit.demo.entity.CandidateProfile;
import recruit.demo.entity.CvData;
import recruit.demo.entity.CvDocument;
import recruit.demo.enums.NotificationType;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import recruit.demo.exception.ApiException;
import recruit.demo.messaging.NotificationConstants;
import recruit.demo.messaging.NotificationEvent;
import recruit.demo.messaging.OutboxWriter;
import recruit.demo.repository.CandidateProfileRepository;
import recruit.demo.repository.CvDataRepository;
import recruit.demo.repository.CvDocumentRepository;
import recruit.demo.repository.JobApplicationRepository;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.CvService;
import recruit.demo.service.SettingService;
import recruit.demo.service.cv.CvExtractionModule;
import recruit.demo.service.cv.CvFileType;
import recruit.demo.service.cv.CvProfileMapper;
import recruit.demo.service.cvmatch.CvMatchEvents;
import tools.jackson.databind.ObjectMapper;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/** specs/007-multi-cv: giới hạn 5 CV, CV chính, xoá CV đang ứng tuyển, quyền sở hữu. Dữ liệu tổng hợp. */
class CvServiceImplTest {

    private IdentityClient identity;
    private CvDataRepository cvData;
    private CvDocumentRepository docs;
    private JobApplicationRepository apps;
    private CvExtractionModule extraction;
    private ApplicationEventPublisher events;
    private StorageService storage;
    private OutboxWriter outbox;
    private CvTemplateRepository templates;
    private CvRenderService renderService;
    private CvServiceImpl service;

    private final CandidateProfile candidate = CandidateProfile.builder().id(7).userId(70).build();

    @BeforeEach
    @SuppressWarnings("unchecked")
    void setUp() {
        identity = mock(IdentityClient.class);
        cvData = mock(CvDataRepository.class);
        CandidateProfileRepository candidates = mock(CandidateProfileRepository.class);
        SettingService settings = mock(SettingService.class);
        extraction = mock(CvExtractionModule.class);
        docs = mock(CvDocumentRepository.class);
        apps = mock(JobApplicationRepository.class);
        events = mock(ApplicationEventPublisher.class);
        storage = mock(StorageService.class);
        outbox = mock(OutboxWriter.class);
        templates = mock(CvTemplateRepository.class);
        renderService = mock(CvRenderService.class);
        ObjectProvider<OutboxWriter> outboxProvider = mock(ObjectProvider.class);
        when(outboxProvider.getIfAvailable()).thenReturn(outbox);
        service = new CvServiceImpl(identity, cvData, candidates, settings, extraction, new CvProfileMapper(),
                storage, events, new ObjectMapper(), docs, apps, outboxProvider, templates, renderService);

        when(candidates.findByUserId(70)).thenReturn(Optional.of(candidate));
        when(settings.cvFields()).thenReturn(List.of("Họ tên", "Kỹ năng"));
        when(docs.save(any(CvDocument.class))).thenAnswer(i -> i.getArgument(0));
        when(apps.findCvIdsByCandidateIdAndStatusIn(eq(7), any())).thenReturn(List.of());

        var p = new UserPrincipal(70, "c@x.test", "", "Cand", Role.CANDIDATE, UserStatus.ACTIVE);
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(p, null, p.getAuthorities()));
    }

    @AfterEach
    void clear() {
        SecurityContextHolder.clearContext();
    }

    private CvDocument doc(int id, boolean main) {
        CvDocument d = CvDocument.builder().id(id).candidateId(7).main(main).build();
        when(docs.findByIdAndCandidateId(id, 7)).thenReturn(Optional.of(d));
        return d;
    }

    private void field(int cvId, String field, String value) {
        when(cvData.findByCvIdAndFieldOrderByIdAsc(cvId, field))
                .thenReturn(List.of(CvData.builder().cvId(cvId).candidateId(7).field(field).value(value).build()));
    }

    @Test
    void uploadNewRejectsSixthCvBeforeExtraction() {
        when(docs.countByCandidateId(7)).thenReturn((long) CvService.MAX_CVS);
        var file = new MockMultipartFile("file", "cv.pdf", "application/pdf", new byte[]{1});

        assertEquals(HttpStatus.BAD_REQUEST,
                assertThrows(ApiException.class, () -> service.uploadNew(file, null)).getStatus());
        verifyNoInteractions(extraction);
    }

    @Test
    void setMainMovesFlagAndResyncsMatching() {
        CvDocument oldMain = doc(1, true);
        CvDocument other = doc(2, false);
        when(docs.findByCandidateIdOrderByMainDescUpdatedAtDesc(7)).thenReturn(List.of(oldMain, other));

        service.setMain(2);

        assertFalse(oldMain.isMain());
        assertTrue(other.isMain());
        verify(events).publishEvent(new CvMatchEvents.CvChanged(7));
    }

    @Test
    void deleteRefusesCvInUnfinishedApplication() {
        doc(2, false);
        when(apps.findCvIdsByCandidateIdAndStatusIn(eq(7), any())).thenReturn(List.of(2));

        assertEquals(HttpStatus.CONFLICT, assertThrows(ApiException.class, () -> service.delete(2)).getStatus());
        verify(docs, never()).delete(any());
    }

    @Test
    void deletingMainCvPromotesNextOne() {
        CvDocument main = doc(1, true);
        CvDocument next = CvDocument.builder().id(2).candidateId(7).main(false).build();
        when(docs.findByCandidateIdOrderByMainDescUpdatedAtDesc(7)).thenReturn(List.of(next));
        when(cvData.findByCvId(1)).thenReturn(List.of());

        service.delete(1);

        verify(docs).delete(main);
        assertTrue(next.isMain());
        verify(events).publishEvent(new CvMatchEvents.CvChanged(7));
    }

    @Test
    void confirmOnSecondaryCvDoesNotSyncAccountOrMatching() {
        doc(2, false);
        field(2, CvService.FILE_NAME, "cv.pdf");
        var request = new ConfirmCvRequest(List.of(new recruit.demo.dto.CvFieldValue("Họ tên", List.of("Tên khác"))), null);

        var form = service.confirm(2, request);

        assertEquals(2, form.getCvId());
        assertFalse(form.isMain());
        verifyNoInteractions(identity);
        verify(events, never()).publishEvent(any());
        verify(cvData).save(argThat(row -> row.getCvId() == 2 && "Họ tên".equals(row.getField())));
    }

    @Test
    void confirmOnMainCvSyncsNameAndMatching() {
        CvDocument main = doc(1, true);
        when(docs.findFirstByCandidateIdAndMainTrue(7)).thenReturn(Optional.of(main));
        field(1, CvService.FILE_NAME, "cv.pdf");
        var request = new ConfirmCvRequest(null, new ObjectMapper().readValue(
                "{\"personal_info\":{\"full_name\":\"Nguyễn Văn A\"}}", CandidateProfileDto.class));

        service.confirm(null, request);

        verify(identity).update(70, "Nguyễn Văn A", null);
        verify(events).publishEvent(new CvMatchEvents.CvChanged(7));
    }

    @Test
    void otherCandidatesCvIsNotFound() {
        when(docs.findByIdAndCandidateId(99, 7)).thenReturn(Optional.empty());

        assertEquals(HttpStatus.NOT_FOUND, assertThrows(ApiException.class, () -> service.mine(99)).getStatus());
        assertEquals(HttpStatus.NOT_FOUND, assertThrows(ApiException.class, () -> service.setMain(99)).getStatus());
        assertEquals(HttpStatus.NOT_FOUND, assertThrows(ApiException.class, () -> service.delete(99)).getStatus());
    }

    // ---- specs/008-r2-storage ----

    @Test
    void uploadNewStoresPdfInPrivateBucketUnderCvKey() {
        when(docs.countByCandidateId(7)).thenReturn(0L);
        when(docs.save(any(CvDocument.class))).thenAnswer(i -> {
            CvDocument d = i.getArgument(0);
            if (d.getId() == null) d.setId(42);
            return d;
        });
        when(extraction.extract(any(), any())).thenReturn(new ObjectMapper().createObjectNode());
        byte[] pdf = {1, 2, 3};
        var file = new MockMultipartFile("file", "cv.pdf", "application/pdf", pdf);

        var res = service.uploadNew(file, null);

        var key = org.mockito.ArgumentCaptor.forClass(String.class);
        verify(storage).putPrivate(key.capture(), eq(pdf), eq("application/pdf"));
        assertTrue(key.getValue().matches("cvs/7/42/[0-9a-f-]{36}\\.pdf"), key.getValue());
        assertEquals(42, res.getCvId());
        verify(cvData).save(argThat(d -> CvService.FILE_URL.equals(d.getField()) && key.getValue().equals(d.getValue())));
    }

    @Test
    void uploadNewStoresDocxUnderDocxKeyWithWordContentType() {
        when(docs.countByCandidateId(7)).thenReturn(0L);
        when(docs.save(any(CvDocument.class))).thenAnswer(i -> {
            CvDocument d = i.getArgument(0);
            if (d.getId() == null) d.setId(42);
            return d;
        });
        when(extraction.extract(any(), any())).thenReturn(new ObjectMapper().createObjectNode());
        byte[] docx = {4, 5, 6};
        String docxMime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
        var file = new MockMultipartFile("file", "cv.docx", docxMime, docx);

        var res = service.uploadNew(file, null);

        verify(extraction).extract(eq(docx), eq(CvFileType.DOCX));
        var key = org.mockito.ArgumentCaptor.forClass(String.class);
        verify(storage).putPrivate(key.capture(), eq(docx), eq(docxMime));
        assertTrue(key.getValue().matches("cvs/7/42/[0-9a-f-]{36}\\.docx"), key.getValue());
        assertEquals(42, res.getCvId());
    }

    @Test
    void uploadRejectsUnsupportedExtension() {
        when(docs.countByCandidateId(7)).thenReturn(0L);
        var file = new MockMultipartFile("file", "cv.txt", "text/plain", new byte[]{1, 2, 3});

        assertEquals(HttpStatus.BAD_REQUEST,
                assertThrows(ApiException.class, () -> service.uploadNew(file, null)).getStatus());
        verifyNoInteractions(extraction);
    }

    @Test
    void uploadFailureOnStorageDoesNotWriteFileUrl() {
        when(docs.countByCandidateId(7)).thenReturn(0L);
        when(extraction.extract(any(), any())).thenReturn(new ObjectMapper().createObjectNode());
        doThrow(new ApiException(HttpStatus.BAD_GATEWAY, "down")).when(storage).putPrivate(any(), any(), any());
        var file = new MockMultipartFile("file", "cv.pdf", "application/pdf", new byte[]{1});

        assertEquals(HttpStatus.BAD_GATEWAY,
                assertThrows(ApiException.class, () -> service.uploadNew(file, null)).getStatus());
        verify(cvData, never()).save(argThat(d -> CvService.FILE_URL.equals(d.getField())));
        verifyNoInteractions(outbox);
    }

    @Test
    void fileReturnsPresignedDownloadLinkWithOriginalName() {
        doc(2, false);
        field(2, CvService.FILE_URL, "cvs/7/2/abc.pdf");
        field(2, CvService.FILE_NAME, "CV Nguyễn A.pdf");
        var link = FileLinkDto.builder().url("https://signed").build();
        when(storage.presignGet("cvs/7/2/abc.pdf", "CV Nguyễn A.pdf", false)).thenReturn(link);

        assertSame(link, service.file(2));
    }

    @Test
    void fileWithLegacyLocalPathIsNotServed() {
        doc(2, false);
        field(2, CvService.FILE_URL, "/app/uploads/old.pdf");

        assertEquals(HttpStatus.NOT_FOUND, assertThrows(ApiException.class, () -> service.file(2)).getStatus());
        verifyNoInteractions(storage);
    }

    @Test
    void deleteRemovesObjectFromStorage() {
        doc(2, false);
        field(2, CvService.FILE_URL, "cvs/7/2/abc.pdf");
        when(cvData.findByCvId(2)).thenReturn(List.of());

        service.delete(2);

        verify(storage).deletePrivateQuietly("cvs/7/2/abc.pdf");
    }

    @Test
    void uploadNewEmitsCvProcessedOutboxEvent() {
        when(docs.countByCandidateId(7)).thenReturn(0L);
        when(docs.save(any(CvDocument.class))).thenAnswer(i -> {
            CvDocument d = i.getArgument(0);
            if (d.getId() == null) d.setId(42);
            return d;
        });
        when(extraction.extract(any(), any())).thenReturn(new ObjectMapper().createObjectNode());
        var file = new MockMultipartFile("file", "cv-nguyenvana.pdf", "application/pdf", new byte[]{1, 2, 3});

        service.uploadNew(file, null);

        ArgumentCaptor<NotificationEvent> captor = ArgumentCaptor.forClass(NotificationEvent.class);
        verify(outbox).add(eq(NotificationConstants.RK_CV_PROCESSED), captor.capture());
        NotificationEvent event = captor.getValue();
        assertEquals(NotificationType.CV_PROCESSED, event.getType());
        assertEquals(List.of(70), event.getRecipientUserIds());
        assertEquals("AI đã xử lý xong CV", event.getTitle());
        assertEquals("cv-nguyenvana.pdf", event.getBody());
        assertEquals("/candidate/cv?cvId=42", event.getLink());
        assertEquals(42, event.getData().get("cvId"));
    }

    // ---- C04 Tạo CV từ đầu ----

    @Test
    void createBlankFirstCvBecomesMainWithoutFile() {
        when(docs.countByCandidateId(7)).thenReturn(0L);
        when(docs.save(any(CvDocument.class))).thenAnswer(i -> {
            CvDocument d = i.getArgument(0);
            if (d.getId() == null) d.setId(50);
            return d;
        });

        var dto = service.createBlank("  CV Fullstack  ");

        assertEquals(50, dto.getId());
        assertTrue(dto.isMain());
        assertEquals("CV Fullstack", dto.getTitle());
        assertNull(dto.getFileName());
        verifyNoInteractions(extraction, storage);
    }

    @Test
    void createBlankRespectsFiveCvLimit() {
        when(docs.countByCandidateId(7)).thenReturn((long) CvService.MAX_CVS);

        assertEquals(HttpStatus.BAD_REQUEST,
                assertThrows(ApiException.class, () -> service.createBlank(null)).getStatus());
        verify(docs, never()).save(any());
    }

    @Test
    void confirmSavesFormCvThatHasNoFile() throws Exception {
        doc(3, false);  // không có FILE_NAME: CV tạo từ form
        var request = new ConfirmCvRequest(null, new ObjectMapper().readValue(
                "{\"skills\":[\"Java\",\"React\"]}", CandidateProfileDto.class));

        var form = service.confirm(3, request);

        assertEquals(3, form.getCvId());
        verify(cvData).save(argThat(row -> row.getCvId() == 3
                && CvService.PARSING_STATUS.equals(row.getField()) && "COMPLETED".equals(row.getValue())));
    }

    // ---- specs/011-cv-templates ----

    @Test
    void createBlankAssignsSelectedOrDefaultTemplateAndRejectsHidden() {
        when(docs.countByCandidateId(7)).thenReturn(0L);
        when(docs.save(any(CvDocument.class))).thenAnswer(i -> {
            CvDocument d = i.getArgument(0);
            if (d.getId() == null) d.setId(51);
            return d;
        });
        CvTemplate active = CvTemplate.builder().id(10).type(CvTemplateType.CONFIG).status(CvTemplateStatus.ACTIVE).build();
        when(templates.findById(10)).thenReturn(Optional.of(active));

        var dto = service.createBlank("CV Java", 10);
        assertEquals(10, dto.getTemplateId());

        CvTemplate hidden = CvTemplate.builder().id(11).type(CvTemplateType.CONFIG).status(CvTemplateStatus.HIDDEN).build();
        when(templates.findById(11)).thenReturn(Optional.of(hidden));
        assertEquals(HttpStatus.BAD_REQUEST,
                assertThrows(ApiException.class, () -> service.createBlank("CV Ẩn", 11)).getStatus());

        CvTemplate def = CvTemplate.builder().id(1).type(CvTemplateType.CONFIG).status(CvTemplateStatus.ACTIVE)
                .defaultTemplate(true).build();
        when(templates.findFirstByDefaultTemplateTrue()).thenReturn(Optional.of(def));
        var dtoDefault = service.createBlank("CV Mặc định", null);
        assertEquals(1, dtoDefault.getTemplateId());
    }

    @Test
    void setTemplateUpdatesTemplateAndRejectsHidden() {
        CvDocument cv = doc(3, false);
        cv.setTemplateId(1);
        CvTemplate active = CvTemplate.builder().id(2).type(CvTemplateType.CONFIG).status(CvTemplateStatus.ACTIVE).build();
        when(templates.findById(2)).thenReturn(Optional.of(active));

        var dto = service.setTemplate(3, 2);
        assertEquals(2, dto.getTemplateId());
        assertEquals(2, cv.getTemplateId());

        CvTemplate hidden = CvTemplate.builder().id(9).type(CvTemplateType.CONFIG).status(CvTemplateStatus.HIDDEN).build();
        when(templates.findById(9)).thenReturn(Optional.of(hidden));
        assertEquals(HttpStatus.BAD_REQUEST,
                assertThrows(ApiException.class, () -> service.setTemplate(3, 9)).getStatus());
    }

    @Test
    void previewRendersHtmlForConfigAndTempPdfForDocx() {
        CvTemplateConfig cfg = CvTemplateConfig.builder().layout("ONE_COLUMN").build();
        CvTemplate configTpl = CvTemplate.builder().id(1).type(CvTemplateType.CONFIG)
                .status(CvTemplateStatus.ACTIVE).config(cfg).build();
        when(templates.findById(1)).thenReturn(Optional.of(configTpl));
        CandidateProfileDto profile = new CandidateProfileDto();
        when(renderService.renderHtml(cfg, profile, "CV Preview")).thenReturn("<html>ok</html>");

        var htmlRes = service.preview(new CvPreviewRequest(1, "CV Preview", profile));
        assertEquals("<html>ok</html>", htmlRes.getHtml());
        assertNull(htmlRes.getPdfLink());

        CvTemplate docxTpl = CvTemplate.builder().id(2).type(CvTemplateType.DOCX)
                .status(CvTemplateStatus.ACTIVE).docxKey("cv-templates/2/sample.docx").build();
        when(templates.findById(2)).thenReturn(Optional.of(docxTpl));
        byte[] docxBytes = {1, 2};
        byte[] pdfBytes = {3, 4};
        when(storage.getPrivate("cv-templates/2/sample.docx")).thenReturn(docxBytes);
        when(renderService.renderDocxPdf(docxBytes, profile, "CV Word")).thenReturn(pdfBytes);
        var link = FileLinkDto.builder().url("https://preview").build();
        when(storage.presignGet(argThat(k -> k.startsWith("cvs/7/preview/")), eq("cv-preview.pdf"), eq(true)))
                .thenReturn(link);

        var pdfRes = service.preview(new CvPreviewRequest(2, "CV Word", profile));
        assertNull(pdfRes.getHtml());
        assertSame(link, pdfRes.getPdfLink());
        verify(storage).putPrivate(argThat(k -> k.startsWith("cvs/7/preview/")), eq(pdfBytes), eq("application/pdf"));
    }

    @Test
    void generatePdfStoresPdfUpdatesDocumentAndDeletesOldKey() {
        CvDocument cv = doc(4, false);
        cv.setTitle("CV Backend");
        cv.setTemplateId(1);
        cv.setGeneratedPdfKey("cvs/7/4/generated-old.pdf");
        field(4, CvService.PROFILE_JSON, "{\"objective\":\"Java dev\"}");

        CvTemplate tpl = CvTemplate.builder().id(1).type(CvTemplateType.CONFIG).status(CvTemplateStatus.ACTIVE).build();
        when(templates.findById(1)).thenReturn(Optional.of(tpl));
        byte[] pdf = {9, 8, 7};
        when(renderService.renderPdf(eq(tpl), any(CandidateProfileDto.class), eq("CV Backend"))).thenReturn(pdf);
        var link = FileLinkDto.builder().url("https://generated").build();
        when(storage.presignGet(argThat(k -> k.startsWith("cvs/7/4/generated-") && !k.equals("cvs/7/4/generated-old.pdf")),
                eq("CV Backend.pdf"), eq(true))).thenReturn(link);

        FileLinkDto res = service.generatePdf(4);

        assertSame(link, res);
        assertNotNull(cv.getGeneratedPdfKey());
        assertNotEquals("cvs/7/4/generated-old.pdf", cv.getGeneratedPdfKey());
        assertNotNull(cv.getGeneratedAt());
        verify(storage).deletePrivateQuietly("cvs/7/4/generated-old.pdf");
    }

    @Test
    void confirmSavesDataEvenWhenPdfRenderFailsAndReturnsPdfError() throws Exception {
        CvDocument cv = doc(5, false);
        cv.setTitle("CV Form");
        cv.setTemplateId(2);
        CvTemplate tpl = CvTemplate.builder().id(2).type(CvTemplateType.DOCX)
                .status(CvTemplateStatus.ACTIVE).docxKey("cv-templates/2/doc.docx").build();
        when(templates.findById(2)).thenReturn(Optional.of(tpl));
        when(storage.getPrivate("cv-templates/2/doc.docx")).thenReturn(new byte[]{1});
        when(renderService.renderDocxPdf(any(), any(), eq("CV Form")))
                .thenThrow(new ApiException(HttpStatus.SERVICE_UNAVAILABLE, "Chuyển đổi chưa sẵn sàng"));

        var request = new ConfirmCvRequest(null, new ObjectMapper().readValue(
                "{\"skills\":[\"Java\"]}", CandidateProfileDto.class));

        var form = service.confirm(5, request);

        assertEquals(5, form.getCvId());
        assertEquals("Chuyển đổi chưa sẵn sàng", form.getPdfError());
        verify(cvData).save(argThat(row -> row.getCvId() == 5
                && CvService.PARSING_STATUS.equals(row.getField()) && "COMPLETED".equals(row.getValue())));
    }

    @Test
    void fileFallsBackToGeneratedPdfWhenNoUploadedFile() {
        CvDocument cv = doc(6, false);
        cv.setTitle("CV Form");
        cv.setGeneratedPdfKey("cvs/7/6/generated-123.pdf");
        var link = FileLinkDto.builder().url("https://gen-download").build();
        when(storage.presignGet("cvs/7/6/generated-123.pdf", "CV Form.pdf", false)).thenReturn(link);

        assertSame(link, service.file(6));
    }
}
