package com.careeros.notification.service;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;
import org.mockito.InOrder;

/**
 * The signals' morning clock (roadmap 22.1, 33.3).
 *
 * <p>The run asks both halves for one pass, and a half that throws is logged rather than
 * rethrown -- and does not take the other half with it: a scheduler thread that dies costs
 * every future morning, and a relay that refuses the letters should not silence the ring.
 */
class NotificationMailSchedulerTest {

    @Test
    void the_morning_run_asks_the_letter_and_then_the_ring_for_one_pass() {
        NotificationMailService mail = mock(NotificationMailService.class);
        NotificationPushService push = mock(NotificationPushService.class);

        new NotificationMailScheduler(mail, push).send();

        InOrder order = inOrder(mail, push);
        order.verify(mail).mailPending();
        order.verify(push).pushPending();
    }

    @Test
    void a_failed_letter_sweep_still_rings_the_browsers() {
        NotificationMailService mail = mock(NotificationMailService.class);
        NotificationPushService push = mock(NotificationPushService.class);
        when(mail.mailPending()).thenThrow(new IllegalStateException("no audience"));

        assertThatCode(() -> new NotificationMailScheduler(mail, push).send())
                .doesNotThrowAnyException();

        verify(push).pushPending();
    }

    @Test
    void a_failed_ring_is_logged_rather_than_thrown() {
        NotificationMailService mail = mock(NotificationMailService.class);
        NotificationPushService push = mock(NotificationPushService.class);
        when(push.pushPending()).thenThrow(new IllegalStateException("push service down"));

        assertThatCode(() -> new NotificationMailScheduler(mail, push).send())
                .doesNotThrowAnyException();
    }
}
