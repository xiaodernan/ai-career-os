package com.careeros.offer.service;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.ai.AiServiceClient;
import com.careeros.offer.dto.OfferShelfDtos.OfferItem;
import com.careeros.offer.dto.OfferShelfDtos.OfferShelfResponse;
import com.careeros.offer.dto.OfferShelfDtos.UpsertOfferRequest;
import com.careeros.offer.entity.OfferRow;
import com.careeros.offer.repository.OfferShelfRepository;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * The offer shelf (Epic 185): the reader's own record of the offers they hold. Every
 * read and write is owner-scoped — an offer is among the most personal rows this
 * platform keeps, and a shelf that leaks one reader's numbers to another is worse
 * than no shelf. The shelf orders by deadline first (the clock that forces a decision)
 * with undated rows last by recency, so the row that expires soonest is the one the
 * reader meets first.
 */
@Service
public class OfferShelfService {

  private final OfferShelfRepository repository;
  private final AiServiceClient aiService;

  public OfferShelfService(OfferShelfRepository repository, AiServiceClient aiService) {
    this.repository = repository;
    this.aiService = aiService;
  }

  @Transactional(readOnly = true)
  public OfferShelfResponse list(UUID userId) {
    List<OfferItem> items =
        repository.shelfOrder(userId).stream()
            .map(OfferShelfService::toItem)
            .toList();
    return new OfferShelfResponse(items, items.size());
  }

  @Transactional
  public OfferItem create(UUID userId, UpsertOfferRequest request) {
    OfferRow row = new OfferRow();
    row.setUserId(userId);
    apply(row, request);
    return toItem(repository.save(row));
  }

  @Transactional
  public OfferItem update(UUID userId, UUID id, UpsertOfferRequest request) {
    OfferRow row =
        repository
            .findByIdAndUserId(id, userId)
            .orElseThrow(() -> new ApiException(ApiErrorCode.OFFER_NOT_FOUND, "No such offer on this shelf"));
    apply(row, request);
    return toItem(repository.save(row));
  }

  @Transactional(readOnly = true)
  public OfferItem get(UUID userId, UUID id) {
    OfferRow row =
        repository
            .findByIdAndUserId(id, userId)
            .orElseThrow(() -> new ApiException(ApiErrorCode.OFFER_NOT_FOUND, "No such offer on this shelf"));
    return toItem(row);
  }

  /**
   * The decision letter (Epic 327): the writer addresses the reader about the offer they are
   * holding, grounded in the shelf's own numbers. The letter is optional by contract — an
   * ungrounded or unwritten answer is an empty letter, never a fabricated one.
   */
  public String letter(UUID userId, UUID id, String locale) {
    OfferRow row = repository.findByIdAndUserId(id, userId)
        .orElseThrow(() -> new ApiException(ApiErrorCode.OFFER_NOT_FOUND, "No such offer on this shelf"));
    return letterOfRow(userId, row, locale);
  }

  /**
   * The acceptance playbook (Epic 335): the reader's first 90 days, written from the offer they just signed.
   * The playbook is always reader-facing; `playbook` is null when nothing grounded survived.
   */
  public String acceptancePlaybook(UUID userId, UUID id, String locale) {
    OfferRow row = repository.findByIdAndUserId(id, userId)
        .orElseThrow(() -> new ApiException(ApiErrorCode.OFFER_NOT_FOUND, "No such offer on this shelf"));
    Map<String, Object> offer = offerPayload(row);
    Map<String, Object> answer = aiService.acceptancePlaybook(userId, offer, locale);
    Object value = answer == null ? null : answer.get("playbook");
    if (value == null) {
      return null;
    }
    String playbook = value.toString().trim();
    return playbook.isEmpty() ? null : playbook;
  }

  /**
   * The stalled-offer letter (Epic 334): one check-in email the reader sends when the company has
   * gone quiet on the offer — no pressure, no made-up urgency, just the reader's own facts restated.
   */
  public String followUpLetter(UUID userId, UUID id, String locale) {
    OfferRow row = repository.findByIdAndUserId(id, userId)
        .orElseThrow(() -> new ApiException(ApiErrorCode.OFFER_NOT_FOUND, "No such offer on this shelf"));
    Map<String, Object> answer = aiService.followUpLetter(userId, offerPayload(row), locale);
    Object value = answer == null ? null : answer.get("letter");
    if (value == null) {
      return null;
    }
    String letter = value.toString().trim();
    return letter.isEmpty() ? null : letter;
  }

  /**
   * The counter-offer letter (Epic 333): the writer drafts the email the reader actually
   * sends about the offer on the table, grounded in the same owned numbers plus the shelf
   * sibling cards as benchmark context (the model shows them only as band joins, never as
   * ultimatums — the verifier holds the letter to their digits alone).
   */
  public String counterLetter(UUID userId, UUID id, String locale) {
    OfferRow row = repository.findByIdAndUserId(id, userId)
        .orElseThrow(() -> new ApiException(ApiErrorCode.OFFER_NOT_FOUND, "No such offer on this shelf"));
    Map<String, Object> offer = offerPayload(row);
    List<Map<String, Object>> siblings = siblingPayloads(userId, row);
    Map<String, Object> answer = aiService.counterOfferLetter(userId, offer, siblings, locale);
    Object value = answer == null ? null : answer.get("letter");
    if (value == null) {
      return null;
    }
    String letter = value.toString().trim();
    return letter.isEmpty() ? null : letter;
  }

  /**
   * The negotiation prep one-pager (Epic 337): the twelve lines the reader carries into the
   * call where they answer the offer on the table — addressed to the reader (second person),
   * never to the company. Same sibling-band discipline as the letter the reader will send.
   */
  public String negotiationPrep(UUID userId, UUID id, String locale) {
    OfferRow row = repository.findByIdAndUserId(id, userId)
        .orElseThrow(() -> new ApiException(ApiErrorCode.OFFER_NOT_FOUND, "No such offer on this shelf"));
    Map<String, Object> offer = offerPayload(row);
    List<Map<String, Object>> siblings = siblingPayloads(userId, row);
    Map<String, Object> answer = aiService.negotiationPrep(userId, offer, siblings, locale);
    Object value = answer == null ? null : answer.get("prep");
    if (value == null) {
      return null;
    }
    String prep = value.toString().trim();
    return prep.isEmpty() ? null : prep;
  }

  /**
   * The gracious decline (Epic 339): the one short email the reader sends when the answer
   * is no �� gratitude, a clean final no, a door left open. The writer never sees siblings
   * (a decline is not a negotiation tactic); digits must already exist in the row's own
   * payload or the whole letter is dropped.
   */
  public String declineLetter(UUID userId, UUID id, String locale) {
    OfferRow row = repository.findByIdAndUserId(id, userId)
        .orElseThrow(() -> new ApiException(ApiErrorCode.OFFER_NOT_FOUND, "No such offer on this shelf"));
    Map<String, Object> answer = aiService.declineLetter(userId, offerPayload(row), locale);
    Object value = answer == null ? null : answer.get("letter");
    if (value == null) {
      return null;
    }
    String letter = value.toString().trim();
    return letter.isEmpty() ? null : letter;
  }

  private String letterOfRow(UUID userId, OfferRow row, String locale) {
    Map<String, Object> answer = aiService.offerDecisionLetter(userId, offerPayload(row),
            siblingPayloads(userId, row), locale);
    Object value = answer == null ? null : answer.get("letter");
    if (value == null) {
      return null;
    }
    String letter = value.toString().trim();
    return letter.isEmpty() ? null : letter;
  }

  private static Map<String, Object> offerPayload(OfferRow row) {
    Map<String, Object> offer = new HashMap<>();
    offer.put("label", row.getLabel());
    offer.put("base", row.getBase());
    offer.put("bonus", row.getBonus());
    offer.put("annualEquity", row.getEquity());
    offer.put("totalComp", row.totalComp());
    offer.put("currency", row.getCurrency());
    offer.put("remoteType", row.getRemoteType());
    offer.put("deadline", row.getDeadline() == null ? null : row.getDeadline().toString());
    offer.put("decision", row.getDecision());
    offer.put("notes", row.getNotes());
    return offer;
  }

  private List<Map<String, Object>> siblingPayloads(UUID userId, OfferRow self) {
    List<Map<String, Object>> siblings = new ArrayList<>();
    for (OfferRow sib : repository.shelfOrder(userId)) {
      if (siblings.size() >= 4 || sib.getId().equals(self.getId())) {
        continue;
      }
      Map<String, Object> s = new HashMap<>();
      s.put("label", sib.getLabel());
      s.put("totalComp", sib.totalComp());
      s.put("currency", sib.getCurrency());
      siblings.add(s);
    }
    return siblings;
  }

  @Transactional
  public UUID delete(UUID userId, UUID id) {
    OfferRow row =
        repository
            .findByIdAndUserId(id, userId)
            .orElseThrow(() -> new ApiException(ApiErrorCode.OFFER_NOT_FOUND, "No such offer on this shelf"));
    repository.delete(row);
    return id;
  }

  private static void apply(OfferRow row, UpsertOfferRequest request) {
    row.setLabel(request.label().trim());
    row.setBase(request.base());
    row.setBonus(request.bonus());
    row.setEquity(request.equity());
    row.setCurrency(
        request.currency() == null || request.currency().isBlank()
            ? "USD"
            : request.currency().toUpperCase());
    row.setRemoteType(request.remoteType() == null ? "onsite" : request.remoteType());
    row.setDeadline(request.deadline());
    row.setNotes(request.notes());
    if (request.decision() != null) {
      row.setDecision(request.decision().trim().toLowerCase());
    }
  }

  public static OfferItem toItem(OfferRow row) {
    return new OfferItem(
        row.getId(),
        row.getLabel(),
        row.getBase(),
        row.getBonus(),
        row.getEquity(),
        row.getCurrency(),
        row.getRemoteType(),
        row.getDeadline(),
        row.getNotes(),
        row.totalComp(),
        row.getCreatedAt(),
        row.getUpdatedAt(),
        row.getDecision());
  }
}
