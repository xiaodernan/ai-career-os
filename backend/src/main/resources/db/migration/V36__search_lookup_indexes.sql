-- High-traffic lookup indexes (114/121).
--
-- The global search reads the reader's own rows ordered by updated_at DESC, then id ASC,
-- in four surfaces: resumes, notes, conversations and applications -- plus the letters
-- kept on applications ordered the same way. The existing single-column user_id indexes
-- serve WHERE user_id = :userId but not the ORDER BY suffix, so PostgreSQL must sort the
-- result set per hit; these composites make each a single-index scan in query order.
--
-- V35 is the highest prior version; this one keeps the strict numeric ordering the
-- nightly CI glob applies (V*.sql sorted with -V).
--
-- IF NOT EXISTS for the same reason as every other index here: a partially-applied
-- night must not stop the next one.
CREATE INDEX IF NOT EXISTS idx_resumes_user_updated ON resumes (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_notes_user_updated ON user_notes (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_user_updated ON conversations (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_applications_user_updated ON applications (user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_application_letters_user_updated ON application_letters (user_id, updated_at DESC);
