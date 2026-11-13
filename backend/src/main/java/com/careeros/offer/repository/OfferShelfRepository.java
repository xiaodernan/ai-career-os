package com.careeros.offer.repository;

import com.careeros.offer.entity.OfferRow;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

/** The offer shelf's reads (Epic 185). Every method is owner-scoped by userId. */
public interface OfferShelfRepository extends JpaRepository<OfferRow, UUID> {

  /**
   * The shelf's order: the row that expires soonest meets the reader first, undated
   * rows trail by recency. Hibernate 6 spells the null placement in the HQL itself.
   */
  @Query("SELECT o FROM OfferRow o WHERE o.userId = :userId "
         + "ORDER BY o.deadline ASC NULLS LAST, o.createdAt DESC")
  List<OfferRow> shelfOrder(@Param("userId") UUID userId);

  Optional<OfferRow> findByIdAndUserId(UUID id, UUID userId);
}
