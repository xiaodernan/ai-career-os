-- The classifier's reading of a forwarded reply (roadmap 37.2). The webhook stores the letter
-- first and files the reading afterwards, so NULL here means "the classifier has not answered
-- for this letter" -- an outage, a slow model, or a letter nobody has read yet -- and never
-- "there was nothing to read". 37.3 files the letter onto the application this reading names.
--
-- `intent` is one of rejection / interview / offer / info / other, decided by the ai-service's
-- deterministic cue passes first and only then by the model; the CHECK keeps the column honest
-- even if a future writer forgets the five. `company` and `role` are the names the letter
-- carried, copied as written, blank when it named none.
ALTER TABLE inbound_mails
    ADD COLUMN intent  VARCHAR(16),
    ADD COLUMN company VARCHAR(200),
    ADD COLUMN role    VARCHAR(200),
    ADD CONSTRAINT ck_inbound_mails_intent
        CHECK (intent IS NULL OR intent IN ('rejection', 'interview', 'offer', 'info', 'other'));
