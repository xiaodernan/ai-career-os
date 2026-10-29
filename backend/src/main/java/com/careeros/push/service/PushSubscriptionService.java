package com.careeros.push.service;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.push.dto.PushDtos.PushSubscriptionItem;
import com.careeros.push.dto.PushDtos.PushSubscriptionRequest;
import com.careeros.push.entity.PushSubscription;
import com.careeros.push.repository.PushSubscriptionRepository;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Pattern;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The browsers an account can be woken through (roadmap 33.1).
 *
 * <p>Registration is an upsert on the endpoint. A browser re-subscribes whenever it likes -- a
 * renewed key, a service worker update, a reader signing in as someone else -- and every one of
 * those is the same registration at the same push service, so a second row would ring that
 * browser twice for one morning. The upsert therefore refreshes the keys and re-points the owner
 * to whoever just registered; the account a browser rings is the account last signed in there,
 * which is also the account whose inbox the worker will fetch when it wakes.
 *
 * <p>Validation happens here rather than at the first send: an endpoint that is not `https`, a
 * key that is not base64url, or a value longer than the column would otherwise be stored and
 * discovered by a failing push at 08:00, where the reader is not and the reason is a stack
 * trace. An endpoint is refused, not repaired -- a mangled URL is not a browser this service
 * can wake, and guessing at it would ring the wrong registration.
 */
@Service
public class PushSubscriptionService {

    /**
     * A list, bounded like the saved-search list (29.4): every morning ring walks it, so an
     * unbounded list is an unbounded number of outbound calls per account per sweep. Ten
     * browsers is more than a reader plausibly signs in on.
     */
    static final int MAX_SUBSCRIPTIONS_PER_USER = 10;

    /** Base64url without padding is what `PushSubscription.toJSON()` hands over. */
    private static final Pattern BASE64URL = Pattern.compile("[A-Za-z0-9_-]+");

    /**
     * The wire shape's own ceiling, repeated here because the service is the boundary that
     * stores the text: bean validation runs only when a controller is in the call path.
     */
    private static final int MAX_ENDPOINT_LENGTH = 2048;

    private final PushSubscriptionRepository subscriptions;

    public PushSubscriptionService(PushSubscriptionRepository subscriptions) {
        this.subscriptions = subscriptions;
    }

    @Transactional(readOnly = true)
    public List<PushSubscriptionItem> list(UUID userId) {
        return subscriptions.findByUserIdOrderByCreatedAtDesc(userId).stream()
                .map(PushSubscriptionItem::of)
                .toList();
    }

    @Transactional
    public PushSubscriptionItem register(UUID userId, PushSubscriptionRequest request) {
        String endpoint = validateEndpoint(request.endpoint());
        String p256dh = validateKey(request.p256dh(), 40, 160, "p256dh");
        String auth = validateKey(request.auth(), 16, 64, "auth");
        String label = label(request.label());

        Optional<PushSubscription> existing = subscriptions.findByEndpointUrl(endpoint);
        if (existing.isPresent()) {
            PushSubscription row = existing.get();
            row.setUserId(userId);
            row.setP256dh(p256dh);
            row.setAuth(auth);
            row.setLabel(label);
            return PushSubscriptionItem.of(subscriptions.save(row));
        }
        if (subscriptions.countByUserId(userId) >= MAX_SUBSCRIPTIONS_PER_USER) {
            throw new ApiException(ApiErrorCode.PUSH_SUBSCRIPTION_LIMIT_REACHED,
                    "An account can be woken on at most " + MAX_SUBSCRIPTIONS_PER_USER
                            + " browsers");
        }
        PushSubscription row = new PushSubscription();
        row.setUserId(userId);
        row.setEndpointUrl(endpoint);
        row.setP256dh(p256dh);
        row.setAuth(auth);
        row.setLabel(label);
        return PushSubscriptionItem.of(subscriptions.save(row));
    }

    @Transactional
    public void delete(UUID userId, UUID id) {
        subscriptions.delete(subscriptions.findByIdAndUserId(id, userId)
                .orElseThrow(() -> new ApiException(ApiErrorCode.PUSH_SUBSCRIPTION_NOT_FOUND,
                        "Push subscription not found")));
    }

    @Transactional
    public void deleteAll(UUID userId) {
        subscriptions.deleteByUserId(userId);
    }

    private static String validateEndpoint(String endpoint) {
        String value = endpoint == null ? "" : endpoint.trim();
        if (value.length() > MAX_ENDPOINT_LENGTH) {
            throw invalid("The push endpoint is longer than a push address can be");
        }
        URI uri;
        try {
            uri = new URI(value);
        } catch (URISyntaxException e) {
            throw invalid("The push endpoint is not a URL");
        }
        // A push service is reached over https at a host of its own; userinfo or a fragment
        // would be part of an address this service never composed.
        if (!"https".equalsIgnoreCase(uri.getScheme()) || uri.getHost() == null
                || uri.getUserInfo() != null || uri.getRawFragment() != null) {
            throw invalid("The push endpoint must be an https address");
        }
        return value;
    }

    private static String validateKey(String key, int min, int max, String name) {
        String value = key == null ? "" : key.trim();
        if (value.length() < min || value.length() > max
                || !BASE64URL.matcher(value).matches()) {
            throw invalid("The push subscription's " + name + " key is malformed");
        }
        return value;
    }

    private static String label(String label) {
        if (label == null) {
            return null;
        }
        String trimmed = label.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private static ApiException invalid(String message) {
        return new ApiException(ApiErrorCode.PUSH_SUBSCRIPTION_INVALID, message);
    }
}
