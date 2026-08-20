#!/usr/bin/env python3
"""
容器内执行版本：统一数据视图迁移
用法：docker exec -i smartask-backend python3 /tmp/run_view_migration.py
"""
import sys
import os

sys.path.insert(0, '/app/backend')
os.chdir('/app/backend')

from dataset_transform_service import transform_service, TransformError

COMMERCIAL_SQL = """WITH base AS (
    SELECT id, record_id,
        CASE WHEN jsonb_typeof(fields->'事业部') = 'array' THEN fields->'事业部'->0->>'text' ELSE fields->>'事业部' END AS 事业部,
        CASE WHEN jsonb_typeof(fields->'分公司') = 'array' THEN fields->'分公司'->0->>'text' ELSE fields->>'分公司' END AS 分公司,
        CASE WHEN jsonb_typeof(fields->'代表处') = 'array' THEN fields->'代表处'->0->>'text' ELSE fields->>'代表处' END AS 代表处,
        CASE WHEN jsonb_typeof(fields->'业务代表') = 'array' THEN fields->'业务代表'->0->>'text' ELSE fields->>'业务代表' END AS 业务代表,
        COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'总任务（金额）') = 'array' THEN fields->'总任务（金额）'->0->>'text' ELSE fields->>'总任务（金额）' END, '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 年度目标营收,
        COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'年度开单金额') = 'array' THEN fields->'年度开单金额'->0->>'text' ELSE fields->>'年度开单金额' END, '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 年度开单金额,
        COALESCE(NULLIF(regexp_replace(CASE WHEN jsonb_typeof(fields->'总任务达成率') = 'array' THEN fields->'总任务达成率'->0->>'text' ELSE fields->>'总任务达成率' END, '[^0-9.-]', '', 'g'), ''), '0')::NUMERIC AS 总任务达成率,
        CASE WHEN jsonb_typeof(fields->'当前年') = 'array' THEN fields->'当前年'->0->>'text' ELSE fields->>'当前年' END AS 当前年,
        fields
    FROM {{source_table}}
    WHERE fields IS NOT NULL AND fields <> '{}'::jsonb
)
SELECT 
    id, record_id,
    CASE 
        WHEN 分公司 LIKE '%分公司' THEN '区域条线'
        WHEN 分公司 LIKE '%业务部' THEN '行业条线'
        ELSE '全事业部'
    END AS 条线,
    CASE 
        WHEN 业务代表 IS NOT NULL AND 业务代表 <> '' THEN '业务代表'
        WHEN 代表处 IS NOT NULL AND 代表处 <> '' THEN '代表处'
        WHEN 分公司 IS NOT NULL AND 分公司 <> '' THEN (CASE WHEN 分公司 LIKE '%分公司' THEN '分公司' ELSE '业务部' END)
        ELSE '事业部'
    END AS 层级级别,
    COALESCE(NULLIF(业务代表, ''), NULLIF(代表处, ''), NULLIF(分公司, ''), '商用事业部') AS 节点名称,
    CASE 
        WHEN 业务代表 IS NOT NULL AND 业务代表 <> '' THEN 代表处
        WHEN 代表处 IS NOT NULL AND 代表处 <> '' THEN 分公司
        WHEN 分公司 IS NOT NULL AND 分公司 <> '' THEN '商用事业部'
        ELSE NULL
    END AS 上级名称,
    事业部, 分公司, 代表处, 
    COALESCE(NULLIF(业务代表, ''), fields->>'总任务承接人', COALESCE(NULLIF(代表处, ''), NULLIF(分公司, ''), '商用事业部')) AS 业务代表,
    COALESCE(NULLIF(业务代表, ''), fields->>'总任务承接人', COALESCE(NULLIF(代表处, ''), NULLIF(分公司, ''), '商用事业部')) AS 负责人,
    年度目标营收, 年度开单金额,
    (年度目标营收 - 年度开单金额) AS 剩余任务金额,
    总任务达成率, 当前年,
    CONCAT(
        COALESCE(代表处, ''), ' ', COALESCE(分公司, ''), ' ',
        CASE 
            WHEN 代表处 LIKE '%粤东%' THEN '广州 深圳 东莞 佛山 粤东'
            WHEN 代表处 LIKE '%粤西%' THEN '粤西 南宁 广西 海南'
            WHEN 代表处 LIKE '%江苏%' THEN '南京 江苏 苏州'
            WHEN 代表处 LIKE '%浙江%' THEN '杭州 浙江 宁波'
            WHEN 代表处 LIKE '%安徽%' THEN '合肥 安徽'
            WHEN 代表处 LIKE '%湖北%' THEN '武汉 湖北'
            WHEN 代表处 LIKE '%湖南%' THEN '长沙 湖南'
            WHEN 代表处 LIKE '%江西%' THEN '南昌 江西'
            WHEN 代表处 LIKE '%四川%' THEN '成都 四川'
            WHEN 代表处 LIKE '%重庆%' THEN '重庆'
            WHEN 代表处 LIKE '%云贵%' THEN '昆明 贵阳 云南 贵州'
            WHEN 代表处 LIKE '%福建%' THEN '福建 福州 厦门'
            WHEN 代表处 LIKE '%上海%' THEN '上海'
            WHEN 代表处 LIKE '%北京%' THEN '北京'
            WHEN 代表处 LIKE '%辽宁%' THEN '辽宁 沈阳'
            WHEN 代表处 LIKE '%陕西%' THEN '陕西 西安'
            WHEN 代表处 LIKE '%山东%' THEN '山东 济南 青岛'
            WHEN 代表处 LIKE '%河南%' THEN '河南 郑州'
            ELSE ''
        END
    ) AS 城市标签,
    fields
FROM base"""

CONSUMER_SQL = """WITH base AS (
    SELECT 
        id, record_id,
        fields->>'事业部' AS 事业部,
        COALESCE(NULLIF(fields->>'分公司', ''), split_part(fields->>'链接字段(勿删)', chr(59), 2)) AS 销售大区,
        COALESCE(NULLIF(fields->>'城市公司', ''), split_part(fields->>'链接字段(勿删)', chr(59), 3)) AS 城市公司,
        fields->>'层级级别' AS 层级级别,
        fields->>'总任务承接人' AS 负责人,
        NULLIF(TRIM(fields->>'总任务（金额）'), '')::numeric AS 年度目标营收,
        NULLIF(TRIM(fields->>'年度开单金额'), '')::numeric AS 年度开单金额,
        NULLIF(TRIM(fields->>'总任务达成率'), '')::numeric AS 总任务达成率,
        NULLIF(TRIM(fields->>'线下-年度开单金额'), '')::numeric AS 线下开单金额,
        NULLIF(TRIM(fields->>'新零售-年度开单金额'), '')::numeric AS 新零售开单金额,
        NULLIF(TRIM(fields->>'燃气定制-年度开单金额'), '')::numeric AS 燃气定制开单金额,
        NULLIF(TRIM(fields->>'地产-年度开单金额'), '')::numeric AS 地产开单金额,
        fields->>'当前年' AS 当前年,
        fields->>'当前月' AS 当前月,
        fields
    FROM {{source_table}}
    WHERE fields IS NOT NULL AND fields <> '{}'::jsonb
)
SELECT 
    id, record_id, 事业部, 销售大区, 城市公司, 层级级别, 负责人,
    年度目标营收, 年度开单金额, 总任务达成率,
    线下开单金额, 新零售开单金额, 燃气定制开单金额, 地产开单金额,
    当前年, 当前月,
    CONCAT(
        销售大区, ' ', 城市公司, ' ',
        CASE 
            WHEN 销售大区 LIKE '%粤桂琼%' THEN '广东 广西 海南'
            WHEN 销售大区 LIKE '%豫晋%' THEN '河南 山西'
            WHEN 销售大区 LIKE '%江浙沪%' THEN '江苏 浙江 上海'
            WHEN 销售大区 LIKE '%鄂皖%' THEN '湖北 安徽'
            WHEN 销售大区 LIKE '%川藏%' THEN '四川 西藏'
            WHEN 销售大区 LIKE '%云贵渝%' THEN '云南 贵州 重庆'
            WHEN 销售大区 LIKE '%赣闽%' THEN '江西 福建'
            WHEN 销售大区 LIKE '%黑吉辽%' THEN '辽宁 吉林 黑龙江'
            WHEN 销售大区 LIKE '%西北%' THEN '陕西 甘肃 宁夏'
            WHEN 销售大区 LIKE '%京津%' THEN '北京 天津'
            WHEN 销售大区 LIKE '%山东%' THEN '山东'
            WHEN 销售大区 LIKE '%湖南%' THEN '湖南'
            WHEN 销售大区 LIKE '%河北%' THEN '河北'
            ELSE ''
        END
    ) AS 省份标签,
    fields
FROM base"""


def main():
    print("=" * 60)
    print("🚀 统一数据视图迁移开始")
    print("=" * 60)
    
    # Step 1: 更新商用视图
    print("\n[1/4] 更新商用视图 (id=8) ...")
    result = transform_service.update_transform(
        transform_id=8,
        data={
            "transform_sql": COMMERCIAL_SQL,
            "is_active": True,
            "auto_run_on_sync": True,
        }
    )
    print(f"  更新: {result}")
    
    exec_result = transform_service.execute_transform(transform_id=8, triggered_by="migration")
    print(f"  执行: {exec_result}")
    
    # Step 2: 新增消费者视图
    print("\n[2/4] 处理消费者视图 (dataset_id=2) ...")
    existing = transform_service.get_transforms(dataset_id=2)
    if existing:
        tid = existing[0]['id']
        print(f"  已存在 (id={tid})，更新 ...")
        transform_service.update_transform(
            transform_id=tid,
            data={
                "transform_sql": CONSUMER_SQL,
                "is_active": True,
                "auto_run_on_sync": True,
            }
        )
    else:
        tid = transform_service.create_transform({
            "dataset_id": 2,
            "name": "消费者事业部标准视图",
            "source_table": "feishu_tbl_xioafeizhe",
            "target_type": "view",
            "target_name": "v_feishu_xiaofeizhe",
            "transform_sql": CONSUMER_SQL,
            "is_active": True,
            "auto_run_on_sync": True,
        })
        print(f"  创建新 transform id={tid}")
    
    exec_result = transform_service.execute_transform(transform_id=tid, triggered_by="migration")
    print(f"  执行: {exec_result}")
    
    # Step 3: 验证
    print("\n[3/4] 验证三视图列结构 ...")
    import psycopg2
    conn = transform_service._connect()
    try:
        with conn.cursor() as cur:
            for vname, required_cols in [
                ('v_angel_group_data', ['条线', '层级级别', '节点名称', '上级名称', '剩余任务金额', '城市标签']),
                ('v_feishu_xiaofeizhe', ['省份标签', '线下开单金额', '新零售开单金额', '燃气定制开单金额', '地产开单金额']),
                ('v_feishu_tbldianshang', ['层级级别', '业务部', '负责人']),
            ]:
                cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position", (vname,))
                cols = [r[0] for r in cur.fetchall()]
                missing = [c for c in required_cols if c not in cols]
                status = "✅" if not missing else f"❌ 缺: {missing}"
                print(f"  {vname}: {status} (共{len(cols)}列)")
                
                try:
                    cur.execute(f"SELECT 1 FROM {vname} LIMIT 1")
                    row = cur.fetchone()
                    print(f"    查询: {'✅ 可查' if row else '⚠️ 空'}")
                except Exception as e:
                    print(f"    查询: ❌ {e}")
    finally:
        conn.close()
    
    # Step 4: 摘要
    print("\n[4/4] 当前 transform 列表:")
    for t in transform_service.get_transforms():
        print(f"  ID={t['id']} | 数据集={t['dataset_id']} | {t['name']} | {t['source_table']} → {t['target_name']} | 状态: {'启用' if t['is_active'] else '停用'}")
    
    print("\n" + "=" * 60)
    print("✅ Phase 1-2 完成！")
    print("下一步: Phase 3 审计与修正")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except TransformError as e:
        print(f"❌ TransformError: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
