#!/usr/bin/env bash
set -uo pipefail

OUTPUT_DIR="backups"
SKIP_DB_DUMP=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="${2:-backups}"
      shift 2
      ;;
    --skip-db-dump)
      SKIP_DB_DUMP=1
      shift
      ;;
    -h|--help)
      cat <<'EOF'
SmartAsk Linux 备份脚本

用法：
  bash backup.sh
  bash backup.sh --skip-db-dump
  bash backup.sh --output-dir backups

说明：
  备份 config、.env、当前 Git commit、docker compose 状态，并默认导出 PostgreSQL SQL dump。
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

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_ROOT="$SCRIPT_DIR/$OUTPUT_DIR"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
mkdir -p "$BACKUP_DIR"

echo "SmartAsk Linux backup"
echo "输出目录: $BACKUP_DIR"

run_cmd() {
  local name="$1"
  shift
  {
    echo "\$ $*"
    "$@"
  } >"$BACKUP_DIR/$name.txt" 2>&1 || true
}

echo "==> 备份运行配置"
if [[ -d config ]]; then
  tar -czf "$BACKUP_DIR/config.tar.gz" config || true
fi
if [[ -f .env ]]; then
  cp .env "$BACKUP_DIR/.env"
fi
if [[ -f .env.example ]]; then
  cp .env.example "$BACKUP_DIR/.env.example"
fi

echo "==> 记录 Git 与 Docker 状态"
run_cmd "git_status" git status --short
run_cmd "git_head" git rev-parse HEAD
run_cmd "git_branch" git branch -vv
run_cmd "compose_ps" docker compose ps -a
run_cmd "compose_config" docker compose config

if [[ "$SKIP_DB_DUMP" -eq 0 ]]; then
  echo "==> 导出 PostgreSQL"
  docker compose exec -T postgres sh -lc \
    'pg_dump --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
    >"$BACKUP_DIR/postgres.sql" 2>"$BACKUP_DIR/postgres_dump_error.txt" || true
  if [[ ! -s "$BACKUP_DIR/postgres.sql" ]]; then
    rm -f "$BACKUP_DIR/postgres.sql"
    echo "  [WARN] PostgreSQL dump failed, see postgres_dump_error.txt"
  fi
fi

cat >"$BACKUP_DIR/README.txt" <<EOF
SmartAsk Linux backup
Time: $TIMESTAMP
Project: $SCRIPT_DIR

Contents:
- config.tar.gz
- .env
- .env.example
- postgres.sql unless --skip-db-dump was used
- git_*.txt
- compose_*.txt

Restore example:
  bash restore.sh --backup-dir "$BACKUP_DIR" --confirm
EOF

echo ""
echo "备份完成: $BACKUP_DIR"
