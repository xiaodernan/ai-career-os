package com.careeros.notification.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * The morning clock the signal mail runs on (roadmap 22.1).
 *
 * <p>Half an hour before the Monday letter, the inbox's waiting signals are carried out by
 * mail: early enough to be read with the day's first coffee, late enough that the previous
 * night's pulls have been filed. The hour is configurable ({@code careeros.signals.cron}) so a
 * deployment can move it without a rebuild. Nothing is thrown out of the sweep -- every
 * account's failure is already a warn line inside it, and a morning that could not even read
 * the audience is logged rather than crashing the scheduler's thread.
 */
@Component
public class NotificationMailScheduler {

    private static final Logger log = LoggerFactory.getLogger(NotificationMailScheduler.class);

    private final NotificationMailService mail;

    public NotificationMailScheduler(NotificationMailService mail) {
        this.mail = mail;
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
    }
}
