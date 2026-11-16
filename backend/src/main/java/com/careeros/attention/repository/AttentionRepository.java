package com.careeros.attention.repository;

import com.careeros.attention.entity.AttentionEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface AttentionRepository extends JpaRepository<AttentionEvent, UUID> {

    /** Delete-synthetic for the simulator's wipe; touches only rows the simulator writes. */
    long deleteByJourney(String journey);
}
