-- AI Career OS — V1 baseline schema
-- Conventions: uuid pk, user_id on every user-scoped table, timestamptz, snake_case.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

-- IMMUTABLE wrapper for 'simple' FTS config (to_tsvector(regconfig,text) is STABLE,
-- which blocks use in GENERATED ALWAYS columns).
CREATE FUNCTION fts_simple(doc text) RETURNS tsvector
  LANGUAGE sql IMMUTABLE PARALLEL SAFE AS
  $$ SELECT to_tsvector('simple'::regconfig, COALESCE(doc, '')) $$;

-- array_to_string(anyarray, text) is STABLE in PG16; wrap for generated-column use.
CREATE FUNCTION fts_join(arr text[]) RETURNS tsvector
  LANGUAGE sql IMMUTABLE PARALLEL SAFE AS
  $$ SELECT to_tsvector('simple'::regconfig, COALESCE(array_to_string(arr, ' '), '')) $$;

-- ============ identity & user ============
CREATE TABLE users (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email         citext NOT NULL UNIQUE,
  password_hash text   NOT NULL,
  auth_provider text   NOT NULL DEFAULT 'local',      -- oauth-ready
  display_name  text   NOT NULL,
  avatar_url    text,
  role          text   NOT NULL DEFAULT 'user',        -- user | admin
  status        text   NOT NULL DEFAULT 'active',      -- active | disabled
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE refresh_tokens (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  text NOT NULL UNIQUE,
  family_id   uuid NOT NULL,                            -- rotation reuse detection
  expires_at  timestamptz NOT NULL,
  revoked_at  timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_refresh_user ON refresh_tokens(user_id);

CREATE TABLE password_reset_tokens (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash text NOT NULL UNIQUE,
  expires_at timestamptz NOT NULL,
  used_at    timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE user_profiles (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  headline         text,
  summary          text,
  location         text,
  years_experience numeric(4,1),
  target_roles     jsonb NOT NULL DEFAULT '[]',
  target_locations jsonb NOT NULL DEFAULT '[]',
  links            jsonb NOT NULL DEFAULT '{}',
  work_authorization jsonb NOT NULL DEFAULT '{}',
  preferences      jsonb NOT NULL DEFAULT '{}',         -- ui prefs, notify prefs
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE user_memories (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind         text NOT NULL,   -- skill|preference|goal|interview_pattern|learning_progress|fact
  key          text NOT NULL,
  content      text NOT NULL,
  importance   real NOT NULL DEFAULT 0.5,
  source       text NOT NULL DEFAULT 'manual',  -- resume_parse|conversation|interview|manual
  embedding    vector,
  last_used_at timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, kind, key)
);
CREATE INDEX idx_memories_user ON user_memories(user_id);

-- ============ resume intelligence ============
CREATE TABLE resumes (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title            text NOT NULL,
  source_file_key  text,
  status           text NOT NULL DEFAULT 'uploaded',    -- uploaded|parsing|parsed|failed
  parse_error      text,
  current_version_id uuid,
  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_resumes_user ON resumes(user_id);

CREATE TABLE resume_versions (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  resume_id   uuid NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
  user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  label       text NOT NULL DEFAULT 'original',
  kind        text NOT NULL DEFAULT 'original',         -- original | tailored
  job_id      uuid,                                     -- fk added after jobs
  structured  jsonb NOT NULL DEFAULT '{}',              -- canonical ResumeProfile JSON
  plaintext   text,
  score       jsonb,                                    -- resume rubric score {total,detail}
  diff        jsonb,                                    -- tailor before/after
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_rv_resume ON resume_versions(resume_id);
CREATE INDEX idx_rv_user ON resume_versions(user_id);

ALTER TABLE resumes ADD CONSTRAINT fk_resume_current_version
  FOREIGN KEY (current_version_id) REFERENCES resume_versions(id) DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE experiences (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  resume_version_id  uuid NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
  user_id            uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  company            text NOT NULL,
  title              text NOT NULL,
  start_date         text,               -- free-form ("2023-06"), normalized month kept below
  start_month        date,
  end_month          date,
  location           text,
  bullets            text[] NOT NULL DEFAULT '{}',
  summary            text,
  ordinal            int  NOT NULL DEFAULT 0
);
CREATE INDEX idx_exp_user ON experiences(user_id);

CREATE TABLE projects (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  resume_version_id  uuid NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
  user_id            uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name               text NOT NULL,
  role               text,
  period             text,
  bullets            text[] NOT NULL DEFAULT '{}',
  tech               text[] NOT NULL DEFAULT '{}',
  url                text,
  ordinal            int NOT NULL DEFAULT 0
);
CREATE INDEX idx_proj_user ON projects(user_id);

CREATE TABLE educations (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  resume_version_id  uuid NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
  user_id            uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  school             text NOT NULL,
  degree             text,
  field              text,
  start_year         int,
  end_year           int,
  gpa                text,
  courses            text[] NOT NULL DEFAULT '{}',
  ordinal            int NOT NULL DEFAULT 0
);
CREATE INDEX idx_edu_user ON educations(user_id);

CREATE TABLE achievements (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  resume_version_id  uuid NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
  user_id            uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  text               text NOT NULL,
  ordinal            int NOT NULL DEFAULT 0
);

CREATE TABLE skills (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        text NOT NULL,
  name_norm   text NOT NULL,                             -- lowercased/aliased
  category    text,                                      -- language|framework|tool|cloud|data|soft|other
  level       text DEFAULT 'inferred',                   -- self_reported | inferred
  evidence_count int NOT NULL DEFAULT 0,
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, name_norm)
);

CREATE TABLE resume_skills (
  resume_version_id uuid NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
  skill_id          uuid NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  user_id           uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  proficiency       real,                                -- 0..1 inferred
  PRIMARY KEY (resume_version_id, skill_id)
);

-- ============ jobs & companies ============
CREATE TABLE companies (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name               text NOT NULL UNIQUE,
  website            text,
  logo_url           text,
  industry           text,
  size               text,
  overview           text,
  tech_stack         text[] NOT NULL DEFAULT '{}',
  culture            text,
  interview_process  text,
  sources            jsonb NOT NULL DEFAULT '[]',        -- external data MUST carry source
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);

-- resume_versions.job_id FK is added after jobs table exists (see end of file).

CREATE TABLE jobs (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id       uuid NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  title            text NOT NULL,
  location         text,
  remote_type      text NOT NULL DEFAULT 'onsite',       -- onsite|hybrid|remote
  employment_type  text NOT NULL DEFAULT 'full_time',    -- full_time|internship|contract|new_grad
  salary_min       int,
  salary_max       int,
  salary_currency  text NOT NULL DEFAULT 'CNY',
  experience_years int,
  description      text NOT NULL,
  requirements     text[] NOT NULL DEFAULT '{}',
  nice_to_have     text[] NOT NULL DEFAULT '{}',
  responsibilities text[] NOT NULL DEFAULT '{}',
  skills           text[] NOT NULL DEFAULT '{}',
  status           text NOT NULL DEFAULT 'open',
  source           text NOT NULL DEFAULT 'seed',         -- seed|user_paste|agent_research
  external_url     text,
  posted_at        timestamptz NOT NULL DEFAULT now(),
  embedding        vector,
  tsv              tsvector GENERATED ALWAYS AS (
      setweight(fts_simple(coalesce(title,'')), 'A') ||
      setweight(fts_join(skills), 'B') ||
      setweight(fts_simple(coalesce(description,'')), 'C')
  ) STORED
);
CREATE INDEX idx_jobs_tsv ON jobs USING gin(tsv);
CREATE INDEX idx_jobs_skills_gin ON jobs USING gin(skills);
CREATE INDEX idx_jobs_company ON jobs(company_id);
CREATE INDEX idx_jobs_status_posted ON jobs(status, posted_at DESC);

CREATE TABLE job_jds (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id     uuid REFERENCES jobs(id) ON DELETE SET NULL,
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  raw_text   text NOT NULL,
  parsed     jsonb,                    -- JD Intelligence output
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_jd_user ON job_jds(user_id);

CREATE TABLE saved_jobs (
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  job_id     uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  note       text,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, job_id)
);

CREATE TABLE job_matches (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  job_id            uuid NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  resume_version_id uuid NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,
  overall           real NOT NULL,
  technical         real NOT NULL,
  experience        real NOT NULL,
  projects          real NOT NULL,
  education         real NOT NULL,
  matched_skills    jsonb NOT NULL DEFAULT '[]',
  missing_skills    jsonb NOT NULL DEFAULT '[]',
  evidence          jsonb NOT NULL DEFAULT '[]',         -- [{criterion,score,chunk_ids,quote,reasoning}]
  narrative         text,
  model             text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, job_id, resume_version_id)
);
CREATE INDEX idx_match_user ON job_matches(user_id);

-- ============ applications (kanban) ============
CREATE TABLE applications (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  job_id            uuid REFERENCES jobs(id) ON DELETE SET NULL,
  company_id        uuid REFERENCES companies(id) ON DELETE SET NULL,
  title             text NOT NULL,
  company_name      text,
  status            text NOT NULL DEFAULT 'saved',       -- saved|applied|oa|interview|final_round|offer|rejected
  position          int  NOT NULL DEFAULT 0,             -- order within column
  notes             text,
  reminder_at       timestamptz,
  resume_version_id uuid REFERENCES resume_versions(id) ON DELETE SET NULL,
  jd_id             uuid REFERENCES job_jds(id) ON DELETE SET NULL,
  match_id          uuid REFERENCES job_matches(id) ON DELETE SET NULL,
  applied_at        timestamptz,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_apps_user_status ON applications(user_id, status);

CREATE TABLE application_events (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id  uuid NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind            text NOT NULL,                         -- status|note|reminder|interview_record|attachment
  payload         jsonb NOT NULL DEFAULT '{}',
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_app_events ON application_events(application_id);

-- ============ interviews ============
CREATE TABLE interview_sessions (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  job_id            uuid REFERENCES jobs(id) ON DELETE SET NULL,
  jd_id             uuid REFERENCES job_jds(id) ON DELETE SET NULL,
  resume_version_id uuid REFERENCES resume_versions(id) ON DELETE SET NULL,
  company_name      text,
  position_title    text,
  mode              text NOT NULL DEFAULT 'mixed',       -- behavioral|technical|system_design|ai_llm|rag|agent|backend|mixed
  status            text NOT NULL DEFAULT 'active',      -- active|paused|completed|abandoned
  difficulty        real NOT NULL DEFAULT 0.5,
  config            jsonb NOT NULL DEFAULT '{}',
  started_at        timestamptz NOT NULL DEFAULT now(),
  finished_at       timestamptz
);
CREATE INDEX idx_iv_user ON interview_sessions(user_id);

CREATE TABLE interview_turns (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id     uuid NOT NULL REFERENCES interview_sessions(id) ON DELETE CASCADE,
  user_id        uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  seq            int NOT NULL,
  role           text NOT NULL,                          -- interviewer | candidate
  content        text NOT NULL,
  question_meta  jsonb,                                  -- {topic, expected_points, depth_level}
  evaluation     jsonb,                                  -- per-answer evaluation
  created_at     timestamptz NOT NULL DEFAULT now(),
  UNIQUE (session_id, seq)
);

CREATE TABLE interview_evaluations (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id  uuid NOT NULL UNIQUE REFERENCES interview_sessions(id) ON DELETE CASCADE,
  user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  dims        jsonb NOT NULL DEFAULT '{}',   -- technical_accuracy, communication, depth, structure,
                                             -- problem_solving, system_thinking, ai_knowledge, backend_knowledge
  summary     jsonb NOT NULL DEFAULT '{}',   -- well / weak / missing_concepts / better_answers / study_materials
  trajectory  jsonb NOT NULL DEFAULT '[]',   -- depth path of question chains
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- ============ copilot ============
CREATE TABLE conversations (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title      text NOT NULL DEFAULT 'New chat',
  context    jsonb NOT NULL DEFAULT '{}',    -- pinned {job_id, resume_version_id, ...}
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_conv_user ON conversations(user_id, updated_at DESC);

CREATE TABLE messages (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role            text NOT NULL,                         -- user|assistant|system
  content         text NOT NULL DEFAULT '',
  artifacts       jsonb NOT NULL DEFAULT '[]',           -- typed AI artifacts
  sources         jsonb NOT NULL DEFAULT '[]',           -- citations
  actions         jsonb NOT NULL DEFAULT '[]',           -- suggested actions
  agent_run_id    uuid,
  created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_msg_conv ON messages(conversation_id, created_at);

-- ============ knowledge base ============
CREATE TABLE knowledge_sources (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind       text NOT NULL,                              -- resume|project|note|jd|company|interview_feedback|certificate|course|goal
  ref_id     uuid,                                       -- domain row id when applicable
  title      text NOT NULL,
  status     text NOT NULL DEFAULT 'pending',            -- pending|ingesting|ready|failed
  error      text,
  document_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_ks_user ON knowledge_sources(user_id);

CREATE TABLE user_notes (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title      text NOT NULL DEFAULT '',
  content    text NOT NULL,
  tags       text[] NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_notes_user ON user_notes(user_id);

CREATE TABLE documents (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  source_id    uuid REFERENCES knowledge_sources(id) ON DELETE SET NULL,
  file_key     text,
  media_type   text NOT NULL,
  title        text,
  content_hash text NOT NULL,
  lang         text DEFAULT 'en',
  text_excerpt text,
  meta         jsonb NOT NULL DEFAULT '{}',
  status       text NOT NULL DEFAULT 'pending',          -- pending|indexing|ready|failed
  error        text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_docs_user ON documents(user_id);
ALTER TABLE knowledge_sources ADD CONSTRAINT fk_ks_document
  FOREIGN KEY (document_id) REFERENCES documents(id) DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE document_chunks (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id  uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  ordinal      int NOT NULL,
  text         text NOT NULL,
  token_count  int NOT NULL DEFAULT 0,
  section_path text,                                     -- e.g. resume > experience > 3
  kind         text,                                     -- chunk semantic type
  meta         jsonb NOT NULL DEFAULT '{}',
  embedding    vector,
  tsv          tsvector GENERATED ALWAYS AS (fts_simple(text)) STORED,
  UNIQUE (document_id, ordinal)
);
CREATE INDEX idx_chunks_tsv ON document_chunks USING gin(tsv);
CREATE INDEX idx_chunks_user ON document_chunks(user_id);
-- HNSW index created by the app after vectors exist (empty column guard): see V2 ops migration.

-- ============ agents & observability ============
CREATE TABLE agent_runs (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  root_run_id    uuid REFERENCES agent_runs(id) ON DELETE SET NULL,
  conversation_id uuid REFERENCES conversations(id) ON DELETE SET NULL,
  agent          text NOT NULL,       -- career|resume|job_research|jd_analyst|rag|interview|learning|tracker
  trigger        text NOT NULL,       -- chat|resume_parse|match|tailor|cover_letter|interview|...
  status         text NOT NULL DEFAULT 'running',         -- running|completed|failed|cancelled
  model          text,
  input_tokens   int NOT NULL DEFAULT 0,
  output_tokens  int NOT NULL DEFAULT 0,
  cached_tokens  int NOT NULL DEFAULT 0,
  cost_usd       numeric(12,6) NOT NULL DEFAULT 0,
  latency_ms     int NOT NULL DEFAULT 0,
  error          text,
  started_at     timestamptz NOT NULL DEFAULT now(),
  finished_at    timestamptz
);
CREATE INDEX idx_runs_user_started ON agent_runs(user_id, started_at DESC);

CREATE TABLE agent_traces (
  id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id     uuid NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  seq        int NOT NULL,
  kind       text NOT NULL,   -- step_start|tool_call|tool_result|llm_call|retrieval|rerank|handoff|message|final|error
  agent      text NOT NULL,
  payload    jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_traces_run ON agent_traces(run_id, seq);

CREATE TABLE ai_usage_events (
  id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  run_id        uuid REFERENCES agent_runs(id) ON DELETE SET NULL,
  model         text NOT NULL,
  provider      text NOT NULL,
  kind          text NOT NULL,          -- chat|stream|embedding|rerank
  input_tokens  int NOT NULL DEFAULT 0,
  output_tokens int NOT NULL DEFAULT 0,
  cached_tokens int NOT NULL DEFAULT 0,
  cost_usd      numeric(12,6) NOT NULL DEFAULT 0,
  latency_ms    int NOT NULL DEFAULT 0,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_usage_user_time ON ai_usage_events(user_id, created_at);

-- deferred cross-fk added after both tables exist
ALTER TABLE resume_versions ADD CONSTRAINT fk_rv_job2
  FOREIGN KEY (job_id) REFERENCES jobs(id) DEFERRABLE INITIALLY DEFERRED;

-- updated_at triggers
CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS trigger AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['users','user_profiles','user_memories','resumes','companies','applications','knowledge_sources','user_notes','conversations','documents']
  LOOP
    EXECUTE format('CREATE TRIGGER trg_touch_%s BEFORE UPDATE ON %I FOR EACH ROW EXECUTE FUNCTION touch_updated_at()', t, t);
  END LOOP;
END $$;

-- citext for user emails
CREATE EXTENSION IF NOT EXISTS citext;
ALTER TABLE users ALTER COLUMN email TYPE citext;

-- vector dim is provider-dependent; enforce per-env at app level via settings check.
-- Default deployment: text-embedding-3-small (1536). HNSW index created lazily in V2 ops
-- script once first vectors are inserted (CREATE INDEX CONCURRENTLY not available in flyway tx
-- on first deploy is fine to run non-concurrently at small scale).
