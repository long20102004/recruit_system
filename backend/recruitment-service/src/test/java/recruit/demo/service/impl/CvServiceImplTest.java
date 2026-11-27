package recruit.demo.service.impl;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import recruit.demo.client.IdentityClient;
import recruit.demo.dto.FileLinkDto;
import recruit.demo.storage.StorageService;
import recruit.demo.dto.CandidateProfileDto;
import recruit.demo.dto.ConfirmCvRequest;
import recruit.demo.entity.CandidateProfile;
import recruit.demo.entity.CvData;
import recruit.demo.entity.CvDocument;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.CandidateProfileRepository;
import recruit.demo.repository.CvDataRepository;
import recruit.demo.repository.CvDocumentRepository;
import recruit.demo.repository.JobApplicationRepository;
import recruit.demo.security.UserPrincipal;
import recruit.demo.service.CvService;
import recruit.demo.service.SettingService;
import recruit.demo.service.cv.CvExtractionModule;
import recruit.demo.service.cv.CvProfileMapper;
import recruit.demo.service.cvmatch.CvMatchEvents;
import tools.jackson.databind.ObjectMapper;

import java.util.List;
import java.util.Optional;
import recruit.demo.service.cv.CvFileType;

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
    private CvServiceImpl service;

    private final CandidateProfile candidate = CandidateProfile.builder().id(7).userId(70).build();

    @BeforeEach
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
        service = new CvServiceImpl(identity, cvData, candidates, settings, extraction, new CvProfileMapper(),
                storage, events, new ObjectMapper(), docs, apps);

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
    void uploadFailureOnStorageDoesNotWriteFileUrl() {
        when(docs.countByCandidateId(7)).thenReturn(0L);
        when(extraction.extract(any(), any())).thenReturn(new ObjectMapper().createObjectNode());
        doThrow(new ApiException(HttpStatus.BAD_GATEWAY, "down")).when(storage).putPrivate(any(), any(), any());
        var file = new MockMultipartFile("file", "cv.pdf", "application/pdf", new byte[]{1});

        assertEquals(HttpStatus.BAD_GATEWAY,
                assertThrows(ApiException.class, () -> service.uploadNew(file, null)).getStatus());
        verify(cvData, never()).save(argThat(d -> CvService.FILE_URL.equals(d.getField())));
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
}
