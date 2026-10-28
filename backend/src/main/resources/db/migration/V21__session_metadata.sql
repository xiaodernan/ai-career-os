-- A refresh-token family is one signed-in device. Naming it when it starts is what lets
-- the account later recognise the doors it left open; until now a family was only an
-- opaque id, so "sign out everywhere" was the only lever the reader had.
ALTER TABLE refresh_tokens ADD COLUMN user_agent varchar(255);
ALTER TABLE refresh_tokens ADD COLUMN client_ip varchar(45);
