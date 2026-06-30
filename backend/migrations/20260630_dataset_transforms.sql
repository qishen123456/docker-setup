CREATE TABLE IF NOT EXISTS bs_dataset_transforms (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_table VARCHAR(255) NOT NULL,
    target_type VARCHAR(32) NOT NULL DEFAULT 'view',
    target_name VARCHAR(255) NOT NULL,
    transform_sql TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    auto_run_on_sync BOOLEAN DEFAULT FALSE,
    sync_dependency TEXT,
    last_run_at TIMESTAMPTZ,
    last_run_status VARCHAR(32),
    last_run_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dataset_transforms_dataset
    ON bs_dataset_transforms(dataset_id);
CREATE INDEX IF NOT EXISTS idx_dataset_transforms_source
    ON bs_dataset_transforms(source_table, is_active);
