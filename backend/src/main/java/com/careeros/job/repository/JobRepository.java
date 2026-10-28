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

    /**
     * One page of the board in one status -- the scheduled sweep's corpus comparison.
     *
     * <p>`posted_at` is not unique (a board that posts a batch in one minute writes ties), so
     * the ordering ends in the id: without it two pages of the same corpus can hand the same
     * posting twice and miss another, and the sweep would plan against a corpus that was
     * never quite the one the board holds.
     */
    Page<Job> findByStatusOrderByPostedAtDescIdDesc(String status, Pageable pageable);
}
