-- A kept letter can be corrected in place (roadmap 50.2). `created_at` answers when the
-- reader first chose it; `updated_at` answers when they last changed it, so the drawer can
-- say which of the two moments the text belongs to.
ALTER TABLE application_letters
  ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now();
