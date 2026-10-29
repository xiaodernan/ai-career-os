package com.careeros.push.service;

import com.careeros.push.entity.PushSubscription;

/**
 * Outbound Web Push port (roadmap 33.2): wakes one browser registration.
 *
 * <p>The push carries no payload. The worker that wakes fetches the authenticated inbox and
 * decides what to show, so no signal text, saved-search name or count ever transits a push
 * service. The port therefore needs nothing but the registration: the endpoint to call and the
 * keys the registration already holds.
 *
 * <p>The answer is an outcome rather than an exception because the caller is a morning sweep
 * walking many registrations: one dead browser must not abort the other accounts' rings. A
 * {@link Outcome#GONE} is the push service saying the registration no longer exists, and the
 * caller prunes the row; every other refusal is metered and left in place, never retried inside
 * the same pass -- a push service that answered 503 once may answer 201 in the morning.
 */
public interface PushSender {

    Outcome send(PushSubscription subscription);

    /** What the push service did with one wake, as the sweep needs to know it. */
    enum Outcome {
        /** The push service accepted the wake. */
        SENT,
        /** `404` or `410`: the browser is gone and the registration should be deleted. */
        GONE,
        /** Any other status, or a transport that could not reach the service. Counted, not retried. */
        REFUSED,
        /** No VAPID keys are configured; registrations are kept but nothing leaves the building. */
        NOT_CONFIGURED
    }
}
