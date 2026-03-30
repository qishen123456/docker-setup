-- Upgrade prompt fragments to support Agent1~4 (was 2~4).

BEGIN;

DO $$
DECLARE
    c_name TEXT;
BEGIN
    SELECT con.conname
    INTO c_name
    FROM pg_constraint con
    JOIN pg_class rel ON rel.oid = con.conrelid
    WHERE rel.relname = 'bs_agent_prompt_fragments'
      AND con.contype = 'c'
      AND pg_get_constraintdef(con.oid) ILIKE '%agent_no%';

    IF c_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE bs_agent_prompt_fragments DROP CONSTRAINT %I;', c_name);
    END IF;
END $$;

ALTER TABLE bs_agent_prompt_fragments
    ADD CONSTRAINT bs_agent_prompt_fragments_agent_no_check
    CHECK (agent_no IN (1, 2, 3, 4));

COMMIT;

