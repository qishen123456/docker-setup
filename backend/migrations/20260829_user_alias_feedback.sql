-- 解析条修正写回学习（parse-bar-design.md Phase 2.5）
-- 记录用户在解析条上的槽位修正：仅本人叠加生效（"已学习"提示），绝不自动改写解析、绝不直写书架。
-- 达阈值后由管理员审核合并进书架（审核 UI 后续再做，本表先沉淀数据）。

CREATE TABLE IF NOT EXISTS user_alias_feedback (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(128) NOT NULL DEFAULT '',
    slot VARCHAR(16) NOT NULL DEFAULT '',
    question TEXT NOT NULL DEFAULT '',
    span_text VARCHAR(255) NOT NULL DEFAULT '',
    original_resolved VARCHAR(255) NOT NULL DEFAULT '',
    new_value VARCHAR(255) NOT NULL DEFAULT '',
    dataset_id INT,
    session_id VARCHAR(128) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_alias_feedback_user_span
    ON user_alias_feedback (user_id, slot, span_text, created_at DESC);
