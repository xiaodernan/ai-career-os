-- The rehearsal remembers the card it is for (roadmap 56.1). A session started from the
-- application drawer names the application it rehearses, so the interview list can point back
-- to that card and the loop the product describes -- track, prepare, feed back -- is recorded
-- rather than implied. Nullable: a free-practice session has no card, and deleting the card
-- leaves the practice history standing (ON DELETE SET NULL) instead of erasing it.
ALTER TABLE interview_sessions
  ADD COLUMN application_id uuid REFERENCES applications(id) ON DELETE SET NULL;
CREATE INDEX idx_interview_sessions_application ON interview_sessions(application_id);