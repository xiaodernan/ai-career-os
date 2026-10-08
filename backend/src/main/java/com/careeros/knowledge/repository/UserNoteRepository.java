package com.careeros.knowledge.repository;

import com.careeros.knowledge.entity.UserNote;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface UserNoteRepository extends JpaRepository<UserNote, UUID> {

    Page<UserNote> findByUserIdOrderByUpdatedAtDescIdAsc(UUID userId, Pageable pageable);

    Optional<UserNote> findByIdAndUserId(UUID id, UUID userId);

    List<UserNote> findByUserId(UUID userId);
}
