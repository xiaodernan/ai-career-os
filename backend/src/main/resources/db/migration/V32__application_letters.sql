-- The letter a reader sends with the application (roadmap 47.4). Until now the cover letter was
-- a relay: the job page asked the ai-service for a draft and handed the text back to the browser,
-- so a letter that was worth keeping was kept nowhere. This table is that place -- one row per
-- saved draft, tied to the application it was written for, and carrying the same user_id the
-- export census uses to decide who owns it. A letter is the reader's own words, so it travels in
-- the bundle as its own section rather than as bookkeeping.
CREATE TABLE application_letters (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id    uuid NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  user_id           uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  job_id            uuid REFERENCES jobs(id) ON DELETE SET NULL,
  resume_version_id uuid REFERENCES resume_versions(id) ON DELETE SET NULL,
  mode              text,
  tone              text,
  length            text,
  body              text NOT NULL,
  created_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_app_letters_app ON application_letters(application_id, created_at DESC);
CREATE INDEX idx_app_letters_user ON application_letters(user_id);
