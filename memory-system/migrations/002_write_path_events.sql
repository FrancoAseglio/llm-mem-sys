-- 002: event types for the write-path fixes (retract, reject, contradiction).
-- Only for databases created before them; a fresh database gets this from schema.sql.
-- Safe to run more than once.

ALTER TABLE memory_events DROP CONSTRAINT IF EXISTS memory_events_event_type_check;
ALTER TABLE memory_events ADD CONSTRAINT memory_events_event_type_check
    CHECK (event_type IN ('add', 'duplicate', 'update', 'conflict', 'summarize', 'archive', 'retrieve',
                          'retract', 'reject', 'contradiction'));
