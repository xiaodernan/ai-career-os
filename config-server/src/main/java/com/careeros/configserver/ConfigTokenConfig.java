package com.careeros.configserver;

import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Wires the optional token gate for the config server (Epic 114).
 *
 * <p>Set {@code CONFIG_SERVER_TOKEN} to enable it; unset, everything behaves as before so
 * local/dev iteration stays predictable. The health probe is deliberately exempt.
 */
@Configuration
public class ConfigTokenConfig {

    private final String token;

    public ConfigTokenConfig(org.springframework.core.env.Environment env) {
        this.token = env.getProperty(ConfigTokenFilter.ENV, "");
    }

    @Bean
    public FilterRegistrationBean<ConfigTokenFilter> configTokenFilterRegistration() {
        FilterRegistrationBean<ConfigTokenFilter> registration = new FilterRegistrationBean<>();
        registration.setFilter(new ConfigTokenFilter(token));
        registration.addUrlPatterns("/*");
        registration.setOrder(/* very high: before the dispatcher */ 1);
        registration.setName("configTokenFilter");
        return registration;
    }
}