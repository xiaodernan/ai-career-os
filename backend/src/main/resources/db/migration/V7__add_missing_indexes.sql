-- Indexes for the hot read paths the initial schema shipped without. Every one
-- below backs a repository query the app actually runs; the (user_id) indexes
-- V1 created sit idle for these because those queries filter by a different
-- leading column (version, session, document), so Postgres could not use them.
CREATE INDEX idx_turns_session ON interview_turns(session_id, seq);
CREATE INDEX idx_exp_version ON experiences(resume_version_id, ordinal);
CREATE INDEX idx_proj_version ON projects(resume_version_id, ordinal);
CREATE INDEX idx_edu_version ON educations(resume_version_id, ordinal);
CREATE INDEX idx_ach_version ON achievements(resume_version_id, ordinal);
CREATE INDEX idx_chunks_document ON document_chunks(document_id, ordinal);
CREATE INDEX idx_docs_source ON documents(source_id);
CREATE INDEX idx_app_events_user ON application_events(user_id, created_at DESC);
CREATE INDEX idx_refresh_family ON refresh_tokens(family_id);
