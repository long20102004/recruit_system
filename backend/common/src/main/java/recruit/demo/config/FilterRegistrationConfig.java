package recruit.demo.config;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import recruit.demo.security.*;
@Configuration
public class FilterRegistrationConfig {
    @Bean
    FilterRegistrationBean<JwtAuthenticationFilter> jwtRegistration(JwtAuthenticationFilter filter) {
        var bean = new FilterRegistrationBean<>(filter); bean.setEnabled(false); return bean;
    }
    @Bean
    FilterRegistrationBean<InternalAccessFilter> internalRegistration(InternalAccessFilter filter) {
        var bean = new FilterRegistrationBean<>(filter); bean.setEnabled(false); return bean;
    }
    @Bean
    @ConditionalOnBean(AuthenticatedRequestHook.class)
    FilterRegistrationBean<AuthenticatedRequestHook> hookRegistration(AuthenticatedRequestHook hook) {
        var bean = new FilterRegistrationBean<>(hook); bean.setEnabled(false); return bean;
    }
}
