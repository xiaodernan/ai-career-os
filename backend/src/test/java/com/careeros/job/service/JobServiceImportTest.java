package com.careeros.job.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.careeros.ai.AiServiceClient;
import com.careeros.application.service.ApplicationService;
import com.careeros.common.Json;
import com.careeros.job.dto.JobDtos.ImportJobRequest;
import com.careeros.job.dto.JobDtos.JobListItem;
import com.careeros.job.entity.Company;
import com.careeros.job.entity.Job;
import com.careeros.job.entity.JobJd;
import com.careeros.job.repository.CompanyRepository;
import com.careeros.job.repository.JobJdRepository;
import com.careeros.job.repository.JobMatchRepository;
import com.careeros.job.repository.JobRepository;
import com.careeros.job.repository.JobSearchRepository;
import com.careeros.job.repository.SavedJobRepository;
import com.careeros.resume.service.ResumeService;
import com.careeros.search.service.QueryEmbeddingService;
import com.careeros.support.TestTransactions;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

/**
 * The paste-a-posting importer is the one job-creation path that trusts an LLM: the analyst's
 * parsed map decides the title, the company name and the skill list, so the tests pin what the
 * code does around it -- the fallbacks when the map is thin, the company upsert's two branches,
 * and the required/preferred skill merge with its blank filtering.
 *
 * <p>Plain Mockito -- no DB, no Spring context -- mirroring JobServiceSavedTest: the write path
 * is asserted through the saved entities, not through a second read.
 */
class JobServiceImportTest {

    private final UUID userId = UUID.randomUUID();

    private JobRepository jobs;
    private CompanyRepository companies;
    private JobJdRepository jds;
    private AiServiceClient ai;
    private JobService service;

    @BeforeEach
    void setUp() {
        jobs = mock(JobRepository.class);
        companies = mock(CompanyRepository.class);
        jds = mock(JobJdRepository.class);
        ai = mock(AiServiceClient.class);
        service = new JobService(jobs, companies, jds, mock(SavedJobRepository.class),
                mock(JobMatchRepository.class), mock(JobSearchRepository.class),
                mock(ResumeService.class), mock(ApplicationService.class), ai,
                mock(QueryEmbeddingService.class), TestTransactions.executing());
        // The write path reads the ids back off the saved rows, so the mocks have to act like
        // the database and hand one out on save.
        when(jobs.save(any())).thenAnswer(inv -> {
            Job j = inv.getArgument(0);
            if (ReflectionTestUtils.getField(j, "id") == null) {
                ReflectionTestUtils.setField(j, "id", UUID.randomUUID());
            }
            return j;
        });
        when(companies.save(any())).thenAnswer(inv -> {
            Company c = inv.getArgument(0);
            if (ReflectionTestUtils.getField(c, "id") == null) {
                ReflectionTestUtils.setField(c, "id", UUID.randomUUID());
            }
            return c;
        });
    }

    private static Map<String, Object> skill(String name) {
        return Map.of("name", name);
    }

    private static Map<String, Object> parsed(Object... kv) {
        Map<String, Object> m = new HashMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            m.put((String) kv[i], kv[i + 1]);
        }
        return m;
    }

    private JobListItem runImport(Map<String, Object> analystResult) {
        when(ai.analyzeJd(any(), any())).thenReturn(analystResult);
        ImportJobRequest request = new ImportJobRequest("Senior Backend Engineer posting text", null);
        return service.importJob(userId, request);
    }

    @Test
    void createsTheCompanyWhenTheAnalystNamesAnUnknownOne() {
        UUID companyId = UUID.randomUUID();
        Company existing = new Company();
        existing.setName("Acme");
        ReflectionTestUtils.setField(existing, "id", companyId);
        when(companies.findByName("Acme")).thenReturn(Optional.of(existing));

        JobListItem item = runImport(Map.of(
                "parsed", Map.of(
                        "title", "Senior Backend Engineer",
                        "company", "Acme",
                        "location", "Remote",
                        "requiredSkills", List.of(skill("Java"), skill("Kafka")))));

        // The known name resolves, so no company row is written by the import.
        verify(companies, never()).save(any());
        assertThat(item.companyId()).isEqualTo(companyId);
        assertThat(item.companyName()).isEqualTo("Acme");
        assertThat(item.title()).isEqualTo("Senior Backend Engineer");
        assertThat(item.location()).isEqualTo("Remote");
    }

    @Test
    void anUnknownCompanyNameIsFiledAsANewPasteSourcedCompany() {
        when(companies.findByName("Globex")).thenReturn(Optional.empty());

        JobListItem item = runImport(Map.of(
                "parsed", Map.of(
                        "title", "Data Engineer",
                        "company", "Globex")));

        ArgumentCaptor<Company> company = ArgumentCaptor.forClass(Company.class);
        verify(companies, times(1)).save(company.capture());
        assertThat(company.getValue().getName()).isEqualTo("Globex");
        assertThat(company.getValue().getSources()).isEqualTo(List.of(Map.of("type", "user_paste")));
        assertThat(item.companyId()).isEqualTo(company.getValue().getId());
    }

    @Test
    void requiredAndPreferredSkillsMergeIntoOneDistinctNonBlankList() {
        when(companies.findByName("Acme")).thenReturn(Optional.empty());

        JobListItem item = runImport(Map.of(
                "parsed", Map.of(
                        "title", "Backend Engineer",
                        "company", "Acme",
                        "requiredSkills", List.of(skill("Java"), skill(""), skill("Kafka")),
                        "preferredSkills", List.of(skill("Java"), skill("Redis")))));

        // The analyst can repeat a skill across the two lists or emit an empty name; the row
        // carries each skill once, and a blank name is not a skill at all.
        assertThat(item.skills()).containsExactly("Java", "Kafka", "Redis");
    }

    @Test
    void theRawPostingIsKeptAsTheDescriptionAndOnItsOwnJdRow() {
        when(companies.findByName("Unknown company")).thenReturn(Optional.empty());

        JobListItem item = runImport(Map.of(
                "parsed", Map.of(
                        "title", "Backend Engineer",
                        "company", "Unknown company",
                        "responsibilities", List.of("Ship APIs", "Mentor engineers"),
                        "experienceYears", 5)));

        ArgumentCaptor<Job> job = ArgumentCaptor.forClass(Job.class);
        verify(jobs, times(1)).save(job.capture());
        assertThat(job.getValue().getDescription()).isEqualTo("Senior Backend Engineer posting text");
        assertThat(job.getValue().getSource()).isEqualTo("user_paste");
        assertThat(job.getValue().getResponsibilities()).containsExactly("Ship APIs", "Mentor engineers");
        assertThat(job.getValue().getExperienceYears()).isEqualTo(5);

        ArgumentCaptor<JobJd> jd = ArgumentCaptor.forClass(JobJd.class);
        verify(jds, times(1)).save(jd.capture());
        assertThat(jd.getValue().getUserId()).isEqualTo(userId);
        assertThat(jd.getValue().getRawText()).isEqualTo("Senior Backend Engineer posting text");

        assertThat(item.source()).isEqualTo("user_paste");
    }

    @Test
    void aThinAnalystAnswerStillLandsARowWithFallbackNamesAndEmptyLists() {
        when(companies.findByName("Unknown company")).thenReturn(Optional.empty());

        // The analyst answered nothing parseable (the mock provider's floor): the import must
        // still produce a trackable job, with the placeholder company and no invented skills.
        JobListItem item = runImport(Map.of());

        assertThat(item.title()).isEqualTo("Imported job");
        assertThat(item.companyName()).isEqualTo("Unknown company");
        assertThat(item.skills()).isEmpty();

        ArgumentCaptor<Job> job = ArgumentCaptor.forClass(Job.class);
        verify(jobs, times(1)).save(job.capture());
        assertThat(job.getValue().getRequirements()).isEmpty();
        assertThat(job.getValue().getNiceToHave()).isEmpty();
        assertThat(job.getValue().getResponsibilities()).isEmpty();
        assertThat(job.getValue().getSkills()).isEmpty();

        // The JD row is the reason the paste survives at all: the raw text is on it even when
        // the parse came back empty, so a re-analysis never needs the user to paste again.
        ArgumentCaptor<JobJd> jd = ArgumentCaptor.forClass(JobJd.class);
        verify(jds, times(1)).save(jd.capture());
        assertThat(jd.getValue().getParsed()).isEqualTo(Json.obj(null));
    }
}