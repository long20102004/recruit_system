package recruit.demo.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import recruit.demo.repository.RecruiterProfileRepository;
import recruit.demo.security.SecurityUtils;

import java.util.List;

@RestController
@RequestMapping("/api/recruiter/companies")
@PreAuthorize("hasRole('RECRUITER')")
@RequiredArgsConstructor
public class RecruiterCompanyMembershipController {
    private final RecruiterProfileRepository memberships;

    public record Membership(Integer id, String name) {}

    @GetMapping
    @Transactional(readOnly = true)
    public List<Membership> mine() {
        return memberships.findByUserIdWithCompany(SecurityUtils.currentUser().getId()).stream()
            .map(profile -> new Membership(profile.getCompany().getId(), profile.getCompany().getName())).toList();
    }

    @DeleteMapping("/{companyId}/membership")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    @Transactional
    public void leave(@PathVariable Integer companyId) {
        memberships.deleteByUserIdAndCompanyId(SecurityUtils.currentUser().getId(), companyId);
    }
}
