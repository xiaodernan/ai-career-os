package com.careeros.job.repository;

import com.careeros.job.entity.Job;
import java.util.List;
import java.util.UUID;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface JobRepository extends JpaRepository<Job, UUID> {

    List<Job> findByCompanyId(UUID companyId);

    void deleteByCompanyId(UUID companyId);

    /** One page of the board in one status -- the scheduled sweep's corpus comparison. */
    Page<Job> findByStatus(String status, Pageable pageable);
}
