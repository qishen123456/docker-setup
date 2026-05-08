#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR=""
CONFIRM=0
RESTORE_ENV=0
SKIP_DB=0
SKIP_CONFIG=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backup-dir)
      BACKUP_DIR="${2:-}"
      shift 2
      ;;
    --confirm)
      CONFIRM=1
      shift
      ;;
    --restore-env)
      RESTORE_ENV=1
      shift
      ;;
    --skip-db)
      SKIP_DB=1
      shift
      ;;
    --skip-config)
      SKIP_CONFIG=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
SmartAsk Linux 恢复脚本

用法：
  bash restore.sh --backup-dir backups/20260508_153000 --confirm
  bash restore.sh --backup-dir backups/20260508_153000 --confirm --restore-env

参数：
  --backup-dir PATH   备份目录，必填。
  --confirm           必填，确认执行恢复。
  --restore-env       同时恢复 .env，默认不恢复，避免覆盖生产密钥。
  --skip-db           不恢复 PostgreSQL。
  --skip-config       不恢复 config。

说明：
  恢复前会自动再执行一次 backup.sh，作为回滚前快照。
EOF
      exit 0
      ;;
    *)
      echo "未知参数: $1"
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

fail() { echo "  [ERR] $*" >&2; exit 1; }
info() { echo ""; echo "==> $*"; }
warn() { echo "  [WARN] $*"; }

[[ -n "$BACKUP_DIR" ]] || fail "必须指定 --backup-dir"
[[ -d "$BACKUP_DIR" ]] || fail "备份目录不存在: $BACKUP_DIR"
[[ "$CONFIRM" -eq 1 ]] || fail "恢复是高风险操作。请加 --confirm 明确确认。"

command -v docker >/dev/null 2>&1 || fail "未找到 docker 命令"
docker info >/dev/null 2>&1 || fail "Docker 未启动或当前用户无权限访问 Docker"

info "恢复前创建安全快照"
bash "$SCRIPT_DIR/backup.sh" || warn "恢复前备份失败，请确认是否继续。"

info "停止后端，避免恢复期间写入"
docker compose stop backend || true

if [[ "$SKIP_CONFIG" -eq 0 ]]; then
  info "恢复 config"
  if [[ -f "$BACKUP_DIR/config.tar.gz" ]]; then
    mkdir -p config
    tar -xzf "$BACKUP_DIR/config.tar.gz" -C "$SCRIPT_DIR"
  elif [[ -d "$BACKUP_DIR/config" ]]; then
    rm -rf config
    cp -a "$BACKUP_DIR/config" config
  else
    warn "备份中没有 config.tar.gz 或 config/，跳过 config 恢复"
  fi
fi

if [[ "$RESTORE_ENV" -eq 1 ]]; then
  info "恢复 .env"
  if [[ -f "$BACKUP_DIR/.env" ]]; then
    cp "$BACKUP_DIR/.env" .env
  else
    warn "备份中没有 .env，跳过 .env 恢复"
  fi
else
  warn "默认不恢复 .env。如需恢复生产密钥配置，请加 --restore-env"
fi

if [[ "$SKIP_DB" -eq 0 ]]; then
  info "恢复 PostgreSQL"
  if [[ -f "$BACKUP_DIR/postgres.sql" ]]; then
    docker compose up -d postgres
    for _ in $(seq 1 60); do
      if docker compose exec -T postgres sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
        break
      fi
      sleep 2
    done
    cat "$BACKUP_DIR/postgres.sql" | docker compose exec -T postgres sh -lc \
      'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
  else
    warn "备份中没有 postgres.sql，跳过数据库恢复"
  fi
fi

info "启动服务"
docker compose up -d
docker compose ps

echo ""
echo "恢复完成。建议执行："
echo "  curl http://127.0.0.1:5002/api/health"
echo "  bash doctor.sh"
