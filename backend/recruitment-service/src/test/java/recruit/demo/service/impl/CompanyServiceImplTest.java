package recruit.demo.service.impl;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import recruit.demo.client.IdentityClient;
import recruit.demo.storage.StorageService;
import recruit.demo.dto.CompanyDtos.CompanyProfileUpdateRequest;
import recruit.demo.entity.Company;
import recruit.demo.entity.RecruiterProfile;
import recruit.demo.enums.CompanyStatus;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;
import recruit.demo.exception.ApiException;
import recruit.demo.repository.CompanyFollowerRepository;
import recruit.demo.repository.CompanyRepository;
import recruit.demo.repository.JobRepository;
import recruit.demo.repository.RecruiterProfileRepository;
import recruit.demo.security.UserPrincipal;

import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class CompanyServiceImplTest {

    private CompanyRepository companyRepo;
    private CompanyFollowerRepository followerRepo;
    private RecruiterProfileRepository recruiterRepo;
    private JobRepository jobRepo;
    private IdentityClient identityClient;
    private StorageService storage;
    private CompanyServiceImpl service;

    @BeforeEach
    void setUp() {
        companyRepo = mock(CompanyRepository.class);
        followerRepo = mock(CompanyFollowerRepository.class);
        recruiterRepo = mock(RecruiterProfileRepository.class);
        jobRepo = mock(JobRepository.class);
        identityClient = mock(IdentityClient.class);
        storage = mock(StorageService.class);
        service = new CompanyServiceImpl(companyRepo, followerRepo, recruiterRepo, jobRepo, identityClient, storage);
        when(companyRepo.save(any(Company.class))).thenAnswer(i -> i.getArgument(0));
    }

    @AfterEach
    void clear() {
        SecurityContextHolder.clearContext();
    }

    private void loginAs(int id, Role role) {
        var p = new UserPrincipal(id, "u" + id + "@x.test", "", "User " + id, role, UserStatus.ACTIVE);
        SecurityContextHolder.getContext().setAuthentication(
                new UsernamePasswordAuthenticationToken(p, null, p.getAuthorities()));
    }

    @Test
    void approveThrowsConflictWhenNotPending() {
        loginAs(1, Role.ADMIN);
        Company c = Company.builder().id(10).name("Lumen").status(CompanyStatus.ACTIVE).build();
        when(companyRepo.findById(10)).thenReturn(Optional.of(c));

        ApiException ex = assertThrows(ApiException.class, () -> service.approve(10));
        assertEquals(HttpStatus.CONFLICT, ex.getStatus());
    }

    @Test
    void approveTransitionsPendingToActiveAndRecordsAudit() {
        loginAs(1, Role.ADMIN);
        Company c = Company.builder().id(10).name("Lumen").status(CompanyStatus.PENDING).build();
        when(companyRepo.findById(10)).thenReturn(Optional.of(c));

        var dto = service.approve(10);
        assertEquals(CompanyStatus.ACTIVE, dto.status());
        assertNotNull(c.getApprovedAt());
        verify(identityClient).recordAuditLog(eq("APPROVE_COMPANY"), eq("Duyệt công ty"), any(), eq("Lumen"), eq(1), any());
    }

    @Test
    void rejectRequiresReasonAndChecksPending() {
        loginAs(1, Role.ADMIN);
        assertEquals(HttpStatus.BAD_REQUEST,
                assertThrows(ApiException.class, () -> service.reject(10, "   ")).getStatus());

        Company c = Company.builder().id(10).name("Lumen").status(CompanyStatus.ACTIVE).build();
        when(companyRepo.findById(10)).thenReturn(Optional.of(c));
        assertEquals(HttpStatus.CONFLICT,
                assertThrows(ApiException.class, () -> service.reject(10, "Invalid tax code")).getStatus());
    }

    @Test
    void lockAndUnlockTransitions() {
        loginAs(1, Role.ADMIN);
        Company c = Company.builder().id(10).name("Lumen").status(CompanyStatus.ACTIVE).build();
        when(companyRepo.findById(10)).thenReturn(Optional.of(c));

        assertEquals(CompanyStatus.LOCKED, service.lock(10, "Spam").status());
        assertEquals(CompanyStatus.ACTIVE, service.unlock(10).status());
    }

    @Test
    void changingTaxCodeOnActiveCompanyResetsToPending() {
        loginAs(20, Role.RECRUITER);
        Company c = Company.builder().id(5).name("Lumen").taxCode("0100112233").status(CompanyStatus.ACTIVE).build();
        when(recruiterRepo.findFirstByUserIdOrderByCreatedAtAsc(20))
                .thenReturn(Optional.of(RecruiterProfile.builder().id(1).userId(20).company(c).build()));

        var res = service.updateProfile(new CompanyProfileUpdateRequest(
                "Lumen Tech", "0999888777", "Fintech", "100", "Product",
                "https://lumen.vn", "T2-T6", "Không OT", "HCM", "Desc", "Perks",
                List.of("Java"), null, null
        ));
        assertEquals(CompanyStatus.PENDING, res.status());
        assertEquals("0999888777", res.taxCode());
    }

    // ---- specs/008-r2-storage ----

    private Company recruiterCompany() {
        loginAs(20, Role.RECRUITER);
        Company c = Company.builder().id(5).name("Lumen").status(CompanyStatus.ACTIVE)
                .logoKey("companies/5/logo/old.png").licenseFileUrl("companies/5/license/old.pdf").build();
        when(recruiterRepo.findFirstByUserIdOrderByCreatedAtAsc(20))
                .thenReturn(Optional.of(RecruiterProfile.builder().id(1).userId(20).company(c).build()));
        return c;
    }

    @Test
    void logoUploadGoesToPublicBucketAndReplacesOldObject() {
        Company c = recruiterCompany();
        when(storage.publicUrl(any())).thenAnswer(i -> i.getArgument(0) == null ? null : "https://pub.test/" + i.getArgument(0));
        var file = new org.springframework.mock.web.MockMultipartFile("file", "logo.PNG", "image/png", new byte[]{1});

        var dto = service.uploadFile("logo", file);

        assertTrue(c.getLogoKey().matches("companies/5/logo/[0-9a-f-]{36}\\.png"), c.getLogoKey());
        verify(storage).putPublic(c.getLogoKey(), new byte[]{1}, "image/png");
        verify(storage).deletePublicQuietly("companies/5/logo/old.png");
        assertEquals("https://pub.test/" + c.getLogoKey(), dto.logoUrl());
        assertNull(dto.coverUrl());
    }

    @Test
    void logoUploadRejectsNonImage() {
        recruiterCompany();
        var file = new org.springframework.mock.web.MockMultipartFile("file", "logo.pdf", "application/pdf", new byte[]{1});

        assertEquals(HttpStatus.BAD_REQUEST,
                assertThrows(ApiException.class, () -> service.uploadFile("logo", file)).getStatus());
        verifyNoInteractions(storage);
    }

    @Test
    void licenseUploadGoesToPrivateBucket() {
        Company c = recruiterCompany();
        var file = new org.springframework.mock.web.MockMultipartFile("file", "gpkd.pdf", "application/pdf", new byte[]{9});

        service.uploadFile("license", file);

        assertTrue(c.getLicenseFileUrl().startsWith("companies/5/license/"));
        verify(storage).putPrivate(c.getLicenseFileUrl(), new byte[]{9}, "application/pdf");
        verify(storage).deletePrivateQuietly("companies/5/license/old.pdf");
        verify(storage, never()).putPublic(any(), any(), any());
    }

    @Test
    void licenseLinkIsInlinePresignedUrlAndRejectsLegacyPath() {
        loginAs(1, Role.ADMIN);
        Company c = Company.builder().id(10).name("Lumen").licenseFileName("GPKD.pdf")
                .licenseFileUrl("companies/10/license/a.pdf").build();
        when(companyRepo.findById(10)).thenReturn(Optional.of(c));
        var link = recruit.demo.dto.FileLinkDto.builder().url("https://signed").build();
        when(storage.presignGet("companies/10/license/a.pdf", "GPKD.pdf", true)).thenReturn(link);

        assertSame(link, service.licenseLink(10));

        c.setLicenseFileUrl("/app/uploads/companies/10/x.pdf");
        assertEquals(HttpStatus.NOT_FOUND, assertThrows(ApiException.class, () -> service.licenseLink(10)).getStatus());
    }
}
