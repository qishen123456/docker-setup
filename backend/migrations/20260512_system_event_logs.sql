-- System event logs for access, auth, errors, and low-confidence answers.

CREATE TABLE IF NOT EXISTS system_event_logs (
    id BIGSERIAL PRIMARY KEY,
    category VARCHAR(48) NOT NULL DEFAULT 'access',
    event_type VARCHAR(96) NOT NULL DEFAULT 'event',
    level VARCHAR(24) NOT NULL DEFAULT 'info',
    title VARCHAR(255) NOT NULL DEFAULT '',
    username VARCHAR(128) NOT NULL DEFAULT '',
    user_name VARCHAR(255) NOT NULL DEFAULT '',
    user_role VARCHAR(64) NOT NULL DEFAULT '',
    user_source VARCHAR(64) NOT NULL DEFAULT '',
    ip_address VARCHAR(96) NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    request_method VARCHAR(16) NOT NULL DEFAULT '',
    request_path TEXT NOT NULL DEFAULT '',
    status_code INT,
    duration_ms INT,
    question TEXT NOT NULL DEFAULT '',
    thinking_process JSONB NOT NULL DEFAULT '[]'::jsonb,
    sql_text TEXT NOT NULL DEFAULT '',
    answer_text TEXT NOT NULL DEFAULT '',
    confidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT NOT NULL DEFAULT '',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_system_event_logs_category_time
    ON system_event_logs (category, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_event_logs_level_time
    ON system_event_logs (level, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_event_logs_user_time
    ON system_event_logs (username, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_event_logs_event_type_time
    ON system_event_logs (event_type, created_at DESC);
