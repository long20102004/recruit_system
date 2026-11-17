package recruit.demo.config;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.mock.web.MockServletContext;
import recruit.demo.security.*;
import static org.junit.jupiter.api.Assertions.*;
class FilterRegistrationConfigTest {
    @Configuration(proxyBeanMethods=false)
    static class Filters {
        @Bean JwtAuthenticationFilter jwtFilter() {
            var properties=new AppProperties();properties.getJwt().setSecret("test-secret-with-at-least-thirty-two-characters");properties.getJwt().setExpirationMs(60000);
            return new JwtAuthenticationFilter(new JwtService(properties),(id,email)->null);
        }
        @Bean InternalAccessFilter internalFilter(){return new InternalAccessFilter("test-service-token");}
    }
    @Configuration(proxyBeanMethods=false)
    static class WithHook {
        @Bean AuthenticatedRequestHook hook(){return new AuthenticatedRequestHook(){
            @Override protected void doFilterInternal(jakarta.servlet.http.HttpServletRequest req,
                jakarta.servlet.http.HttpServletResponse res,jakarta.servlet.FilterChain chain)
                    throws java.io.IOException,jakarta.servlet.ServletException{chain.doFilter(req,res);}
        };}
    }
    @Test void servicesWithoutDomainHookNeverRegisterANullFilter() {
        new ApplicationContextRunner().withUserConfiguration(Filters.class,FilterRegistrationConfig.class).run(context->{
            assertNull(context.getStartupFailure());assertFalse(context.containsBean("hookRegistration"));
            var registrations=context.getBeansOfType(FilterRegistrationBean.class);
            assertEquals(2,registrations.size());
            for(var bean:registrations.values()){
                assertNotNull(bean.getFilter());assertFalse(bean.isEnabled());
                assertDoesNotThrow(()->bean.onStartup(new MockServletContext()));
            }
        });
    }
    @Test void recruitmentHookIsOnlyInvokedBySecurityNotRegisteredTwice() {
        new ApplicationContextRunner().withUserConfiguration(Filters.class,WithHook.class,FilterRegistrationConfig.class).run(context->{
            assertNull(context.getStartupFailure());
            var registration=context.getBean("hookRegistration",FilterRegistrationBean.class);
            assertSame(context.getBean(AuthenticatedRequestHook.class),registration.getFilter());
            assertFalse(registration.isEnabled());
            assertDoesNotThrow(()->registration.onStartup(new MockServletContext()));
        });
    }
}
