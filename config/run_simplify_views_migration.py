"""精简三视图迁移脚本 - 在容器内执行

用法: docker cp 到容器后执行
"""

import sys
sys.path.insert(0, '/app/backend')

from dataset_transform_service import DatasetTransformService

service = DatasetTransformService()

# ============================================================================
# 电商视图：29列 → 13列
# 移除: 审批状态, 编号, 集团, 上级负责人, 当前月份任务达成率, 截止当前目标阈值达成率,
#        本月开单金额, 本月当前目标阈值, 年度阈值开单差额万, 总金额转换万, 
#        年度开单金额转换万, 当前月, q1-q4目标
# 保留: id, record_id, 事业部, 业务部, 细分业务, 层级级别, 负责人,
#        年度目标营收, 年度开单金额, 总任务达成率, 月度阈值开单差额万, 组织路径, 当前年
# ============================================================================
ECOMMERCE_SQL = """SELECT
  id,
  record_id,
  fields->>'事业部' AS 事业部,
  NULLIF(fields->>'业务部','') AS 业务部,
  NULLIF(fields->>'业务承接角色','') AS 细分业务,
  fields->>'层级级别' AS 层级级别,
  fields->>'任务承接人' AS 负责人,
  NULLIF(trim(fields->>'总任务（金额）'),'')::numeric AS 年度目标营收,
  NULLIF(trim(fields->>'年度开单金额'),'')::numeric AS 年度开单金额,
  NULLIF(trim(fields->>'总任务达成率'),'')::numeric AS 总任务达成率,
  ROUND((NULLIF(trim(fields->>'年度开单金额'),'')::numeric - NULLIF(trim(fields->>'总任务（金额）'),'')::numeric) / 12.0 / 10000.0, 2) AS 月度阈值开单差额万,
  fields->>'链接字段(勿删)' AS 组织路径,
  fields->>'当前年' AS 当前年
FROM {{source_table}}
WHERE fields IS NOT NULL AND fields <> '{}'::jsonb
  AND NULLIF(fields->>'编号','') IS NOT NULL"""

# ============================================================================
# 商用视图：修正层级级别(业务代表→业务经理)，精简字段
# ============================================================================
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
        WHEN 业务代表 IS NOT NULL AND 业务代表 <> '' THEN '业务经理'
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

# ============================================================================
# 消费者视图：补全空层级数据，精简字段
# ============================================================================
CONSUMER_SQL = """WITH base AS (
    SELECT
        id, record_id,
        fields->>'事业部' AS 事业部,
        COALESCE(NULLIF(fields->>'分公司', ''), split_part(fields->>'链接字段(勿删)', chr(59), 2)) AS 销售大区,
        COALESCE(NULLIF(fields->>'城市公司', ''), split_part(fields->>'链接字段(勿删)', chr(59), 3)) AS 城市公司,
        COALESCE(NULLIF(fields->>'层级级别', ''),
            CASE
                WHEN NULLIF(fields->>'城市公司', '') IS NOT NULL THEN '城市分公司'
                WHEN NULLIF(fields->>'分公司', '') IS NOT NULL THEN '分公司'
                ELSE '事业部'
            END
        ) AS 层级级别,
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


def migrate():
    print("=" * 60)
    print("🚀 三视图精简迁移开始")
    print("=" * 60)

    # 1. 电商视图
    print("\n[1/3] 精简电商视图 (id=6) ...")
    service.update_transform(6, {"transform_sql": ECOMMERCE_SQL})
    print("  ✅ SQL 已更新")
    result = service.execute_transform(6)
    print(f"  执行: {result}")

    # 2. 商用视图
    print("\n[2/3] 修正商用视图 (id=8) ...")
    service.update_transform(8, {"transform_sql": COMMERCIAL_SQL})
    print("  ✅ SQL 已更新")
    result = service.execute_transform(8)
    print(f"  执行: {result}")

    # 3. 消费者视图
    print("\n[3/3] 修正消费者视图 (id=9) ...")
    service.update_transform(9, {"transform_sql": CONSUMER_SQL})
    print("  ✅ SQL 已更新")
    result = service.execute_transform(9)
    print(f"  执行: {result}")

    # 4. 验证列数
    print("\n[4/4] 验证三视图列结构 ...")
    for tid, name in [(6, "电商"), (8, "商用"), (9, "消费者")]:
        info = service.get_transform(tid)
        if info:
            print(f"  {name} (id={tid}): {info.get('target_name')}")

    print("\n✅ 迁移完成！")


if __name__ == "__main__":
    migrate()
