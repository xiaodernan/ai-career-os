package com.careeros.notification.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The morning clock the signals run on (roadmap 22.1, 33.3).
 *
 * <p>Half an hour before the Monday letter, the inbox's waiting signals are carried out: first
 * by mail, then by ringing the browsers that asked to be woken. The hour is configurable
 * ({@code careeros.signals.cron}) so a deployment can move it without a rebuild.
 *
 * <p>The two halves are caught separately on purpose. They share an audience but not a failure
 * mode: an SMTP relay that refuses every letter should not silence a browser that could have
 * rung, and a push transport that hangs should not cost the morning its letters. Nothing is
 * thrown out of the run -- a scheduler thread that dies costs every future morning.
 */
@Component
public class NotificationMailScheduler {

    private static final Logger log = LoggerFactory.getLogger(NotificationMailScheduler.class);

    private final NotificationMailService mail;
    private final NotificationPushService push;

    public NotificationMailScheduler(NotificationMailService mail, NotificationPushService push) {
        this.mail = mail;
        this.push = push;
    }

    @Scheduled(cron = "${careeros.signals.cron:0 30 7 * * *}")
    public void send() {
        try {
            int mailed = mail.mailPending();
            if (mailed > 0) {
                log.info("signal mail delivered to {} account(s)", mailed);
            }
        } catch (RuntimeException e) {
            log.warn("the signal mail sweep could not run", e);
        }
        try {
            int rung = push.pushPending();
            if (rung > 0) {
                log.info("morning ring delivered to {} account(s)", rung);
            }
        } catch (RuntimeException e) {
            log.warn("the morning ring sweep could not run", e);
        }
    }
}
