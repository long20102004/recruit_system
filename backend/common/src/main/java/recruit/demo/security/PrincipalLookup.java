package recruit.demo.security;
public interface PrincipalLookup {
    UserPrincipal load(Integer userId, String email);
}
