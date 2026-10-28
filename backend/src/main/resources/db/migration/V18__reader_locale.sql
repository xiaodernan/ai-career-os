-- The reader's language (roadmap 21.4).
--
-- The product speaks two languages and the browser has always been able to say which one it
-- shows, but the account had no copy of that fact: the nightly letter was composed and mailed
-- in English whatever the reader had chosen. The account now carries the language, written by
-- the language switch, so a sweep that runs without a browser can still address the reader in
-- their own words -- both in the engine's signals and in the letter's chrome.
--
-- `users.locale` is the account's current language. It is the account's, not the device's:
-- a reader who switches on one device is telling the product how to write to them, not only
-- how to paint this screen.
ALTER TABLE users ADD COLUMN locale VARCHAR(8) NOT NULL DEFAULT 'en'
    CONSTRAINT users_locale_is_known CHECK (locale IN ('en', 'zh'));

-- The letter freezes its language with its words (roadmap 21.4). The payload's signals are
-- prose the engine already wrote in that language, so the mail chrome has to agree with them
-- -- including on a retry, days later, when the reader may have switched again. Rows written
-- before this column are English, which is what they were.
ALTER TABLE weekly_digests ADD COLUMN locale VARCHAR(8) NOT NULL DEFAULT 'en'
    CONSTRAINT weekly_digests_locale_is_known CHECK (locale IN ('en', 'zh'));
