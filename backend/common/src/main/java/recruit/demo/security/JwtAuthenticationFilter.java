package recruit.demo.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtService jwtService;
    private final PrincipalLookup principalLookup;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String header = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (header == null || !header.startsWith("Bearer ")) {
            filterChain.doFilter(request, response);
            return;
        }

        String token = header.substring(7);
        if (jwtService.isValid(token) && SecurityContextHolder.getContext().getAuthentication() == null) {
            String email = jwtService.getEmail(token);
            UserPrincipal principal;
            try {
                principal = principalLookup.load(jwtService.getUserId(token), email);
            } catch (org.springframework.security.core.userdetails.UsernameNotFoundException ex) {
                response.sendError(401); return;
            } catch (recruit.demo.exception.ApiException ex) {
                response.sendError(ex.getStatus().value()); return;
            }
            if (!principal.isEnabled() || !principal.isAccountNonLocked()
                    || !principal.acceptsTokenIssuedAt(jwtService.parseClaims(token).getIssuedAt())) {
                response.sendError(401); return;
            }
            UsernamePasswordAuthenticationToken authentication =
                    new UsernamePasswordAuthenticationToken(principal, null, principal.getAuthorities());
            authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
            SecurityContextHolder.getContext().setAuthentication(authentication);
        }

        filterChain.doFilter(request, response);
    }
}
