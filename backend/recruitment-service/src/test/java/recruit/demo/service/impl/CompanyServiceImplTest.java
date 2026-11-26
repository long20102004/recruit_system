package recruit.demo.service.impl;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import recruit.demo.client.IdentityClient;
import recruit.demo.config.AppProperties;
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
    private CompanyServiceImpl service;

    @BeforeEach
    void setUp() {
        companyRepo = mock(CompanyRepository.class);
        followerRepo = mock(CompanyFollowerRepository.class);
        recruiterRepo = mock(RecruiterProfileRepository.class);
        jobRepo = mock(JobRepository.class);
        identityClient = mock(IdentityClient.class);
        service = new CompanyServiceImpl(companyRepo, followerRepo, recruiterRepo, jobRepo, identityClient, new AppProperties());
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
}
