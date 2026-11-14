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
}
