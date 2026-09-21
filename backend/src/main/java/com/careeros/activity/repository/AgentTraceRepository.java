package com.careeros.activity.repository;

import com.careeros.activity.entity.AgentTrace;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AgentTraceRepository extends JpaRepository<AgentTrace, Long> {

    List<AgentTrace> findByRunIdOrderBySeqAsc(UUID runId);
}
