-- Memory system schema (Postgres 17 + pgvector). Single source of truth for a fresh DB.
-- Existing DBs: apply migrations/*.sql instead.
-- Embedding dimension 768 = nomic-embed-text. If you change embedding model, change every vector(768).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ---------------------------------------------------------------
-- Users
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------
-- Relation types: tells the conflict detector whether a relation can
-- hold one value at a time (lives_in) or many (hobby).
-- routing_hint is extra text appended to the description when retrieval
-- routes a question to relation types (see retrieve.relation_ranks).
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS relation_types (
    name          TEXT PRIMARY KEY,
    cardinality   TEXT NOT NULL CHECK (cardinality IN ('single', 'multi')),
    description   TEXT,
    routing_hint  TEXT
);

INSERT INTO relation_types (name, cardinality, description, routing_hint) VALUES
    ('name',            'single', 'The user''s name',                      NULL),
    ('lives_in',        'single', 'Current city or country of residence',  NULL),
    ('works_at',        'single', 'Current employer',                      NULL),
    ('job_title',       'single', 'Current job title',                     NULL),
    ('partner',         'single', 'Current partner or spouse',             NULL),
    ('birthday',        'single', 'Date of birth',                         NULL),
    ('hobby',           'multi',  'Hobbies and interests',                 NULL),
    ('likes',           'multi',  'Things the user likes',                 NULL),
    ('dislikes',        'multi',  'Things the user dislikes',
        'Relevant to food, meals, recipes, cooking and what to avoid or skip.'),
    ('allergic_to',     'multi',  'Allergies',
        'Relevant to food, snacks, meals, recipes, restaurants, cooking and medicines.'),
    ('family_member',   'multi',  'Family members',                        NULL),
    ('speaks',          'multi',  'Languages spoken',                      NULL),
    ('goal',            'multi',  'Goals and plans',                       NULL)
ON CONFLICT (name) DO NOTHING;

-- ---------------------------------------------------------------
-- Summaries: compressed history of old messages
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS summaries (
    id           BIGSERIAL PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic        TEXT,
    content      TEXT NOT NULL,
    period_start TIMESTAMPTZ,
    period_end   TIMESTAMPTZ,
    importance   REAL NOT NULL DEFAULT 0.3 CHECK (importance BETWEEN 0 AND 1),
    embedding    vector(768),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------
-- Messages: raw conversation snippets (recent memory)
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id          BIGSERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id  TEXT,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    embedding   vector(768),
    importance  REAL NOT NULL DEFAULT 0.2 CHECK (importance BETWEEN 0 AND 1),
    archived    BOOLEAN NOT NULL DEFAULT FALSE,
    summary_id  BIGINT REFERENCES summaries(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------
-- Facts: structured, versioned knowledge about the user
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS facts (
    id                 BIGSERIAL PRIMARY KEY,
    user_id            TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject            TEXT NOT NULL DEFAULT 'user',
    relation           TEXT NOT NULL REFERENCES relation_types(name),
    value              TEXT NOT NULL,
    importance         REAL NOT NULL DEFAULT 0.5 CHECK (importance BETWEEN 0 AND 1),
    confidence         REAL NOT NULL DEFAULT 0.8 CHECK (confidence BETWEEN 0 AND 1),
    status             TEXT NOT NULL DEFAULT 'active'
                       CHECK (status IN ('active', 'superseded', 'conflicted', 'archived')),
    valid_from         TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to           TIMESTAMPTZ,
    superseded_by      BIGINT REFERENCES facts(id) ON DELETE SET NULL,
    source_message_id  BIGINT REFERENCES messages(id) ON DELETE SET NULL,
    access_count       INTEGER NOT NULL DEFAULT 0,
    last_accessed_at   TIMESTAMPTZ,
    embedding          vector(768),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- No exact duplicate active facts
CREATE UNIQUE INDEX IF NOT EXISTS facts_unique_active
    ON facts (user_id, subject, relation, lower(value))
    WHERE status = 'active';

-- ---------------------------------------------------------------
-- Relations: lightweight knowledge graph edges between entities
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS relations (
    id          BIGSERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    source      TEXT NOT NULL,
    relation    TEXT NOT NULL,
    target      TEXT NOT NULL,
    valid_from  TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to    TIMESTAMPTZ,
    fact_id     BIGINT REFERENCES facts(id) ON DELETE SET NULL
);

-- ---------------------------------------------------------------
-- Memory events: audit log of everything the manager does
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memory_events (
    id          BIGSERIAL PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type  TEXT NOT NULL
                CHECK (event_type IN ('add', 'duplicate', 'update', 'conflict', 'summarize', 'archive', 'retrieve')),
    fact_id     BIGINT REFERENCES facts(id) ON DELETE SET NULL,
    details     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------
CREATE INDEX IF NOT EXISTS messages_embedding_idx
    ON messages USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS facts_embedding_idx
    ON facts USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS summaries_embedding_idx
    ON summaries USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS facts_lookup_idx
    ON facts (user_id, subject, relation) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS facts_value_trgm_idx
    ON facts USING gin (value gin_trgm_ops);
CREATE INDEX IF NOT EXISTS messages_user_time_idx
    ON messages (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS events_user_time_idx
    ON memory_events (user_id, created_at DESC);
