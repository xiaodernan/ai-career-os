package com.careeros.push.service;

import com.careeros.push.entity.PushSubscription;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The sender a deployment without VAPID keys gets (roadmap 33.2).
 *
 * <p>Push is an optional channel: a fresh checkout, a CI run and an install that never opted
 * into notifications all boot without a key pair. The registration routes still work -- a
 * browser may opt in before the operator has generated keys, and bringing the keys later must
 * not silently leave those browsers unreachable -- but every wake answers
 * {@link Outcome#NOT_CONFIGURED} so the sweep can say why the bell stayed silent. The boot line
 * in {@code PushConfig} is the operator's report; this class does not repeat it per browser.
 */
public class NoopPushSender implements PushSender {

    private static final Logger log = LoggerFactory.getLogger(NoopPushSender.class);

    @Override
    public Outcome send(PushSubscription subscription) {
        log.debug("no push left for subscription {}: no VAPID key pair is configured",
                subscription.getId());
        return Outcome.NOT_CONFIGURED;
    }
}
