package com.careeros.resume.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.careeros.ApiIntegrationTest;
import com.careeros.auth.repository.UserRepository;
import com.careeros.resume.dto.ResumeDtos.CreateResumeRequest;
import com.careeros.resume.dto.ResumeDtos.ResumeListItem;
import com.careeros.resume.entity.Experience;
import com.careeros.resume.entity.Project;
import com.careeros.resume.entity.ResumeVersion;
import com.careeros.resume.repository.AchievementRepository;
import com.careeros.resume.repository.EducationRepository;
import com.careeros.resume.repository.ExperienceRepository;
import com.careeros.resume.repository.ProjectRepository;
import com.careeros.resume.repository.ResumeRepository;
import com.careeros.resume.repository.ResumeSkillRepository;
import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import javax.sql.DataSource;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * Re-parsing a resume replaces what the previous parse derived: {@code populateChildren} deletes
 * the version's five child sets and re-inserts them from the new answer, and the version's own
 * structured body is rewritten before any of that. Those writes are the parse's output as a unit.
 * {@code ResumeService.parse} opened no transaction and reached its {@code @Transactional} writer
 * through a call on itself -- the one route Spring's proxy does not intercept -- so each write
 * committed alone. Two consequences, both measured here before the fix:
 *
 * <p>First, {@code POST /api/v1/resumes/{id}/parse} cannot re-parse a resume that already has
 * children at all. A derived {@code deleteByResumeVersionId} loads the rows and calls
 * {@code EntityManager#remove}, which refuses to run without a transaction in progress, so the
 * second parse dies at its first delete -- after the version row it already committed -- and the
 * reader sees their own resume rewritten around a body that never arrived.
 *
 * <p>Second, when a child insert is refused for any reason, the deletes that came before it stay
 * committed: the reader is left with a resume whose experience, projects, education, achievements
 * and skill links are simply gone.
 *
 * <p>The refusal in the last two cases is the database's own but not one of this chain's shipped
 * constraints: no {@code NOT NULL}, foreign key or unique key in {@code populateChildren} can be
 * provoked from parse output alone (every required column is filled from {@code Json.strOr} or a
 * generated id), so the case installs a row-level trigger that refuses a sentinel value and treats
 * it as whatever else might refuse that INSERT at that moment. {@code JobImportAtomicityIT} is the
 * sibling that needs no stand-in, because {@code jobs.description} really is {@code NOT NULL}. The
 * trigger matches only values carrying this run's random id, is dropped after every case, and the
 * IT schema is rebuilt from {@code V1} at the start of each suite run.
 */
class ResumeParseAtomicityIT extends ApiIntegrationTest {

    @Autowired
    private ResumeService resumes;
    @Autowired
    private ResumeRepository resumeRows;
    @Autowired
    private ExperienceRepository experienceRows;
    @Autowired
    private ProjectRepository projectRows;
    @Autowired
    private EducationRepository educationRows;
    @Autowired
    private AchievementRepository achievementRows;
    @Autowired
    private ResumeSkillRepository skillLinks;
    @Autowired
    private UserRepository users;
    @Autowired
    private DataSource dataSource;

    private final UUID runId = UUID.randomUUID();
    private final String firstCompany = "First Parse " + runId;

    private UUID userId;
    private UUID resumeId;
    private UUID versionId;

    @BeforeEach
    void parseAPlainResume() throws Exception {
        String email = "parse-atomic-" + runId + "@example.test";
        register(email);
        userId = users.findByEmail(email).orElseThrow().getId();
        ResumeListItem item = resumes.create(userId, new CreateResumeRequest("Atomicity probe",
                "Senior Backend Engineer with five years building distributed services."));
        resumeId = item.id();
        versionId = item.currentVersionId();

        ai.resumeExperienceCompany = firstCompany;
        resumes.parse(userId, resumeId);
        assertThat(experiences())
                .as("the setup parse has to file a child set for a re-parse to have anything to replace")
                .hasSize(1);
    }

    @AfterEach
    void dropRefusal() throws SQLException {
        execute("DROP TRIGGER IF EXISTS it_refuse_row ON experiences");
        execute("DROP TRIGGER IF EXISTS it_refuse_row ON projects");
        execute("DROP FUNCTION IF EXISTS it_refuse_row()");
    }

    private List<Experience> experiences() {
        return experienceRows.findByResumeVersionIdOrderByOrdinalAsc(versionId);
    }

    private int projectCount() {
        return projectRows.findByResumeVersionIdOrderByOrdinalAsc(versionId).size();
    }

    private String structuredCompany() {
        ResumeVersion version = currentVersion();
        List<Object> experience = (List<Object>) version.getStructured().get("experience");
        return String.valueOf(((Map<String, Object>) experience.get(0)).get("company"));
    }

    @SuppressWarnings("unchecked")
    private ResumeVersion currentVersion() {
        return resumeRows.findById(resumeId)
                .flatMap(r -> resumes.currentVersion(r))
                .orElseThrow();
    }

    private void execute(String sql) throws SQLException {
        try (Connection c = dataSource.getConnection(); Statement st = c.createStatement()) {
            st.execute(sql);
        }
    }

    /**
     * The database refuses any child row carrying {@code value}, whichever table it lands in --
     * so the case decides whether the batch dies at its first insert or at a later one.
     */
    private void refuse(String value) throws SQLException {
        execute("CREATE OR REPLACE FUNCTION it_refuse_row() RETURNS trigger LANGUAGE plpgsql AS $$ "
                + "DECLARE body jsonb; "
                + "BEGIN "
                + "body := to_jsonb(NEW); "
                + "IF body->>'company' = '" + value + "' OR body->>'name' = '" + value + "' THEN "
                + "RAISE EXCEPTION 'the resume parse atomicity case refuses this row' "
                + "USING ERRCODE = '23505'; "
                + "END IF; "
                + "RETURN NEW; "
                + "END $$");
        execute("CREATE TRIGGER it_refuse_row BEFORE INSERT ON experiences "
                + "FOR EACH ROW EXECUTE FUNCTION it_refuse_row()");
        execute("CREATE TRIGGER it_refuse_row BEFORE INSERT ON projects "
                + "FOR EACH ROW EXECUTE FUNCTION it_refuse_row()");
    }

    private void assertFirstParseStillFiled() {
        assertThat(experiences())
                .as("the re-parse deleted the reader's experience rows and never replaced them")
                .extracting(Experience::getCompany).containsExactly(firstCompany);
        assertThat(projectCount())
                .as("projects were deleted by the parse that could not finish")
                .isEqualTo(1);
        assertThat(educationRows.findByResumeVersionIdOrderByOrdinalAsc(versionId))
                .as("education was deleted by the parse that could not finish")
                .hasSize(1);
        assertThat(achievementRows.findByResumeVersionIdOrderByOrdinalAsc(versionId))
                .as("achievements were deleted by the parse that could not finish")
                .hasSize(1);
        assertThat(skillLinks.findByResumeVersionId(versionId))
                .as("skill links were deleted by the parse that could not finish")
                .hasSize(2);
    }

    @Test
    @DisplayName("a resume that already has children can be re-parsed")
    void aReParseReplacesTheChildrenItDerived() {
        String secondCompany = "Second Parse " + runId;
        ai.resumeExperienceCompany = secondCompany;

        resumes.parse(userId, resumeId);

        assertThat(experiences())
                .as("the second parse left the first parse's row where it was")
                .extracting(Experience::getCompany).containsExactly(secondCompany);
        assertThat(projectCount()).isEqualTo(1);
        assertThat(skillLinks.findByResumeVersionId(versionId)).hasSize(2);
        assertThat(structuredCompany()).isEqualTo(secondCompany);
    }

    @Test
    @DisplayName("a refused first child row leaves the previous parse filed and writes nothing")
    void aRefusedChildRowKeepsThePreviouslyParsedResume() throws Exception {
        String refused = "Refused Parse " + runId;
        refuse(refused);
        ai.resumeExperienceCompany = refused;

        assertThatThrownBy(() -> resumes.parse(userId, resumeId)).isInstanceOf(RuntimeException.class);

        assertFirstParseStillFiled();
        assertThat(structuredCompany())
                .as("the version's structured body already carries the text of a parse that failed")
                .isEqualTo(firstCompany);
    }

    @Test
    @DisplayName("a refused later row rolls back the child rows that already succeeded")
    void aRefusedLaterRowRollsBackTheBatchAheadOfIt() throws Exception {
        String refusedProject = "Refused Project " + runId;
        refuse(refusedProject);
        ai.resumeExperienceCompany = "Rebuilt Experience " + runId;
        ai.resumeProjectName = refusedProject;

        assertThatThrownBy(() -> resumes.parse(userId, resumeId)).isInstanceOf(RuntimeException.class);

        assertFirstParseStillFiled();
        assertThat(projectRows.findByResumeVersionIdOrderByOrdinalAsc(versionId))
                .as("the refused project row landed beside, or instead of, the one already filed")
                .extracting(Project::getName).containsExactly("OpenLedger");
    }
}
