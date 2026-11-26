package recruit.demo.service.impl;
import recruit.demo.service.*;
import recruit.demo.enums.Role;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import recruit.demo.entity.*;
import recruit.demo.repository.*;
import recruit.demo.security.UserPrincipal;
@Service
@RequiredArgsConstructor
public class ProfileProvisioningServiceImpl implements ProfileProvisioningService {
    private final CandidateProfileRepository candidates;
    private final RecruiterProfileRepository recruiters;
    private final CompanyRepository companies;
    @Transactional
    public void ensureProfile(UserPrincipal user) {
        if (user.getRole() == Role.CANDIDATE) {
            candidates.insertIfAbsent(user.getId());
        } else if (user.getRole() == Role.RECRUITER &&
                recruiters.findFirstByUserIdOrderByCreatedAtAsc(user.getId()).isEmpty()) {
            // A stable company key prevents duplicate company creation on concurrent first requests.
            String companyName = user.getFullName() + " #" + user.getId();
            companies.insertIfAbsent(companyName);
            Company company = companies.findByNameIgnoreCase(companyName).orElseThrow();
            recruiters.insertIfAbsent(user.getId(), company.getId());
        }
    }
}
