package com.careeros.offer.service;

import com.careeros.common.ApiErrorCode;
import com.careeros.common.ApiException;
import com.careeros.offer.dto.OfferShelfDtos.OfferItem;
import com.careeros.offer.dto.OfferShelfDtos.OfferShelfResponse;
import com.careeros.offer.dto.OfferShelfDtos.UpsertOfferRequest;
import com.careeros.offer.entity.OfferRow;
import com.careeros.offer.repository.OfferShelfRepository;
import java.util.List;
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

  public OfferShelfService(OfferShelfRepository repository) {
    this.repository = repository;
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
