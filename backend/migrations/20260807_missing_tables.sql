-- 20260807_missing_tables.sql
-- 审计修正 L-01/L-02（2026-08-06）：
-- angel_group_data 表原本只在 docker/postgres/init/002_angel_group_data.sql 中定义，
-- 仅在数据目录为空时执行一次，非全新数据卷环境必然缺表。
-- bs_common_questions / bs_dataset_external_configs / bs_regression_cases 三张表
-- 唯一定义在 controllers/bookshelf.py:526-570 内联 DDL，不在任何迁移文件中。
-- 本迁移文件把上述四张表收敛到正规迁移体系，使 bootstrap 幂等建表。

-- angel_group_data（从 docker/postgres/init/002_angel_group_data.sql 迁入）
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

-- bs_common_questions（从 controllers/bookshelf.py:529-537 迁入）
CREATE TABLE IF NOT EXISTS bs_common_questions (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    sort_order INT NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- bs_dataset_external_configs（从 controllers/bookshelf.py:542-552 迁入）
CREATE TABLE IF NOT EXISTS bs_dataset_external_configs (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
    config_type VARCHAR(64) NOT NULL,
    config_key VARCHAR(128) NOT NULL,
    config_value JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(dataset_id, config_type, config_key)
);

-- bs_regression_cases（从 controllers/bookshelf.py:557-568 迁入）
CREATE TABLE IF NOT EXISTS bs_regression_cases (
    id BIGSERIAL PRIMARY KEY,
    dataset_id BIGINT NOT NULL REFERENCES bs_datasets(id) ON DELETE CASCADE,
    case_type VARCHAR(32) NOT NULL DEFAULT 'summary',
    question_text TEXT NOT NULL,
    expected_focus TEXT NOT NULL DEFAULT '',
    expected_intent VARCHAR(32) NOT NULL DEFAULT 'generate_sql',
    sort_order INT NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- bs_schema_definitions.source_id（从 controllers/bookshelf.py:573-574 迁入）
ALTER TABLE bs_schema_definitions
    ADD COLUMN IF NOT EXISTS source_id BIGINT;
