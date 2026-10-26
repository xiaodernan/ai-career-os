package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.ApiIntegrationTest;
import com.careeros.auth.repository.UserRepository;
import com.careeros.job.dto.JobDtos.ImportJobRequest;
import com.careeros.job.dto.JobDtos.JobListItem;
import com.careeros.job.entity.Job;
import com.careeros.job.entity.JobJd;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobJdRepository;
import com.careeros.job.repository.JobRepository;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * The paste-a-posting importer writes three rows -- a company when the analyst names one the
 * catalog does not know, the job, and the posting's own JD row -- and it must keep none of them
 * when one of the three is refused.
 *
 * <p>{@code JobService.importJob} opens no transaction and reaches its writer through a call on
 * itself, which is the one route Spring's proxy does not intercept: {@code persistImport}'s
 * {@code @Transactional} was decoration, and the three writes each committed in their own
 * transaction. These cases fail the write at the second row and at the third and ask what the
 * database kept, so the boundary is proved by what survives rather than by an annotation being
 * present. The last case is the control: a real import still files all three rows, so a "fix"
 * that quietly stopped writing would not pass either.
 *
 * <p>The refusals are the database's own, not a stub's: {@code jobs.description} is
 * {@code NOT NULL}, so an empty paste fails at the job row, and {@code job_jds.user_id} carries
 * a foreign key to {@code users(id)}, so a user id with no row behind it fails only the JD row.
 * Each case names its own company, so "the import created a company" is never confused with a
 * row an earlier class filed.
 */
class JobImportAtomicityIT extends ApiIntegrationTest {

    @Autowired
    private JobService jobs;
    @Autowired
    private JobRepository jobRows;
    @Autowired
    private CompanyRepository companyRows;
    @Autowired
    private JobJdRepository jdRows;
    @Autowired
    private UserRepository users;

    /** An id no {@code users} row owns, so only the JD write's foreign key can fail. */
    private final UUID nobody = UUID.randomUUID();

    private String companyUnderTest(String tag) {
        String name = "Import " + tag + " " + nobody;
        ai.jdCompany = name;
        return name;
    }

    @Test
    @DisplayName("a refused job row leaves no company behind")
    void aRefusedJobRowLeavesNoCompanyBehind() {
        String company = companyUnderTest("second");
        long jobsBefore = jobRows.count();

        // description comes from the pasted text and is NOT NULL: the second write is refused.
        assertThatThrownBy(() -> jobs.importJob(nobody, new ImportJobRequest(null, null)))
                .isInstanceOf(RuntimeException.class);

        assertThat(jobRows.count()).isEqualTo(jobsBefore);
        assertThat(companyRows.findByName(company))
                .as("the catalog kept a company the import never finished")
                .isEmpty();
    }

    @Test
    @DisplayName("a refused JD row leaves no job and no company behind")
    void aRefusedJdRowLeavesNothingBehind() {
        String company = companyUnderTest("third");
        long jobsBefore = jobRows.count();

        assertThatThrownBy(() -> jobs.importJob(nobody,
                new ImportJobRequest("We are hiring a staff payment engineer in Zurich.", null)))
                .isInstanceOf(RuntimeException.class);

        assertThat(jobRows.count())
                .as("the tracker kept a posting whose text was refused")
                .isEqualTo(jobsBefore);
        assertThat(companyRows.findByName(company)).isEmpty();
        assertThat(jdRows.findAll().stream().filter(row -> nobody.equals(row.getUserId())).toList())
                .as("the user id this import was refused for owns a JD row anyway")
                .isEmpty();
    }

    @Test
    @DisplayName("a real import still files all three rows")
    void aSuccessfulImportFilesEveryRow() throws Exception {
        String email = "import-atomic-" + nobody + "@example.test";
        String company = companyUnderTest("ok");
        register(email);
        UUID someone = users.findByEmail(email).orElseThrow().getId();
        long jobsBefore = jobRows.count();

        JobListItem item = jobs.importJob(someone, new ImportJobRequest("Build our ledger API.", null));

        assertThat(item.title()).isEqualTo("Senior Backend Engineer");
        assertThat(item.companyName()).isEqualTo(company);
        assertThat(jobRows.count()).isEqualTo(jobsBefore + 1);
        Job stored = jobRows.findById(item.id()).orElseThrow();
        assertThat(stored.getSource()).isEqualTo("user_paste");
        List<JobJd> rows = jdRows.findByJobIdAndUserId(stored.getId(), someone);
        assertThat(rows).hasSize(1);
        assertThat(rows.get(0).getRawText()).isEqualTo("Build our ledger API.");
    }
}
