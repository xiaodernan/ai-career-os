package com.careeros.job.repository;

import com.careeros.job.entity.Job;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface JobRepository extends JpaRepository<Job, UUID> {

    List<Job> findByCompanyId(UUID companyId);

    void deleteByCompanyId(UUID companyId);
}
