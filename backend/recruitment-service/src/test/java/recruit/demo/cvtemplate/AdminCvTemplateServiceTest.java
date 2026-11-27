package recruit.demo.cvtemplate;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockMultipartFile;
import recruit.demo.cvtemplate.CvTemplateDtos.AdminCvTemplateDto;
import recruit.demo.cvtemplate.CvTemplateDtos.CreateConfigTemplateRequest;
import recruit.demo.cvtemplate.CvTemplateDtos.UpdateConfigTemplateRequest;
import recruit.demo.dto.FileLinkDto;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.CvDocumentRepository;
import recruit.demo.storage.StorageService;

import java.io.IOException;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AdminCvTemplateServiceTest {

    @Mock
    private CvTemplateRepository cvTemplateRepository;
    @Mock
    private CvDocumentRepository cvDocumentRepository;
    @Mock
    private CvRenderService cvRenderService;
    @Mock
    private StorageService storageService;

    private final DocxTemplateValidator docxValidator = new DocxTemplateValidator();
    private AdminCvTemplateService service;

    @BeforeEach
    void setUp() {
        service = new AdminCvTemplateService(
                cvTemplateRepository,
                cvDocumentRepository,
                cvRenderService,
                docxValidator,
                storageService
        );
    }

    private static CvTemplateConfig validConfig() {
        return CvTemplateConfig.builder()
                .layout("ONE_COLUMN")
                .font("Tinos")
                .accent("#1f1d1a")
                .background("#ffffff")
                .header("CENTER")
                .heading("UPPERCASE_RULE")
                .dates("RIGHT_INLINE")
                .density("COMPACT")
                .margin("NORMAL")
                .sections(List.of("info", "education", "experience", "skills"))
                .build();
    }

    @Test
    void createAndUpdateConfigTemplatePersistsAndUploadsThumbnail() {
        when(cvTemplateRepository.existsByNameIgnoreCase("Harvard Pro")).thenReturn(false);
        when(cvRenderService.renderConfigPdf(any(), any(), any())).thenReturn(new byte[]{1, 2, 3});
        when(cvRenderService.renderFirstPagePng(any())).thenReturn(new byte[]{4, 5, 6});
        when(cvTemplateRepository.saveAndFlush(any(CvTemplate.class))).thenAnswer(inv -> {
            CvTemplate t = inv.getArgument(0);
            if (t.getId() == null) t.setId(10);
            return t;
        });
        when(cvTemplateRepository.save(any(CvTemplate.class))).thenAnswer(inv -> inv.getArgument(0));
        when(cvDocumentRepository.countByTemplateId(10)).thenReturn(0L);
        when(storageService.presignGet(anyString(), anyString(), eq(true)))
                .thenReturn(new FileLinkDto("https://r2.example/thumb.png", Instant.now().plusSeconds(300)));

        AdminCvTemplateDto created = service.createConfig(new CreateConfigTemplateRequest("Harvard Pro", validConfig()));

        assertEquals(10, created.getId());
        assertEquals("Harvard Pro", created.getName());
        assertEquals(CvTemplateType.CONFIG, created.getType());
        assertEquals("https://r2.example/thumb.png", created.getThumbnailUrl());
        verify(storageService).putPrivate(startsWith("cv-templates/10/thumb-"), any(), eq("image/png"));
        verify(storageService).putPrivate(startsWith("cv-templates/10/preview-"), any(), eq("application/pdf"));

        // Update config
        CvTemplate stored = CvTemplate.builder()
                .id(10)
                .name("Harvard Pro")
                .type(CvTemplateType.CONFIG)
                .status(CvTemplateStatus.ACTIVE)
                .config(validConfig())
                .thumbnailKey("cv-templates/10/thumb-old.png")
                .previewPdfKey("cv-templates/10/preview-old.pdf")
                .build();
        when(cvTemplateRepository.findById(10)).thenReturn(Optional.of(stored));
        when(cvTemplateRepository.existsByNameIgnoreCaseAndIdNot("Harvard V2", 10)).thenReturn(false);

        AdminCvTemplateDto updated = service.updateConfig(10, new UpdateConfigTemplateRequest("Harvard V2", validConfig()));
        assertEquals("Harvard V2", updated.getName());
        verify(storageService).deletePrivateQuietly("cv-templates/10/thumb-old.png");
        verify(storageService).deletePrivateQuietly("cv-templates/10/preview-old.pdf");
    }

    @Test
    void rejectsDuplicateNameAndInvalidConfigOptions() {
        when(cvTemplateRepository.existsByNameIgnoreCase("Harvard")).thenReturn(true);
        ApiException dupEx = assertThrows(ApiException.class,
                () -> service.createConfig(new CreateConfigTemplateRequest("Harvard", validConfig())));
        assertEquals(HttpStatus.CONFLICT, dupEx.getStatus());

        when(cvTemplateRepository.existsByNameIgnoreCase("Bad Font")).thenReturn(false);
        CvTemplateConfig badFont = validConfig();
        badFont.setFont("Comic Sans");
        ApiException fontEx = assertThrows(ApiException.class,
                () -> service.createConfig(new CreateConfigTemplateRequest("Bad Font", badFont)));
        assertEquals(HttpStatus.BAD_REQUEST, fontEx.getStatus());
    }

    @Test
    void blocksHidingOrDeletingDefaultTemplateAndDeletingInUseTemplate() {
        CvTemplate defaultTpl = CvTemplate.builder()
                .id(1)
                .name("Harvard")
                .type(CvTemplateType.CONFIG)
                .status(CvTemplateStatus.ACTIVE)
                .defaultTemplate(true)
                .build();
        when(cvTemplateRepository.findById(1)).thenReturn(Optional.of(defaultTpl));

        ApiException hideEx = assertThrows(ApiException.class,
                () -> service.updateStatus(1, CvTemplateStatus.HIDDEN));
        assertEquals(HttpStatus.CONFLICT, hideEx.getStatus());

        ApiException delDefaultEx = assertThrows(ApiException.class, () -> service.delete(1));
        assertEquals(HttpStatus.CONFLICT, delDefaultEx.getStatus());

        CvTemplate usedTpl = CvTemplate.builder()
                .id(2)
                .name("Two Col")
                .type(CvTemplateType.CONFIG)
                .status(CvTemplateStatus.ACTIVE)
                .defaultTemplate(false)
                .build();
        when(cvTemplateRepository.findById(2)).thenReturn(Optional.of(usedTpl));
        when(cvDocumentRepository.countByTemplateId(2)).thenReturn(3L);

        ApiException delUsedEx = assertThrows(ApiException.class, () -> service.delete(2));
        assertEquals(HttpStatus.CONFLICT, delUsedEx.getStatus());
        assertTrue(delUsedEx.getMessage().contains("3"));
    }

    @Test
    void deletesUnusedTemplateAndCleansUpR2ObjectsAfterDbDelete() {
        CvTemplate unused = CvTemplate.builder()
                .id(5)
                .name("Unused Word")
                .type(CvTemplateType.DOCX)
                .status(CvTemplateStatus.HIDDEN)
                .defaultTemplate(false)
                .docxKey("cv-templates/5/a.docx")
                .previewPdfKey("cv-templates/5/preview-a.pdf")
                .thumbnailKey("cv-templates/5/thumb-a.png")
                .build();
        when(cvTemplateRepository.findById(5)).thenReturn(Optional.of(unused));
        when(cvDocumentRepository.countByTemplateId(5)).thenReturn(0L);

        service.delete(5);

        verify(cvTemplateRepository).delete(unused);
        verify(cvTemplateRepository).flush();
        verify(storageService).deletePrivateQuietly("cv-templates/5/a.docx");
        verify(storageService).deletePrivateQuietly("cv-templates/5/preview-a.pdf");
        verify(storageService).deletePrivateQuietly("cv-templates/5/thumb-a.png");
    }

    @Test
    void setDefaultSwitchesFlagFromOldDefaultToTarget() {
        CvTemplate oldDefault = CvTemplate.builder()
                .id(1).name("Harvard").status(CvTemplateStatus.ACTIVE).defaultTemplate(true).build();
        CvTemplate nextDefault = CvTemplate.builder()
                .id(2).name("Modern").status(CvTemplateStatus.ACTIVE).defaultTemplate(false).build();

        when(cvTemplateRepository.findById(2)).thenReturn(Optional.of(nextDefault));
        when(cvTemplateRepository.findFirstByDefaultTemplateTrue()).thenReturn(Optional.of(oldDefault));
        when(cvTemplateRepository.saveAndFlush(any(CvTemplate.class))).thenAnswer(inv -> inv.getArgument(0));
        when(cvTemplateRepository.save(any(CvTemplate.class))).thenAnswer(inv -> inv.getArgument(0));
        when(cvDocumentRepository.countByTemplateId(2)).thenReturn(0L);

        AdminCvTemplateDto res = service.setDefault(2);
        assertFalse(oldDefault.isDefaultTemplate());
        assertTrue(res.isDefaultTemplate());
        verify(cvTemplateRepository).saveAndFlush(oldDefault);
    }

    @Test
    void createDocxValidatesConvertsViaGotenbergAndStoresAllObjectsOnR2() throws IOException {
        byte[] docxBytes = HarvardSampleDocxGenerator.generateBytes();
        MockMultipartFile file = new MockMultipartFile(
                "file",
                "harvard-custom.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                docxBytes
        );

        when(cvTemplateRepository.existsByNameIgnoreCase("Word Harvard")).thenReturn(false);
        when(cvRenderService.renderDocxPdf(eq(docxBytes), any(), any())).thenReturn(new byte[]{10, 20, 30});
        when(cvRenderService.renderFirstPagePng(any())).thenReturn(new byte[]{40, 50});
        when(cvTemplateRepository.saveAndFlush(any(CvTemplate.class))).thenAnswer(inv -> {
            CvTemplate t = inv.getArgument(0);
            if (t.getId() == null) t.setId(7);
            return t;
        });
        when(cvTemplateRepository.save(any(CvTemplate.class))).thenAnswer(inv -> inv.getArgument(0));
        when(cvDocumentRepository.countByTemplateId(7)).thenReturn(0L);
        when(storageService.presignGet(anyString(), anyString(), eq(true)))
                .thenReturn(new FileLinkDto("https://r2.example/thumb-7.png", Instant.now().plusSeconds(300)));

        AdminCvTemplateDto created = service.createDocx(file, "Word Harvard");

        assertEquals(7, created.getId());
        assertEquals(CvTemplateType.DOCX, created.getType());
        assertTrue(created.isHasPreviewPdf());
        verify(storageService).putPrivate(startsWith("cv-templates/7/"), eq(docxBytes),
                eq("application/vnd.openxmlformats-officedocument.wordprocessingml.document"));
        verify(storageService).putPrivate(startsWith("cv-templates/7/preview-"), any(), eq("application/pdf"));
        verify(storageService).putPrivate(startsWith("cv-templates/7/thumb-"), any(), eq("image/png"));
    }

    @Test
    void setDefaultRejectsHiddenTemplateAndPreviewPdfGeneratesForSeededConfig() {
        CvTemplate hidden = CvTemplate.builder()
                .id(3).name("Hidden").status(CvTemplateStatus.HIDDEN).build();
        when(cvTemplateRepository.findById(3)).thenReturn(Optional.of(hidden));

        ApiException ex = assertThrows(ApiException.class, () -> service.setDefault(3));
        assertEquals(HttpStatus.CONFLICT, ex.getStatus());

        CvTemplate seededConfig = CvTemplate.builder()
                .id(1).name("Harvard").type(CvTemplateType.CONFIG).status(CvTemplateStatus.ACTIVE)
                .config(validConfig()).build();
        when(cvTemplateRepository.findById(1)).thenReturn(Optional.of(seededConfig));
        when(cvRenderService.renderPdf(eq(seededConfig), any(), any())).thenReturn(new byte[]{1, 2, 3});
        when(cvRenderService.renderFirstPagePng(any())).thenReturn(new byte[]{4, 5});
        when(cvTemplateRepository.save(any(CvTemplate.class))).thenAnswer(inv -> inv.getArgument(0));
        when(storageService.presignGet(anyString(), anyString(), eq(true)))
                .thenReturn(new FileLinkDto("https://r2.example/preview.pdf", Instant.now().plusSeconds(300)));

        FileLinkDto link = service.previewPdf(1);
        assertEquals("https://r2.example/preview.pdf", link.getUrl());
        verify(storageService).putPrivate(startsWith("cv-templates/1/preview-"), any(), eq("application/pdf"));
        verify(storageService).putPrivate(startsWith("cv-templates/1/thumb-"), any(), eq("image/png"));
    }

    @Test
    void gotenbergClientThrowsServiceUnavailableWhenEndpointDown() {
        GotenbergClient client = new GotenbergClient("http://127.0.0.1:59999", 1000);
        ApiException ex = assertThrows(ApiException.class, () -> client.convertDocxToPdf(new byte[]{1, 2, 3}));
        assertEquals(HttpStatus.SERVICE_UNAVAILABLE, ex.getStatus());
        assertEquals("Chuyển đổi chưa sẵn sàng", ex.getMessage());
    }
}
