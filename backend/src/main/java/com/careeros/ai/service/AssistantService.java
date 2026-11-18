package com.careeros.ai.service;

import com.careeros.ai.AiServiceClient;
import com.careeros.ai.dto.NextStepRequest;
import com.careeros.application.repository.ApplicationRepository;
import com.careeros.interview.repository.InterviewSessionRepository;
import com.careeros.offer.entity.OfferRow;
import com.careeros.offer.repository.OfferShelfRepository;
import com.careeros.report.repository.DashboardRepository;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The assistant's one proactive first step (Epic 331).
 *
 * <p>The dashboard has always shown the numbers; this service composes the handful of
 * facts the editor needs into one payload — every one of them read by the backend
 * itself from the caller's own rows, nothing the browser could inflate: how many
 * applications the caller tracks, how many items genuinely need the user today
 * (the same predicate the dashboard count uses), and how that count splits into
 * "someone is waiting for a reply to my reminder" vs "no movement for a fortnight".
 * The editor is allowed this context and nothing else — no names, no jobs, no
 * narrative; digits it can cite, and silence on any failure.
 */
@Service
public class AssistantService {

    /** Matches the dashboard's own attention window; a 14-day silence is a stall. */
    static final int STALE_DAYS = 14;

    private final AiServiceClient aiService;
    private final ApplicationRepository applications;
    private final DashboardRepository dashboards;
    private final OfferShelfRepository offers;
    private final InterviewSessionRepository sessions;

    public AssistantService(AiServiceClient aiService,
                            ApplicationRepository applications,
                            DashboardRepository dashboards,
                            OfferShelfRepository offers,
                            InterviewSessionRepository sessions) {
        this.aiService = aiService;
        this.applications = applications;
        this.dashboards = dashboards;
        this.offers = offers;
        this.sessions = sessions;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> nextStep(UUID userId, NextStepRequest request) {
        long totalApplications = applications.countByUserId(userId);
        long attention = dashboards.needsAttention(userId, STALE_DAYS);
        long[] split = dashboards.attentionBreakdown(userId, STALE_DAYS);
        long reminderDue = split[0];
        long staleCount = split[1];
        long interviewsStartedLast7Days = sessions.countStartedSince(userId,
                java.time.OffsetDateTime.now().minusDays(7));
        long offersPending = offers.shelfOrder(userId).stream()
                .filter(row -> "pending".equals(row.getDecision()))
                .count();
        String locale = normalizeLocale(request == null ? null : request.locale());
        Map<String, Object> payload = new HashMap<>();
        payload.put("totalApplications", totalApplications);
        payload.put("attentionCount", attention);
        payload.put("reminderDue", reminderDue);
        payload.put("staleCount", staleCount);
        payload.put("interviewsStartedLast7Days", interviewsStartedLast7Days);
        payload.put("offersPending", offersPending);
        payload.put("locale", locale);
        Map<String, Object> answered = aiService.proactiveStep(userId, payload, locale);
        Object step = answered == null ? null : answered.get("step");
        Map<String, Object> out = new HashMap<>(payload);
        if (step != null) {
            out.put("step", step);
        }
        return out;
    }

    private static String normalizeLocale(String locale) {
        if (locale != null && locale.strip().toLowerCase().startsWith("zh")) {
            return "zh";
        }
        return "en";
    }
}
