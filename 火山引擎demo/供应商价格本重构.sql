CREATE TABLE meiju.ods_nebula_t_purchase_order_material (
    id bigint NOT NULL, -- 主键id
    business_id bigint, -- 采购订单主键id
    order_material_list_code character varying(100), -- 采购单材料列表编码 （材料id_施工）
    sku_id bigint, -- 拆包材料id
    sku_type_code character varying(32) DEFAULT ''::character varying, -- 材料sku类型编码: MAIN_MATERIAL：主材；MINOR_MATERIAL：辅材；SERVICE：服务；LABOR：人工；
    auxiliary_flag smallint DEFAULT 0::smallint, -- 自选辅材商品标识：1，是；0，否；2，自选服务费
    supplier_id bigint, -- 材料库供应商id
    purchase_num numeric(16,6), -- 采购数量
    purchase_unit character varying(10) DEFAULT ''::character varying, -- 采购单位
    prices numeric(16,2), -- 采购单价（元）
    service_rate numeric(16,6) DEFAULT 0.000000, -- 供应商服务费率
    vat_amount_due numeric(16,6) DEFAULT 0.000000, -- 应结增值税总金额
    additional_tax_amount_due numeric(16,6) DEFAULT 0.000000, -- 应结附加税总金额
    amount numeric(16,6), -- 采购金额（元） = 采购数量*采购单价
    plan_settle_num numeric(16,6) DEFAULT 0.000000, -- 计划采购数量:初始等于采购数量
    ori_total_amount numeric(16,6) DEFAULT 0.000000, -- 原始采购总额
    real_settle_num numeric(16,6) DEFAULT 0.000000, -- 应结算采购量：收货数量-退货数量
    material_total_amount_due numeric(16,6) DEFAULT 0.000000, -- 应结材料采购总金额
    take_over_num numeric(16,6) DEFAULT 0.000000, -- 收货数量：明细行，验收时记录的收货数量
    return_num numeric(16,6) DEFAULT 0.000000, -- 退货数量：明细行，退货时记录的退货数量
    total_return_amount numeric(16,6) DEFAULT 0.000000, -- 退货总金额 退货数量*采购单价 
    concentrate_price numeric(16,2), -- 集采采购单价
    concentrate_amount numeric(16,2), -- 集采采购金额（元） = （采购数量*非采购单价）+（采购数量*集采采购单价）
    deliver_time timestamp without time zone, -- 材料到场时间
    status smallint, -- 发货状态；0：未发货；1：已发货；2：已验收
    remark character varying(1000) DEFAULT ''::character varying, -- 备注
    remark_imgs text, -- 备注图片url
    send_attachments text, -- 发货单附件
    return_attachments text, -- 退货附件
    reason character varying(100), -- 材料驳回原因
    snapshot_json text, -- 采购单创建时的材料快照信息
    cost_no character varying(50) DEFAULT ''::character varying, -- 材料推成本关联的流水号
    yecai_status smallint DEFAULT 0::smallint, -- 成本推送业财状态，0=未推送，1已推送，2撤回
    document_no character varying(32) DEFAULT ''::character varying, -- 材料推成本，成本推业财成功后成本的单据号
    construction_phase character varying(32) DEFAULT ''::character varying, -- 材料施工阶段
    version integer DEFAULT 1, -- 版本号
    deleted smallint DEFAULT 0::smallint, -- 是否已删除 1：已删除 0：未删除
    creator character varying(50), -- 创建人
    created_time timestamp without time zone, -- 创建时间
    updator character varying(50), -- 更新人
    updated_time timestamp with time zone DEFAULT now(), -- 更新时间
    contract_price numeric(16,6) DEFAULT 0, -- 材料承包单价
    total_contract_price numeric(16,6) DEFAULT 0, -- 采购材料承包价总额（承包单价*采购数量）
    install_status smallint,
    install_attachments text,
    takeover_time timestamp without time zone,
    takeover_source smallint,
    takeover_status smallint,
    package_id smallint,
    need_shipment bit(1),
    logistics_company_code character varying(32),
    logistics_company_name character varying(255),
    shipment_number character varying(32),
    installation_type character varying(32),
    pay_amount_no_tax numeric(16,6) DEFAULT 0.000000,
    material_supplier_id bigint,
    relate_ship_code character varying(100),
    procurement_price numeric(16,2),
    new_purchase_type smallint DEFAULT 0,
    msg_status character varying(8) DEFAULT '0'::character varying
);
COMMENT ON TABLE meiju.ods_nebula_t_purchase_order_material IS '采购订单材料清单表';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.id IS '主键id';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.business_id IS '采购订单主键id';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.order_material_list_code IS '采购单材料列表编码 （材料id_施工）';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.sku_id IS '拆包材料id';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.sku_type_code IS '材料sku类型编码: MAIN_MATERIAL：主材；MINOR_MATERIAL：辅材；SERVICE：服务；LABOR：人工；';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.auxiliary_flag IS '自选辅材商品标识：1，是；0，否；2，自选服务费';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.supplier_id IS '材料库供应商id';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.purchase_num IS '采购数量';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.purchase_unit IS '采购单位';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.prices IS '采购单价（元）';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.service_rate IS '供应商服务费率';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.vat_amount_due IS '应结增值税总金额';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.additional_tax_amount_due IS '应结附加税总金额';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.amount IS '采购金额（元） = 采购数量*采购单价';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.plan_settle_num IS '计划采购数量:初始等于采购数量';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.ori_total_amount IS '原始采购总额';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.real_settle_num IS '应结算采购量：收货数量-退货数量';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.material_total_amount_due IS '应结材料采购总金额';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.take_over_num IS '收货数量：明细行，验收时记录的收货数量';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.return_num IS '退货数量：明细行，退货时记录的退货数量';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.total_return_amount IS '退货总金额 退货数量*采购单价 ';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.concentrate_price IS '集采采购单价';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.concentrate_amount IS '集采采购金额（元） = （采购数量*非采购单价）+（采购数量*集采采购单价）';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.deliver_time IS '材料到场时间';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.status IS '发货状态；0：未发货；1：已发货；2：已验收';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.remark IS '备注';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.remark_imgs IS '备注图片url';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.send_attachments IS '发货单附件';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.return_attachments IS '退货附件';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.reason IS '材料驳回原因';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.snapshot_json IS '采购单创建时的材料快照信息';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.cost_no IS '材料推成本关联的流水号';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.yecai_status IS '成本推送业财状态，0=未推送，1已推送，2撤回';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.document_no IS '材料推成本，成本推业财成功后成本的单据号';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.construction_phase IS '材料施工阶段';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.version IS '版本号';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.deleted IS '是否已删除 1：已删除 0：未删除';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.creator IS '创建人';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.created_time IS '创建时间';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.updator IS '更新人';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.updated_time IS '更新时间';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.contract_price IS '材料承包单价';
COMMENT ON COLUMN meiju.ods_nebula_t_purchase_order_material.total_contract_price IS '采购材料承包价总额（承包单价*采购数量）';



-- ============================================================================
-- 采购订单表查询
-- 功能说明：查询集采供应商稽查相关的采购订单数据，排除草稿、待接单、驳回、待审核状态
-- 数据来源：meiju.ods_nebula_t_purchase_order
-- ============================================================================

SELECT
    -- 基础信息
    id AS "采购订单编号(主键)",
    business_code AS "业务编码(订单号)",
    contract_id AS "面客装修主合同号",
    customer_name AS "客户姓名",
    customer_mobile AS "客户手机号",
    house_address AS "客户地址",
    
    -- 单据类型与创建方式
    tab_type AS "单据类型(RENOVATION=装修采购单;PLATFORM=精装微改采购单)",
    type AS "单据创建方式(PUBLISH=拆包推送材料申领单;MANUAL=自建采购;LABOR=工费申领单)",
    publish_id AS "来源申请单据编码",
    
    -- 归属组织信息
    belong_org_code AS "归属组织编码",
    belong_org_name AS "归属组织名称",
    
    -- 采购类型信息
    purchase_actual_type AS "实际采购类型(MATERIAL=材料;LABOR=工费;CAPTAIN=超级队长提成;PLATFORM=精装微改)",
    purchase_type AS "采购入库方式(HOME=入户;WAREHOUSE=入仓)",
    purchase_method AS "采购方式(SALES=销采;BATCH=批采)",
    
    -- 金额信息
    amount_total AS "采购总金额",
    concentrate_amount_total AS "集采采购金额",
    value_added_tax AS "增值税",
    additional_tax AS "附加税",
    
    -- 采购方信息
    purchase_city_code AS "采购方编码",
    purchase_city_name AS "采购方名称",
    
    -- 供应商信息
    supplier_id AS "材料库供应商ID",
    supplier_name AS "供应商名称",
    
    -- 状态信息
    status AS "采购单据状态(1=草稿;2=待供应商接单;3=供应商已接单;4=单据关闭-供应商驳回;5=供应商已发货;6=供应商已验收;7=单据关闭-完成结算;8=待审核)",
    reconcile_status AS "对账状态(0=待对账;1=已对账)",
    settle_status AS "结算状态(0=未结算;1=已结算)",
    order_remark AS "订单异常标记(0=正常;1=异常)",
    
    -- 时间信息
    start_time AS "采购发起时间",
    price_date AS "采购价格明确提交时间",
    created_time AS "创建时间",
    updated_time AS "更新时间",
    
    -- 联系人信息
    laborer_mobile AS "工长手机号",
    laborer_name AS "工长姓名",
    contact_mobile AS "联系人手机号",
    contact_name AS "联系人姓名",
    
    -- 工费信息
    labor_info AS "工费信息JSON串",
    labor_info_urls AS "工费信息凭证URL",
    server_info AS "供应商服务费用信息",
    
    -- 发票与结算信息
    total_contract_amount AS "总承包价总额",
    invoice_include_tax_amount AS "发票含税总金额折算额",
    invoice_exclude_tax_amount AS "发票不含税总金额折算额",
    pay_invoices_tax_rate AS "付款发票税率",
    
    -- 发货信息
    delivery_note AS "发货单",
    delivery_note_url AS "发货单附件合并外链",
    delivery_address AS "送货地址",
    
    -- 税务与公司信息
    company_name AS "公司名称",
    taxer_id_number AS "纳税人识别号",
    is_concentrate AS "是否含集采材料(1=是;0=否)",
    
    -- 其他信息
    reason AS "供应商接单驳回原因",
    remarks AS "采购订单备注",
    order_info AS "订单信息",
    audit_info AS "审核信息",
    instance_code AS "流程实例编码",
    source_order_type AS "来源订单类型",
    
    -- 系统字段
    deleted AS "是否删除(1=已删除;0=未删除)",
    creator AS "创建人",
    updator AS "更新人"
FROM meiju.ods_nebula_t_purchase_order

-- 过滤条件
WHERE status NOT IN (1, 2, 4, 8)  -- 排除草稿、待供应商接单、供应商驳回、待审核状态
  AND deleted = 0                   -- 仅查询未删除的订单
  -- AND is_concentrate = 1            -- 仅查询包含集采材料的订单
  AND order_remark = 0              -- 仅查询正常的订单(排除异常订单)
AND id ='83768'
LIMIT 100;  -- 限制返回100条记录

采购订单编号(主键)	业务编码(订单号)	面客装修主合同号	客户姓名	客户手机号	客户地址	单据类型(RENOVATION=装修采购单;PLATFORM=精装微改	单据创建方式(PUBLISH=拆包推送材料申领单;MANUAL=	来源申请单据编码	归属组织编码	归属组织名称	实际采购类型(MATERIAL=材料;LABOR=工费;CAPTAIN=超级	采购入库方式(HOME=入户;WAREHOUSE=入仓)	采购方式(SALES=销采;BATCH=批采)	采购总金额	集采采购金额	增值税	附加税	采购方编码	采购方名称	材料库供应商ID	供应商名称	采购单据状态(1=草稿;2=待供应商接单;3=供应商已	对账状态(0=待对账;1=已对账)	结算状态(0=未结算;1=已结算)	订单异常标记(0=正常;1=异常)	采购发起时间	采购价格明确提交时间	创建时间	更新时间	工长手机号	工长姓名	联系人手机号	联系人姓名	工费信息JSON串	工费信息凭证URL	供应商服务费用信息	总承包价总额	发票含税总金额折算额	发票不含税总金额折算额	付款发票税率	发货单	发货单附件合并外链	送货地址	公司名称	纳税人识别号	是否含集采材料(1=是;0=否)	供应商接单驳回原因	采购订单备注	订单信息	审核信息	流程实例编码	来源订单类型	是否删除(1=已删除;0=未删除)	创建人	更新人
83768	4251220625037780111724544	4005375324963144712	杨东立	13927724877	广东省佛山市南海区桂城街道佛山金色家园金虹一座1单元603	RENOVATION	MANUAL		CT00010288	佛山金湾服务站	MATERIAL	HOME	SALES	1528.00	1528.00			2289	深圳市万物研选科技服务有限公司佛山分公司	3378	佛山市创粤建材有限公司	7	1	1	0	2025-12-31 18:02:10		2025-12-31 18:02:10	2026-02-16 00:00:58+08	13106712514	谢兆锟	13106712514	谢兆锟				0.000000	1528.00	1352.21	0.130000	[{"name":"万物研选26年1月份对账_2.pdf","url":"https://yxcos.onewo.com/2026/01/30/9ed603f9-4f04-430d-b96b-43cad0cb98ea.pdf"}]	https://yxcos.onewo.com/2026/1/30/8c835df909884062a9d4c2aa18dc1b9d.zip	广东省佛山市南海区桂城街道佛山金色家园金虹一座1单元603	深圳市万物研选科技服务有限公司佛山分公司	91440604MABPQF0L4H	0						0	0	21683461	

-- ============================================================================
-- 【正式执行块】一键运行：建临时表 → 主查询 → 清理临时表
-- 使用说明：全选本块（从 DROP 到最后一行 DROP）一起执行
-- ============================================================================

-- Step 0: 清理可能已存在的临时表（避免重复执行报错）
DROP TABLE IF EXISTS temp_dealer_list;

-- Step 1: 创建经销商临时表，前置 COALESCE 确定匹配基准名称
-- 优先用"属地确认的供应商"(COL_9)，为空时退用"战略供应商清单"(COL_4)
CREATE TEMP TABLE temp_dealer_list AS
SELECT
    "COL_1" AS 品牌,
    "COL_2" AS 区域,
    "COL_3" AS 城市,
    TRIM("COL_4") AS 战略供应商清单, 
    "COL_5" AS 联系人,
    "COL_6" AS 联系电话,
    "COL_7" AS 自营装修业务城市,
    "COL_8" AS 供应商ID,
    TRIM("COL_9") AS 属地确认的供应商,
    "COL_10" AS 引入方,
    COALESCE(NULLIF(TRIM("COL_9"), ''), TRIM("COL_4")) AS 匹配基准供应商
FROM public.qbi_file_20260423_10_49_26_0;

-- Step 2: 主查询
-- ============================================================================
-- 【供应商价格本稽查 + 采购订单统计】（修正版 v2）
-- 
-- 需求：拿人工Excel供应商清单，按"供应商+城市"为维度：
--   1. 用供应商名 → ods_diana_t_supplier → 拿到 supplier_id
--   2. 用 supplier_id → ods_diana_t_price_book（价格本主表）→ 判断是否有价格本
--   3. 用 book_code → ods_diana_t_price_book_detail → 拿到价格本中的 sku_id 列表
--   4. 用价格本中的 sku_id → ods_nebula_t_purchase_order_material → 找到用了这些SKU的材料行
--   5. 用材料行的 business_id → ods_nebula_t_purchase_order → 找到对应的采购订单
--   6. 用采购订单的 business_code → 研选订单表 → 拿到城市
--   7. 按"供应商+城市"聚合统计订单数和金额
--
-- ⚠️ 核心修正：之前错误地用 supplier_id 直接关联采购订单
--   正确路径是：价格本明细 sku_id → 材料清单 sku_id → business_id → 采购订单
--   这样才能知道"价格本里的材料在实际采购中被用了多少"
--
-- ⚠️ 关键点：同一个供应商在多个城市都有业务，必须用城市区分
-- ============================================================================

WITH 

-- ────────────────────────────────────────────────────────────────────────────
-- 第①步：人工清单 匹配 供应商主数据，拿到 supplier_id
-- ────────────────────────────────────────────────────────────────────────────
supplier_match AS (
    SELECT 
        dl.匹配基准供应商,                  -- 最终用来匹配的供应商名
        dl.品牌,
        dl.区域,
        dl.城市       AS 清单城市,          -- 人工清单的城市（关键维度！）
        s.id          AS supplier_id,       -- 系统供应商ID
        s.company_name AS 供应商名称        -- 系统中的公司名
    FROM temp_dealer_list dl
    LEFT JOIN meiju.ods_diana_t_supplier s 
        ON s.company_name = dl.匹配基准供应商
        AND s.deleted = 0
),

-- ────────────────────────────────────────────────────────────────────────────
-- 第②步：查价格本主表，判断该供应商是否有价格本
-- 说明：ods_diana_t_price_book 是价格本主表
--       status: 0=未生效, 1=启用, 2=停用
-- ────────────────────────────────────────────────────────────────────────────
price_book_summary AS (
    SELECT 
        pb.supplier_id,
        COUNT(*)                                                    AS 价格本总数,
        COUNT(CASE WHEN pb.status = 1 THEN 1 END)                  AS 启用价格本数,
        STRING_AGG(DISTINCT pb.book_code, ', ')                     AS 价格本编码列表,
        STRING_AGG(DISTINCT CASE WHEN pb.status = 1 THEN pb.book_code END, ', ') AS 启用价格本编码
    FROM meiju.ods_diana_t_price_book pb
    WHERE pb.deleted = 0
    GROUP BY pb.supplier_id
),

-- ────────────────────────────────────────────────────────────────────────────
-- 第③步：价格本明细 — 拿到每个供应商价格本中的所有 sku_id
-- 说明：这是核心关联桥梁！
--       supplier_id → price_book(book_code) → price_book_detail(sku_id)
--       拿到的 sku_id 是"该供应商价格本里登记的材料"
-- ────────────────────────────────────────────────────────────────────────────
supplier_pricebook_skus AS (
    SELECT 
        pb.supplier_id,
        pbd.sku_id,
        pbd.purchase_price AS 价格本采购价,     -- 价格本中登记的采购价
        pbd.book_code,
        COUNT(DISTINCT pbd.sku_id) OVER (PARTITION BY pb.supplier_id) AS 该供应商价格本SKU总数
    FROM meiju.ods_diana_t_price_book pb
    INNER JOIN meiju.ods_diana_t_price_book_detail pbd 
        ON pbd.book_code = pb.book_code         -- 通过价格本编码关联明细
        AND pbd.deleted = 0 
        AND pbd.status = 0                       -- 正常（非作废）
    WHERE pb.deleted = 0 
      AND pb.status = 1                          -- 只看启用的价格本
),

-- ────────────────────────────────────────────────────────────────────────────
-- 第④步：用价格本的 sku_id → 采购订单材料清单 → 找到 business_id（采购订单主键）
-- 说明：这是关键！从价格本的 sku_id 出发，去材料清单表中找
--       哪些采购订单用了这些材料（通过 sku_id 匹配）
--       材料清单表中的 business_id 就是 采购订单表的 id（主键）
-- ────────────────────────────────────────────────────────────────────────────
sku_order_material AS (
    SELECT 
        sps.supplier_id,                         -- 供应商ID（来自价格本）
        sps.sku_id,                              -- 价格本中的材料SKU
        sps.价格本采购价,
        m.business_id,                           -- 采购订单主键（→ 关联采购订单表）
        m.prices        AS 实际采购单价,         -- 材料清单中的实际采购价
        m.amount        AS 材料采购金额,         -- 该行的采购金额
        m.purchase_num  AS 采购数量,
        m.id            AS material_id
    FROM supplier_pricebook_skus sps
    INNER JOIN meiju.ods_nebula_t_purchase_order_material m
        ON m.sku_id = sps.sku_id                 -- ⭐ 核心关联：价格本SKU = 材料清单SKU
        AND m.deleted = 0                         -- 未删除
),

-- ────────────────────────────────────────────────────────────────────────────
-- 第⑤步：通过 business_id 找到采购订单，并过滤有效状态
-- 说明：material的 business_id = 采购订单的 id
--       这里同时获取 business_code（订单号）用来下一步查城市
-- ────────────────────────────────────────────────────────────────────────────
sku_order_valid AS (
    SELECT 
        som.*,
        po.business_code,                        -- 业务编码/订单号（用于查城市）
        po.amount_total  AS 订单总金额           -- 整张订单的总金额
    FROM sku_order_material som
    INNER JOIN meiju.ods_nebula_t_purchase_order po
        ON po.id = som.business_id               -- business_id = 采购订单主键
        AND po.status NOT IN (1, 2, 4, 8)        -- 排除：草稿/待接单/驳回/待审核
        AND po.deleted = 0
        AND po.order_remark = 0                   -- 正常订单
        AND po.created_time >= '2026-01-01 00:00:00'  -- 只统计2026年的订单
        AND po.created_time <  '2027-01-01 00:00:00'  -- 不含2027年
),

-- ────────────────────────────────────────────────────────────────────────────
-- 第⑥步：用 business_code 查订单所在城市
-- 说明：采购订单本身没有"城市"字段，需要用订单号
--       去研选的平台订单/装修订单表里查
-- ────────────────────────────────────────────────────────────────────────────
city_lookup AS (
    SELECT DISTINCT order_code, city_name AS 城市
    FROM (
        SELECT order_code, city_name
        FROM yanxuan.dwd_platform_order_detail 
        WHERE is_test = '否'
        UNION ALL
        SELECT order_code, city_name
        FROM yanxuan.dwd_decoration_order_detail 
        WHERE is_refund_order = '否' AND is_test = '否'
    ) sub
),

-- ────────────────────────────────────────────────────────────────────────────
-- 第⑦步：给每条记录打上城市标签
-- ────────────────────────────────────────────────────────────────────────────
sku_order_with_city AS (
    SELECT 
        sov.*,
        cl.城市 AS 订单城市
    FROM sku_order_valid sov
    LEFT JOIN city_lookup cl ON cl.order_code = sov.business_code
),

-- ────────────────────────────────────────────────────────────────────────────
-- 第⑧步：按"供应商+城市"聚合统计
-- 说明：⚠️ 关键过滤 sm.清单城市 = soc.订单城市，确保只统计该城市的订单
--       这里从人工清单出发 LEFT JOIN，保证每个清单行都出现在结果中
-- ────────────────────────────────────────────────────────────────────────────
order_stats AS (
    SELECT
        sm.匹配基准供应商,
        sm.品牌,
        sm.区域,
        sm.清单城市,
        sm.supplier_id,
        sm.供应商名称,
        -- 采购订单维度（去重统计，因为一张订单有多个材料行）
        COUNT(DISTINCT soc.business_id)                   AS 采购订单数,
        COALESCE(SUM(DISTINCT soc.订单总金额), 0)         AS 订单总金额,
        -- 材料明细维度
        COUNT(soc.material_id)                            AS 材料行数,
        COALESCE(SUM(soc.材料采购金额), 0)                AS 材料采购总金额,
        COUNT(DISTINCT soc.sku_id)                        AS 实际采购的价格本SKU数
    FROM supplier_match sm
    LEFT JOIN sku_order_with_city soc 
        ON soc.supplier_id = sm.supplier_id
        AND sm.清单城市 = soc.订单城市               -- ⚠️ 只匹配同城市的订单
    GROUP BY 
        sm.匹配基准供应商, sm.品牌, sm.区域, sm.清单城市,
        sm.supplier_id, sm.供应商名称
)

-- ============================================================================
-- 最终输出：每行 = 一个"供应商+城市"组合
-- ============================================================================
SELECT 
    -- ◆ 人工清单信息
    os.品牌,
    os.区域,
    os.清单城市                               AS 城市,
    os.匹配基准供应商                         AS 供应商名称,

    -- ◆ 系统匹配
    os.supplier_id                            AS 系统供应商ID,
    CASE WHEN os.supplier_id IS NOT NULL 
         THEN '是' ELSE '否' 
    END                                       AS 是否匹配到系统供应商,

    -- ◆ 价格本情况（来自价格本主表 ods_diana_t_price_book）
    CASE 
        WHEN os.supplier_id IS NULL THEN '供应商未匹配'
        WHEN pbs.supplier_id IS NULL THEN '否'           -- 价格本主表中没有该供应商
        WHEN pbs.启用价格本数 > 0 THEN '是(启用)'        -- 有启用的价格本
        ELSE '是(未启用)'                                 -- 有价格本但未启用
    END                                       AS 是否在价格本中,
    COALESCE(pbs.价格本总数, 0)               AS 价格本总数,
    COALESCE(pbs.启用价格本数, 0)             AS 启用价格本数,
    pbs.启用价格本编码                        AS 启用价格本编码,

    -- ◆ 价格本SKU vs 实际采购SKU
    COALESCE((SELECT MAX(该供应商价格本SKU总数) 
              FROM supplier_pricebook_skus x 
              WHERE x.supplier_id = os.supplier_id), 0)
                                              AS 价格本中SKU种类数,  -- 价格本里登记了多少种SKU
    os.实际采购的价格本SKU数                  AS 该城市实际采购的SKU数, -- 这些SKU中在该城市有多少被实际采购了

    -- ◆ 采购订单统计（该城市下，只统计用了价格本SKU的订单）
    os.采购订单数                             AS 该城市采购订单数,
    os.订单总金额                             AS 该城市订单总金额,
    os.材料行数                               AS 该城市材料明细行数,
    os.材料采购总金额                         AS 该城市材料采购总金额

FROM order_stats os

-- 关联价格本主表汇总
LEFT JOIN price_book_summary pbs 
    ON pbs.supplier_id = os.supplier_id

ORDER BY 
    os.品牌,
    os.区域,
    os.清单城市,
    os.匹配基准供应商;

-- Step 3: 清理临时表（执行完毕后释放资源）
DROP TABLE IF EXISTS temp_dealer_list;