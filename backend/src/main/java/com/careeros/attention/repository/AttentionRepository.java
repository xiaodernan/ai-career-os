package com.careeros.attention.repository;

import com.careeros.attention.entity.AttentionEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.UUID;

@Repository
public interface AttentionRepository extends JpaRepository<AttentionEvent, UUID> {
}
