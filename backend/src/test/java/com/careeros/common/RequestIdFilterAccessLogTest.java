package com.careeros.common;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import jakarta.servlet.FilterChain;
import java.io.IOException;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

/**
 * Every answer leaves one line, and the line belongs to the answer's id.
 *
 * <p>The id alone only joins the lines a route chose to write; a request that hung
 * and logged nothing is still the one an operator has to find. The access line is
 * that floor: method, path, status and elapsed time, written under the same id --
 * and the request's own path, never its query, because a search term is the
 * reader's text and a reset link carries a token.
 */
class RequestIdFilterAccessLogTest {

    private final RequestIdFilter filter = new RequestIdFilter();
    private ListAppender<ILoggingEvent> appender;
    private Logger accessLog;

    @BeforeEach
    void attach() {
        accessLog = (Logger) LoggerFactory.getLogger("careeros.access");
        appender = new ListAppender<>();
        appender.start();
        accessLog.addAppender(appender);
    }

    @AfterEach
    void detach() {
        accessLog.detachAppender(appender);
        MDC.clear();
    }

    private MockHttpServletRequest request(String method, String uri) {
        MockHttpServletRequest request = new MockHttpServletRequest(method, uri);
        request.setRequestURI(uri);
        return request;
    }

    @Test
    void aCompletedRequestLeavesItsMethodPathStatusAndTime() throws Exception {
        MockHttpServletResponse response = new MockHttpServletResponse();
        response.setStatus(200);
        filter.doFilter(request("GET", "/api/v1/jobs"), response,
                (req, res) -> ((MockHttpServletResponse) res).setStatus(200));

        assertThat(appender.list).hasSize(1);
        assertThat(appender.list.get(0).getFormattedMessage())
                .matches("GET /api/v1/jobs 200 \\d+ms");
    }

    @Test
    void theLineCarriesTheRequestsId() throws Exception {
        MockHttpServletResponse response = new MockHttpServletResponse();
        filter.doFilter(request("POST", "/api/v1/jobs"), response,
                (req, res) -> ((MockHttpServletResponse) res).setStatus(201));

        ILoggingEvent event = appender.list.get(0);
        assertThat(event.getMDCPropertyMap().get(RequestIdFilter.MDC_KEY))
                .isNotNull()
                .isEqualTo(response.getHeader(RequestIdFilter.HEADER));
        assertThat(event.getFormattedMessage()).startsWith("POST /api/v1/jobs 201 ");
    }

    @Test
    void theQueryStringIsNotInTheLine() throws Exception {
        MockHttpServletRequest request = request("GET", "/api/v1/jobs");
        request.setQueryString("q=my-private-search&token=secret");
        MockHttpServletResponse response = new MockHttpServletResponse();
        filter.doFilter(request, response, (req, res) -> { });

        String line = appender.list.get(0).getFormattedMessage();
        assertThat(line).startsWith("GET /api/v1/jobs 200 ");
        assertThat(line).doesNotContain("my-private-search").doesNotContain("secret");
    }

    @Test
    void aChainThatThrowsStillLeavesALine() {
        MockHttpServletResponse response = new MockHttpServletResponse();
        FilterChain exploding = (req, res) -> {
            throw new IOException("client went away");
        };

        assertThatThrownBy(() -> filter.doFilter(request("GET", "/api/v1/me"), response, exploding))
                .isInstanceOf(IOException.class);

        assertThat(appender.list).hasSize(1);
        // "error", not a number: the container will answer 500 after this filter unwinds.
        assertThat(appender.list.get(0).getFormattedMessage())
                .matches("GET /api/v1/me error \\d+ms");
        assertThat(MDC.get(RequestIdFilter.MDC_KEY)).isNull();
    }
}
