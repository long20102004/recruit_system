package recruit.demo.config;
import org.junit.jupiter.api.Test;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.mock.web.MockServletContext;
import org.springframework.web.context.support.AnnotationConfigWebApplicationContext;
import org.springframework.security.web.SecurityFilterChain;
import static org.junit.jupiter.api.Assertions.*;
class SecurityStartupTest {
    @Configuration(proxyBeanMethods=false)
    static class Properties {
        @Bean AppProperties properties(){
            var p=new AppProperties();p.getCors().setAllowedOrigins("http://localhost:5173");return p;
        }
    }
    @Test void sharedWebSecurityConfigurationStartsWithoutDatabaseOrDomainHook(){
        try(var context=new AnnotationConfigWebApplicationContext()){
            context.setServletContext(new MockServletContext());
            context.register(Properties.class,FilterRegistrationConfigTest.Filters.class,SecurityConfig.class,FilterRegistrationConfig.class);
            assertDoesNotThrow(context::refresh);
            assertNotNull(context.getBean(SecurityFilterChain.class));
        }
    }
}
