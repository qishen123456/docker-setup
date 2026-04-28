CREATE TABLE IF NOT EXISTS angel_group_data (
    id BIGSERIAL PRIMARY KEY,
    record_id TEXT UNIQUE,
    fields JSONB NOT NULL DEFAULT '{}'::jsonb,
    sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_angel_group_data_fields
    ON angel_group_data USING GIN (fields);
