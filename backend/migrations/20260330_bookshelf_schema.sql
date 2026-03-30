-- Bookshelf schema for dataset-isolated 4-agent architecture
-- PostgreSQL migration script

BEGIN;

CREATE TABLE IF NOT EXISTS bs_datasets (
    id BIGSERIAL PRIMARY KEY,
    dataset_code VARCHAR(128) NOT NULL UNIQUE,
    dataset_name VARCHAR(255) NOT NULL,
    business_domain VARCHAR(128) NOT NULL,
    source_id BIGINT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bs_datasets_active ON bs_datasets (is_active);
CREATE INDEX IF NOT EXISTS idx_bs_datasets_source ON bs_datasets (source_id);

CREATE TABLE IF NOT EXISTS bs_dataset_synonyms (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
    synonym VARCHAR(255) NOT NULL,
    normalized_synonym VARCHAR(255) NOT NULL,
    weight INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_bs_dataset_synonyms_dataset_synonym
    ON bs_dataset_synonyms (dataset_id, normalized_synonym);
CREATE INDEX IF NOT EXISTS idx_bs_dataset_synonyms_norm
    ON bs_dataset_synonyms (normalized_synonym);

CREATE TABLE IF NOT EXISTS bs_lld_documents (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
    version INT NOT NULL DEFAULT 1,
    title VARCHAR(255) NOT NULL DEFAULT 'LLD',
    content TEXT NOT NULL,
    redline_rules JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by VARCHAR(128) NOT NULL DEFAULT 'system',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(dataset_id, version)
);

CREATE INDEX IF NOT EXISTS idx_bs_lld_documents_dataset
    ON bs_lld_documents (dataset_id, is_active, version DESC);

CREATE TABLE IF NOT EXISTS bs_data_dictionary_items (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    column_name VARCHAR(255) NOT NULL,
    jsonb_key VARCHAR(255),
    semantic_name VARCHAR(255) NOT NULL,
    data_type VARCHAR(64) NOT NULL DEFAULT 'text',
    enum_mapping JSONB NOT NULL DEFAULT '{}'::jsonb,
    extraction_rule TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bs_dictionary_dataset
    ON bs_data_dictionary_items (dataset_id, is_active);
CREATE INDEX IF NOT EXISTS idx_bs_dictionary_table_column
    ON bs_data_dictionary_items (dataset_id, table_name, column_name);

CREATE TABLE IF NOT EXISTS bs_schema_definitions (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
    table_name VARCHAR(255) NOT NULL,
    ddl_sql TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(dataset_id, table_name)
);

CREATE INDEX IF NOT EXISTS idx_bs_schema_definitions_dataset
    ON bs_schema_definitions (dataset_id, is_active);

CREATE TABLE IF NOT EXISTS bs_table_relations (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
    left_table VARCHAR(255) NOT NULL,
    left_key VARCHAR(255) NOT NULL,
    right_table VARCHAR(255) NOT NULL,
    right_key VARCHAR(255) NOT NULL,
    relation_type VARCHAR(32) NOT NULL DEFAULT 'inner',
    description TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bs_table_relations_dataset
    ON bs_table_relations (dataset_id, is_active);

CREATE TABLE IF NOT EXISTS bs_golden_sql_samples (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
    intent_type VARCHAR(64) NOT NULL DEFAULT 'detail',
    question TEXT NOT NULL,
    sql_text TEXT NOT NULL,
    tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    quality_score INT NOT NULL DEFAULT 80,
    usage_count BIGINT NOT NULL DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by VARCHAR(128) NOT NULL DEFAULT 'system',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bs_golden_sql_dataset
    ON bs_golden_sql_samples (dataset_id, is_active, quality_score DESC, updated_at DESC);

CREATE TABLE IF NOT EXISTS bs_agent_prompt_fragments (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
    agent_no SMALLINT NOT NULL CHECK (agent_no IN (1, 2, 3, 4)),
    prompt_key VARCHAR(64) NOT NULL DEFAULT 'default',
    prompt_content TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by VARCHAR(128) NOT NULL DEFAULT 'system',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(dataset_id, agent_no, prompt_key)
);

CREATE INDEX IF NOT EXISTS idx_bs_agent_prompt_dataset
    ON bs_agent_prompt_fragments (dataset_id, agent_no, is_active);

COMMIT;
