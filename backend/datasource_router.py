"""
Data source router for multi-source Vanna instances.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config_manager import decode_secret, get_default_ai_model


class DataSourceRouter:
    def __init__(self):
        self.data_sources: Dict[int, Dict] = {}
        self.keywords: Dict[int, List[str]] = {}
        self.load_data_source_config()

    def load_data_source_config(self):
        self.data_sources = {}
        self.keywords = {}
        config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
        config_path = os.path.join(config_dir, "datasources.json")
        local_path = os.path.join(config_dir, "datasources.local.json")
        if os.path.exists(local_path):
            config_path = local_path
        try:
            with open(config_path, "r", encoding="utf-8-sig") as f:
                config = json.load(f)
        except Exception:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

        for db in config.get("databases", []):
            if not db.get("is_active"):
                continue
            ds_id = int(db["id"])
            ds_name = db.get("name", "")
            ds_type = (db.get("type") or "").lower()
            self.data_sources[ds_id] = {"name": ds_name, "type": ds_type, "config": db}
            self.keywords[ds_id] = self._generate_keywords(ds_name, ds_type)

    def _generate_keywords(self, name: str, db_type: str) -> List[str]:
        name_lower = (name or "").lower()
        keywords: List[str] = []

        if any(token in name_lower for token in ["feishu", "dtable"]) or "飞书" in name or "多维表格" in name:
            keywords.extend(["飞书", "多维表格", "事业部", "分公司", "代表处", "业务代表", "业绩", "任务", "开单"])
        if "crm" in name_lower or "客户" in name:
            keywords.extend(["客户", "商机", "合同", "订单", "crm"])

        for year in ["2023", "2024", "2025", "2026"]:
            if year in name:
                keywords.append(year)

        if db_type:
            keywords.append(db_type)
        return list(dict.fromkeys(keywords))

    def identify_data_source(self, question: str) -> Tuple[Optional[int], float]:
        question_lower = (question or "").lower()
        best_id: Optional[int] = None
        best_score = 0
        best_conf = 0.0

        for ds_id, words in self.keywords.items():
            if not words:
                continue
            score = sum(1 for w in words if w.lower() in question_lower)
            if score <= 0:
                continue
            confidence = score / max(len(words), 1)
            if score > best_score:
                best_id = ds_id
                best_score = score
                best_conf = confidence

        return best_id, best_conf

    def _decode_password(self, password_b64: str) -> str:
        if not password_b64:
            return ""
        try:
            return decode_secret(password_b64)
        except Exception:
            try:
                return base64.b64decode(password_b64).decode("utf-8")
            except Exception:
                return ""

    def _build_vanna_with_recovery(self, vanna_cls, vn_config):
        try:
            return vanna_cls(config=vn_config)
        except Exception as exc:
            message = str(exc)
            recoverable_errors = [
                "default_tenant",
                "Could not connect to tenant",
                "disk I/O error",
                "database disk image is malformed",
                "readonly database",
                "has no attribute 'bindings'",
            ]
            if not any(token in message for token in recoverable_errors):
                raise
            broken_path = vn_config.get("chroma_path")
            if broken_path and os.path.isdir(broken_path):
                shutil.rmtree(broken_path, ignore_errors=True)
            if broken_path:
                os.makedirs(broken_path, exist_ok=True)
            return vanna_cls(config=vn_config)

    def _connect_vanna_to_database(self, vn, db_config):
        db_type = (db_config.get("type") or "").lower()
        if db_type == "postgresql":
            vn.connect_to_postgres(
                host=db_config.get("host", "localhost"),
                dbname=db_config.get("database_name", ""),
                user=db_config.get("username", ""),
                password=self._decode_password(db_config.get("password_b64", "")),
                port=int(db_config.get("port", 5432) or 5432),
            )
            return
        if db_type == "mysql":
            vn.connect_to_mysql(
                host=db_config.get("host", "localhost"),
                dbname=db_config.get("database_name", ""),
                user=db_config.get("username", ""),
                password=self._decode_password(db_config.get("password_b64", "")),
                port=int(db_config.get("port", 3306) or 3306),
            )
            return
        if db_type == "sqlite":
            vn.connect_to_sqlite(db_config.get("sqlite_path", ""))
            return
        if db_type == "sqlserver":
            driver = db_config.get("driver", "ODBC Driver 17 for SQL Server")
            odbc_conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={db_config.get('host', '')};"
                f"DATABASE={db_config.get('database_name', '')};"
                f"UID={db_config.get('username', '')};"
                f"PWD={self._decode_password(db_config.get('password_b64', ''))}"
            )
            vn.connect_to_mssql(odbc_conn_str=odbc_conn_str)
            return
        raise ValueError(f"unsupported database type: {db_type}")

    def _resolve_sqlite_path(self, sqlite_path: str) -> str:
        if sqlite_path and sqlite_path != ":memory:" and not os.path.isabs(sqlite_path):
            return os.path.join(os.path.dirname(__file__), sqlite_path)
        return sqlite_path

    def _connect_raw_database(self, db_config):
        db_type = (db_config.get("type") or "").lower()
        if db_type == "postgresql":
            import psycopg2

            return psycopg2.connect(
                host=db_config.get("host", "localhost"),
                port=int(db_config.get("port", 5432) or 5432),
                dbname=db_config.get("database_name", ""),
                user=db_config.get("username", ""),
                password=self._decode_password(db_config.get("password_b64", "")),
            )
        if db_type == "mysql":
            import pymysql

            return pymysql.connect(
                host=db_config.get("host", "localhost"),
                port=int(db_config.get("port", 3306) or 3306),
                database=db_config.get("database_name", ""),
                user=db_config.get("username", ""),
                password=self._decode_password(db_config.get("password_b64", "")),
                charset="utf8mb4",
            )
        if db_type == "sqlite":
            import sqlite3

            return sqlite3.connect(self._resolve_sqlite_path(db_config.get("sqlite_path", ":memory:")))
        if db_type == "sqlserver":
            import pyodbc

            driver = db_config.get("driver", "ODBC Driver 17 for SQL Server")
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={db_config.get('host', '')};"
                f"DATABASE={db_config.get('database_name', '')};"
                f"UID={db_config.get('username', '')};"
                f"PWD={self._decode_password(db_config.get('password_b64', ''))}"
            )
            return pyodbc.connect(conn_str)
        raise ValueError(f"unsupported database type: {db_type}")

    def execute_sql_for_source(self, source_id: int, sql: str) -> pd.DataFrame:
        if source_id not in self.data_sources:
            raise ValueError("数据源不存在")

        db_config = self.data_sources[source_id]["config"]
        conn = self._connect_raw_database(db_config)
        try:
            return pd.read_sql_query(sql, conn)
        finally:
            conn.close()

    def get_vanna_for_source(self, source_id: int) -> Tuple[object, str]:
        if source_id not in self.data_sources:
            return None, "数据源不存在"

        source_config = self.data_sources[source_id]
        from vanna_core import MyVanna

        ai_model = get_default_ai_model()
        if not ai_model:
            return None, "未找到AI模型配置"

        chroma_path = os.path.join(os.path.dirname(__file__), f"chroma_db_source_{source_id}")
        vn_config = {
            "api_key": ai_model.get("api_key", ""),
            "model": ai_model.get("model", ""),
            "base_url": ai_model.get("base_url", ""),
            "chroma_path": chroma_path,
        }

        try:
            vn = self._build_vanna_with_recovery(MyVanna, vn_config)
            self._connect_vanna_to_database(vn, source_config["config"])
            return vn, None
        except Exception as exc:
            return None, f"创建Vanna实例失败: {exc}"


router = DataSourceRouter()
