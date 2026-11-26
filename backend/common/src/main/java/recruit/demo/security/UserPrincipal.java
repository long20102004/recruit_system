package recruit.demo.security;

import lombok.Getter;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import recruit.demo.enums.Role;
import recruit.demo.enums.UserStatus;

import java.util.Collection;
import java.util.List;

@Getter
public class UserPrincipal implements UserDetails {

    private final Integer id;
    private final String email;
    private final String password;
    private final String fullName;
    private final Role role;
    private final UserStatus status;
    /** Epoch giây; JWT có iat nhỏ hơn bị từ chối. Null = không giới hạn. */
    private final Long sessionsValidAfter;
    /** Quyền theo ma trận RBAC của role (vd "job:create"); dùng với @PreAuthorize("hasAuthority('…')"). */
    private final java.util.Set<String> permissions;

    public UserPrincipal(Integer id, String email, String password, String fullName, Role role, UserStatus status) {
        this(id, email, password, fullName, role, status, null);
    }

    public UserPrincipal(Integer id, String email, String password, String fullName, Role role, UserStatus status,
                         Long sessionsValidAfter) {
        this(id, email, password, fullName, role, status, sessionsValidAfter, java.util.Set.of());
    }

    public UserPrincipal(Integer id, String email, String password, String fullName, Role role, UserStatus status,
                         Long sessionsValidAfter, java.util.Collection<String> permissions) {
        this.id = id; this.email = email; this.password = password;
        this.fullName = fullName; this.role = role; this.status = status;
        this.sessionsValidAfter = sessionsValidAfter;
        this.permissions = permissions == null ? java.util.Set.of() : java.util.Set.copyOf(permissions);
    }

    public boolean hasPermission(String permission) {
        return permissions.contains(permission);
    }

    /** Token phát hành trước mốc vô hiệu phiên thì không còn hợp lệ. */
    public boolean acceptsTokenIssuedAt(java.util.Date issuedAt) {
        if (sessionsValidAfter == null) return true;
        return issuedAt != null && issuedAt.getTime() / 1000 >= sessionsValidAfter;
    }

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        List<GrantedAuthority> authorities = new java.util.ArrayList<>();
        authorities.add(new SimpleGrantedAuthority("ROLE_" + role.name()));
        permissions.stream().sorted().forEach(p -> authorities.add(new SimpleGrantedAuthority(p)));
        return authorities;
    }

    @Override
    public String getPassword() {
        return password;
    }

    @Override
    public String getUsername() {
        return email;
    }

    @Override
    public boolean isAccountNonExpired() {
        return true;
    }

    @Override
    public boolean isAccountNonLocked() {
        return status != UserStatus.BANNED;
    }

    @Override
    public boolean isCredentialsNonExpired() {
        return true;
    }

    @Override
    public boolean isEnabled() {
        return status == UserStatus.ACTIVE;
    }
}
