-- The nightly retention sweep deletes credential rows by age, and none of the three
-- tables indexed the column that age is measured on: every sweep would scan the full
-- table to find the handful of rows past the cutoff. These indexes turn that scan into
-- a range read, which is the difference between a sweep that stays cheap as the tables
-- grow and one that gets slower every night.
CREATE INDEX idx_refresh_expires ON refresh_tokens(expires_at);
CREATE INDEX idx_reset_expires ON password_reset_tokens(expires_at);
CREATE INDEX idx_email_change_expires ON email_change_tokens(expires_at);
