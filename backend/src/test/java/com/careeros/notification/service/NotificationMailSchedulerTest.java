package com.careeros.notification.service;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;

/**
 * The signal mail's clock (roadmap 22.1).
 *
 * <p>The morning run asks the service for one pass and a sweep that throws is logged, never
 * rethrown -- a scheduler thread that dies costs every future morning.
 */
class NotificationMailSchedulerTest {

    @Test
    void the_morning_run_asks_the_service_for_one_pass() {
        NotificationMailService mail = mock(NotificationMailService.class);

        new NotificationMailScheduler(mail).send();

        verify(mail).mailPending();
    }

    @Test
    void a_failed_sweep_is_logged_rather_than_thrown() {
        NotificationMailService mail = mock(NotificationMailService.class);
        when(mail.mailPending()).thenThrow(new IllegalStateException("no audience"));

        assertThatCode(() -> new NotificationMailScheduler(mail).send())
                .doesNotThrowAnyException();
    }
}
