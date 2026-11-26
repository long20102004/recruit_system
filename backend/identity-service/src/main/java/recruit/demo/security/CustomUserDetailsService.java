package recruit.demo.security;

import lombok.RequiredArgsConstructor;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;
import recruit.demo.repository.UserRepository;
import recruit.demo.service.RbacService;

@Service
@RequiredArgsConstructor
public class CustomUserDetailsService implements UserDetailsService, PrincipalLookup {

    private final UserRepository userRepository;
    private final RbacService rbac;

    @Override
    public UserPrincipal load(Integer userId, String email) {
        UserPrincipal principal = (UserPrincipal) loadUserByUsername(email);
        if (!principal.getId().equals(userId)) throw new UsernameNotFoundException("User not found");
        return principal;
    }

    @Override
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        return userRepository.findByEmailIgnoreCase(username)
                .map(u -> new UserPrincipal(u.getId(), u.getEmail(), u.getPasswordHash(), u.getFullName(), u.getRole(), u.getStatus(),
                        u.sessionsValidAfterEpochSeconds(), rbac.permissionsOf(u.getRole())))
                .orElseThrow(() -> new UsernameNotFoundException("User not found: " + username));
    }
}
