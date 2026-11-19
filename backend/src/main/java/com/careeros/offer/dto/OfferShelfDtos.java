package com.careeros.offer.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

/** The offer shelf's wire shapes (Epic 185). */
public final class OfferShelfDtos {

  private OfferShelfDtos() {}

  /** One shelf row as the reader sees it: the numbers plus the total they compare by. */
  public record OfferItem(
      UUID id,
      String label,
      int base,
      int bonus,
      int equity,
      String currency,
      String remoteType,
      OffsetDateTime deadline,
      String notes,
      int totalComp,
      OffsetDateTime createdAt,
      OffsetDateTime updatedAt,
      String decision) {}

  public record OfferShelfResponse(List<OfferItem> items, int total) {}

  public record UpsertOfferRequest(
      @NotBlank @Size(min = 1, max = 120) String label,
      @NotNull @Positive int base,
      @Min(0) int bonus,
      @Min(0) int equity,
      @Size(min = 3, max = 3) String currency,
      @Pattern(regexp = "onsite|hybrid|remote", message = "must be onsite, hybrid or remote")
          String remoteType,
      OffsetDateTime deadline,
      @Size(max = 2000) String notes,
      @Pattern(regexp = "pending|accepted|declined", message = "must be pending, accepted or declined")
          String decision) {}

  public record UpsertOfferResponse(OfferItem item) {}

  public record DeleteOfferResponse(UUID id) {}

  /** The decision letter's request (Epic 327). The backend builds the offer payload itself from the row. */
  public record OfferLetterRequest(@Size(max = 8) String locale) {}

  /** The decision letter (Epic 327). `letter` is null when the letter could not be written grounded — the honest answer, not a coat of plausibility. */
  public record OfferLetterResponse(String letter) {}

  /** The sendable counter-offer letter's request (Epic 333). */
  public record CounterLetterRequest(@Size(max = 8) String locale) {}

  /** The sendable counter-offer letter (Epic 333). `letter` is null when nothing grounded survived. */
  public record CounterLetterResponse(String letter) {}

  /** The stalled-offer letter's request (Epic 334). */
  public record FollowUpLetterRequest(@Size(max = 8) String locale) {}

  /** The stalled-offer letter (Epic 334). `letter` is null when nothing grounded survived. */
  public record FollowUpLetterResponse(String letter) {}

  /** The acceptance playbook's request (Epic 335). */
  public record AcceptancePlaybookRequest(@Size(max = 8) String locale) {}

  /** The reader's first-90-days playbook (Epic 335). `playbook` is null when nothing grounded survived. */
  public record AcceptancePlaybookResponse(String playbook) {}

  /** The negotiation prep one-pager's request (Epic 337). */
  public record NegotiationPrepRequest(@Size(max = 8) String locale) {}

  /** The reader's twelve-line prep sheet (Epic 337). `prep` is null when nothing grounded survived. */
  public record NegotiationPrepResponse(String prep) {}
}
