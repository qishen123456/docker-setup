"""
飞书多维表格数据同步服务
"""

import requests
import json
import psycopg2
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import threading
import schedule

from feishu_sync_manager import (
    get_feishu_configs, 
    update_sync_status, 
    read_feishu_config
)
from feishu_sync_logger import write_log
from config_manager import read_json

class FeishuSyncService:
    """飞书同步服务"""
    
    def __init__(self):
        self.sync_threads = {}
        self.running = False
        
    def get_access_token(self, app_id: str, app_secret: str, config_id: int) -> Optional[str]:
        """获取飞书访问令牌"""
        try:
            write_log(config_id, 'INFO', f'开始获取飞书访问令牌, App ID: {app_id[:10]}...')
            
            payload = {
                "app_id": app_id,
                "app_secret": app_secret
            }
            headers = {'Content-Type': 'application/json'}
            
            response = requests.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                headers=headers, 
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("code") == 0:
                token = data["tenant_access_token"]
                write_log(config_id, 'SUCCESS', '飞书访问令牌获取成功')
                return token
            else:
                error_msg = f"获取飞书Token失败: {data.get('msg')}"
                write_log(config_id, 'ERROR', error_msg)
                return None
                
        except Exception as e:
            error_msg = f"获取飞书Token异常: {e}"
            write_log(config_id, 'ERROR', error_msg)
            return None
    
    def get_feishu_data(self, config: Dict, access_token: str) -> Optional[List[Dict]]:
        """获取飞书多维表格数据"""
        try:
            write_log(config['id'], 'INFO', f'开始获取飞书数据, Base ID: {config["base_id"][:10]}..., Table ID: {config["table_id"][:10]}...')
            
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{config['base_id']}/tables/{config['table_id']}/records"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            params = {}
            if config.get('view_id'):
                params['view_id'] = config['view_id']
            
            all_records = []
            page_token = None
            page_count = 0
            
            while True:
                page_count += 1
                current_params = params.copy()
                if page_token:
                    current_params['page_token'] = page_token
                
                response = requests.get(url, headers=headers, params=current_params, timeout=60)
                response.raise_for_status()
                
                data = response.json()
                if data.get("code") == 0:
                    items = data.get("data", {}).get("items", [])
                    current_page_size = len(items)
                    all_records.extend(items)
                    
                    write_log(config['id'], 'INFO', f'获取第{page_count}页数据，{current_page_size}条记录')
                    
                    next_page_token = data.get("data", {}).get("page_token")
                    if not next_page_token:
                        break
                    page_token = next_page_token
                else:
                    error_msg = f"获取飞书数据失败: {data.get('msg')}"
                    write_log(config['id'], 'ERROR', error_msg)
                    return None
            
            write_log(config['id'], 'SUCCESS', f'飞书数据获取完成，共{len(all_records)}条记录，{page_count}页')
            return all_records
            
        except Exception as e:
            error_msg = f"获取飞书数据异常: {e}"
            write_log(config['id'], 'ERROR', error_msg)
            return None
    
    def get_postgres_connection(self, config: Dict) -> Optional[psycopg2.extensions.connection]:
        """获取PostgreSQL连接"""
        try:
            # 直接读取数据源配置文件
            import json
            import os
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
            config_file = os.path.join(config_dir, 'datasources.json')
            local_file = os.path.join(config_dir, 'datasources.local.json')
            if os.path.exists(local_file):
                config_file = local_file
            
            with open(config_file, 'r', encoding='utf-8') as f:
                datasources = json.load(f)
            
            db_config = None
            for db in datasources.get('databases', []):
                if db.get('type') == 'postgresql' and db.get('is_active'):
                    db_config = db
                    break
            
            if not db_config:
                print("未找到活跃的PostgreSQL数据源")
                return None
            
            import base64
            password = base64.b64decode(db_config['password_b64']).decode('utf-8')
            
            conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database_name'],
                user=db_config['username'],
                password=password,
                connect_timeout=30
            )
            return conn
            
        except Exception as e:
            print(f"连接PostgreSQL失败: {e}")
            return None
    
    def create_target_table(self, conn: psycopg2.extensions.connection, table_name: str) -> bool:
        """创建目标表"""
        try:
            cursor = conn.cursor()
            
            # 创建表结构（根据飞书数据结构）
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                record_id VARCHAR(255) UNIQUE,
                fields JSONB,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_{table_name}_record_id ON {table_name}(record_id);
            CREATE INDEX IF NOT EXISTS idx_{table_name}_sync_time ON {table_name}(sync_time);
            """
            
            cursor.execute(create_table_sql)
            conn.commit()
            print(f"成功创建/更新表: {table_name}")
            return True
            
        except Exception as e:
            print(f"创建表失败: {e}")
            return False
    
    def get_last_sync_time(self, conn: psycopg2.extensions.connection, table_name: str) -> Optional[datetime]:
        """获取最后同步时间"""
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT MAX(sync_time) FROM {table_name}")
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
        except Exception:
            return None
    
    def sync_data_to_postgres(self, config: Dict, records: List[Dict]) -> bool:
        """同步数据到PostgreSQL"""
        conn = self.get_postgres_connection(config)
        if not conn:
            return False
        
        try:
            table_name = config['target_table']
            
            # 创建目标表
            if not self.create_target_table(conn, table_name):
                return False
            
            cursor = conn.cursor()
            
            # 增量同步：只同步新记录
            if config.get('sync_mode') == 'incremental':
                last_sync_time = self.get_last_sync_time(conn, table_name)
                if last_sync_time:
                    # 过滤出更新的记录（这里简化处理，实际应该比较记录的更新时间）
                    existing_records = set()
                    cursor.execute(f"SELECT record_id FROM {table_name}")
                    existing_records.update(row[0] for row in cursor.fetchall())
                    
                    # 只同步新记录
                    new_records = [r for r in records if r.get('record_id') not in existing_records]
                    records_to_sync = new_records
                    print(f"增量同步：共{len(records)}条记录，新增{len(new_records)}条")
                else:
                    records_to_sync = records
                    print(f"首次全量同步：{len(records)}条记录")
            else:
                # 全量同步
                records_to_sync = records
                print(f"全量同步：{len(records)}条记录")
            
            # 批量插入/更新数据
            if records_to_sync:
                sync_time = datetime.now()
                for record in records_to_sync:
                    record_id = record.get('record_id', '')
                    fields_json = json.dumps(record.get('fields', {}), ensure_ascii=False)
                    
                    # 使用UPSERT操作
                    cursor.execute(f"""
                        INSERT INTO {table_name} (record_id, fields, sync_time, created_time, updated_time)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (record_id) 
                        DO UPDATE SET 
                            fields = EXCLUDED.fields,
                            sync_time = EXCLUDED.sync_time,
                            updated_time = EXCLUDED.updated_time
                    """, (record_id, fields_json, sync_time, sync_time, sync_time))
                
                conn.commit()
                print(f"成功同步{len(records_to_sync)}条记录到{table_name}")
            
            return True
            
        except Exception as e:
            print(f"同步数据到PostgreSQL失败: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def sync_single_config(self, config: Dict) -> bool:
        """同步单个配置"""
        try:
            print(f"\n开始同步配置: {config['name']}")
            update_sync_status(config['id'], 'running')
            
            # 获取访问令牌
            access_token = self.get_access_token(config['app_id'], config['app_secret'], config['id'])
            if not access_token:
                update_sync_status(config['id'], 'failed')
                return False
            
            # 获取飞书数据
            records = self.get_feishu_data(config, access_token)
            if records is None:
                update_sync_status(config['id'], 'failed')
                return False
            
            # 同步到PostgreSQL
            write_log(config['id'], 'INFO', f'开始同步数据到PostgreSQL，共{len(records)}条记录')
            success = self.sync_data_to_postgres(config, records)
            if success:
                sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                write_log(config['id'], 'INFO', f'数据库同步成功，更新状态为success')
                update_sync_status(config['id'], 'success', sync_time)
                write_log(config['id'], 'SUCCESS', f'配置 {config["name"]} 同步完成')
                print(f"配置 {config['name']} 同步完成")
            else:
                write_log(config['id'], 'ERROR', f'数据库同步失败，更新状态为failed')
                update_sync_status(config['id'], 'failed')
                print(f"配置 {config['name']} 同步失败")
            
            return success
            
        except Exception as e:
            print(f"同步配置 {config['name']} 异常: {e}")
            update_sync_status(config['id'], 'failed')
            return False
    
    def sync_all_active_configs(self):
        """同步所有活跃配置"""
        configs = get_feishu_configs()
        active_configs = [c for c in configs if c.get('is_active')]
        
        if not active_configs:
            print("没有活跃的飞书同步配置")
            return
        
        print(f"开始同步{len(active_configs)}个活跃配置")
        
        for config in active_configs:
            self.sync_single_config(config)
    
    def start_scheduler(self):
        """启动定时同步"""
        print("启动飞书同步调度器...")
        
        # 配置定时任务
        configs = get_feishu_configs()
        for config in configs:
            if config.get('is_active'):
                frequency = int(config.get('sync_frequency', 30))  # 分钟
                schedule.every(frequency).minutes.do(
                    self.sync_single_config, config
                ).tag(f"feishu_sync_{config['id']}")
        
        # 立即执行一次同步
        self.sync_all_active_configs()
        
        # 启动调度器
        self.running = True
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    def stop_scheduler(self):
        """停止定时同步"""
        print("停止飞书同步调度器...")
        self.running = False
        schedule.clear()

# 全局同步服务实例
sync_service = FeishuSyncService()

def start_feishu_sync():
    """启动飞书同步服务"""
    try:
        sync_service.start_scheduler()
    except KeyboardInterrupt:
        print("飞书同步服务被用户中断")
        sync_service.stop_scheduler()
    except Exception as e:
        print(f"飞书同步服务异常: {e}")

if __name__ == "__main__":
    start_feishu_sync()
