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



SELECT 
    id AS 主键ID,
    business_id AS 业务ID,
    order_material_list_code AS 订单材料清单编码,
    sku_id AS SKU_ID,
    sku_type_code AS SKU类型编码,
    auxiliary_flag AS 辅材标识,
    supplier_id AS 供应商ID,
    purchase_num AS 采购数量,
    purchase_unit AS 采购单位,
    prices AS 单价,
    service_rate AS 服务费率,
    vat_amount_due AS 应交增值税额,
    additional_tax_amount_due AS 应交附加税额,
    amount AS 金额,
    plan_settle_num AS 计划结算数量,
    ori_total_amount AS 原始总金额,
    real_settle_num AS 实际结算数量,
    material_total_amount_due AS 应交材料总金额,
    take_over_num AS 接收数量,
    return_num AS 退货数量,
    total_return_amount AS 总退货金额,
    concentrate_price AS 集中采购价,
    concentrate_amount AS 集中采购金额,
    deliver_time AS 交付时间,
    status AS 状态,
    remark AS 备注,
    remark_imgs AS 备注图片,
    send_attachments AS 发送附件,
    return_attachments AS 退货附件,
    reason AS 原因,
    snapshot_json AS 快照JSON,
    cost_no AS 成本编号,
    yecai_status AS 野菜状态,
    document_no AS 单据编号,
    construction_phase AS 施工阶段,
    version AS 版本,
    deleted AS 是否删除,
    creator AS 创建人,
    created_time AS 创建时间,
    updator AS 更新人,
    updated_time AS 更新时间,
    contract_price AS 合同价格,
    total_contract_price AS 合同总价,
    install_status AS 安装状态,
    install_attachments AS 安装附件,
    takeover_time AS 接收时间,
    takeover_source AS 接收来源,
    takeover_status AS 接收状态,
    package_id AS 包裹ID,
    need_shipment AS 是否需要发货,
    logistics_company_code AS 物流公司编码,
    logistics_company_name AS 物流公司名称,
    shipment_number AS 运单号,
    installation_type AS 安装类型,
    pay_amount_no_tax AS 不含税支付金额,
    material_supplier_id AS 材料供应商ID,
    relate_ship_code AS 关联发货编码,
    procurement_price AS 采购价格,
    new_purchase_type AS 新采购类型,
    msg_status AS 消息状态
FROM meiju.ods_nebula_t_purchase_order_material
WHERE deleted =  '0' AND
sku_type_code in (MAIN_MATERIAL：主材；SERVICE：服务；)
 AND 
   created_time >='2026-01-01 00:00:00'
   AND created_time <'2026-04-01 00:00:00'
business_id = '83768'
主键id	业务id	订单材料清单编码	sku_id	sku类型编码	辅材标识	供应商id	采购数量	采购单位	单价	服务费率	应交增值税额	应交附加税额	金额	计划结算数量	原始总金额	实际结算数量	应交材料总金额	接收数量	退货数量	总退货金额	集中采购价	集中采购金额	交付时间	状态	备注	备注图片	发送附件	退货附件	原因	快照json	成本编号	野菜状态	单据编号	施工阶段	版本	是否删除	创建人	创建时间	更新人	更新时间	合同价格	合同总价	安装状态	安装附件	接收时间	接收来源	接收状态	包裹id	是否需要发货	物流公司编码	物流公司名称	运单号	安装类型	不含税支付金额	材料供应商id	关联发货编码	采购价格	新采购类型	消息状态
421502	83768	POM00004FQK	21723	MAIN_MATERIAL	0	3378	80.000000	片	16.60	0.000000	0.000000	0.000000	1328.000000	80.000000	1328.000000	80.000000	1328.000000	80.000000	0.000000	0.000000	0.00	0.00	2025-12-31 00:00:00	2			[{"name":"微信图片_2026-01-27_145702_809.jpg","url":"https://yxcos.onewo.com/2026/01/27/5c55e52f-da14-4e45-b0df-fbace753c064.jpg"},{"name":"微信图片_2026-01-27_145700_608.jpg","url":"https://yxcos.onewo.com/2026/01/27/8bacb677-2149-401c-b180-34ce2256a774.jpg"},{"name":"微信图片_2026-01-27_145656_842.jpg","url":"https://yxcos.onewo.com/2026/01/27/66f85ef5-5a76-4b0f-bd84-007082fb66f5.jpg"}]			{"brandName":"蒙娜丽莎","categoryId":9,"categoryPath":"瓷砖>墙砖>墙砖400×800mm","companyOrgCode":"2289","companyOrgName":"深圳市万物研选科技服务有限公司佛山分公司","contractPrice":0.00,"corporateEntityInfoVO":{"cityCompanyCode":"2289","cityCompanyName":"深圳市万物研选科技服务有限公司佛山分公司","companyName":"深圳市万物研选科技服务有限公司佛山分公司","taxRate":"null","taxerIdNumber":"91440604MABPQF0L4H"},"deliveryFee":0.00,"description":"400*800mm，釉面砖","installationType":"无需安装","materialSupplierId":3378,"materialSupplierName":"佛山市创粤建材有限公司","model":"墙砖【40-80FKB07002PM-蒙娜丽莎】","newPurchaseType":0,"procureRemark":"","purchasePrice":16.60,"purchasePriceList":[],"purchasingUnit":"片","sellAreas":[{"concentratePrice":"0","id":21723,"purchasePrice":"16.6","pushStatus":1,"relatedContractStatus":false,"salesStatus":1,"sellableArea":"全国"}],"skuAttr":"-","skuCode":"12921723","skuId":21723,"skuName":"墙砖400×800mm/-","skuType":"主材","skuTypeCode":"MAIN_MATERIAL","supplier":{"businessLicenseNo":"91440604MABPQF0L4H","generalTaxpayer":true,"id":2289,"isGeneralTaxpayer":1,"taxCalculationMethod":0,"taxPayerType":1},"supplierId":3378,"supplierInvoicingType":"专票","supplierName":"佛山市创粤建材有限公司","supplierQyOrgCode":"CT00010092,CT00010088","taxRate":"13%"}	M1260127638754288935587841	1	ZY2601275408929121		2	0	21683461	2026-01-27 15:01:29		2026-02-16 00:00:58+08	0.000000	0.000000	0					2	false				无需安装	1176.430000	3378	MLC00000PR4	16.60	0	0
421501	83768	POM00004FQJ	11690	MAIN_MATERIAL	0	3378	1.000000	次	200.00	0.000000	0.000000	0.000000	200.000000	1.000000	200.000000	1.000000	200.000000	1.000000	0.000000	0.000000	0.00	0.00	2025-12-31 00:00:00	2			[{"name":"微信图片_2026-01-27_145702_809.jpg","url":"https://yxcos.onewo.com/2026/01/27/5c55e52f-da14-4e45-b0df-fbace753c064.jpg"},{"name":"微信图片_2026-01-27_145700_608.jpg","url":"https://yxcos.onewo.com/2026/01/27/8bacb677-2149-401c-b180-34ce2256a774.jpg"},{"name":"微信图片_2026-01-27_145656_842.jpg","url":"https://yxcos.onewo.com/2026/01/27/66f85ef5-5a76-4b0f-bd84-007082fb66f5.jpg"}]			{"brandName":"蒙娜丽莎","categoryId":33,"categoryPath":"瓷砖>瓷砖服务费>瓷砖服务费","companyOrgCode":"2289","companyOrgName":"深圳市万物研选科技服务有限公司佛山分公司","contractPrice":0.00,"contractPriceVO":[{"contractId":38179,"purchasePriceList":[200]}],"corporateEntityInfoVO":{"cityCompanyCode":"2289","cityCompanyName":"深圳市万物研选科技服务有限公司佛山分公司","companyName":"深圳市万物研选科技服务有限公司佛山分公司","taxRate":"null","taxerIdNumber":"91440604MABPQF0L4H"},"deliveryFee":0.00,"description":"","installationType":"无需安装","materialSupplierId":3378,"materialSupplierName":"佛山市创粤建材有限公司","model":"瓷砖服务费【小单费-蒙娜丽莎】","newPurchaseType":0,"procureRemark":"","purchasePrice":200.00,"purchasePriceList":[],"purchasingUnit":"次","sellAreas":[{"concentratePrice":"0","id":11690,"purchasePrice":"200","pushStatus":1,"relatedContractStatus":false,"salesStatus":1,"sellableArea":"全国"}],"skuAttr":"小单费","skuCode":"153311690","skuId":11690,"skuName":"瓷砖服务费/小单费","skuType":"主材","skuTypeCode":"MAIN_MATERIAL","supplier":{"businessLicenseNo":"91440604MABPQF0L4H","generalTaxpayer":true,"id":2289,"isGeneralTaxpayer":1,"taxCalculationMethod":0,"taxPayerType":1},"supplierId":3378,"supplierInvoicingType":"专票","supplierName":"佛山市创粤建材有限公司","supplierQyOrgCode":"CT00010092,CT00010088","taxRate":"13%"}	M1260127638754288935587840	1	ZY2601275408928757		2	0	21683461	2026-01-27 15:01:29		2026-02-16 00:00:58+08	0.000000	0.000000	0					2	false				无需安装	175.780000	3378	MLC00000PR3	200.00	0	0


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

-- 第三步：创建经销商临时表 (【重点修改】：前置 Coalesce)
-- ------------------------------------------------------------
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
    -- 【新增】：在这里直接确定最终要拿去匹配的名称
    COALESCE(NULLIF(TRIM("COL_9"), ''), TRIM("COL_4")) AS 匹配基准供应商
FROM public.qbi_file_20260423_10_49_26_0;



SELECT 
    order_code, 
    order_status,
    city_name AS 城市,
    '平台订单' AS 数据来源
FROM 
    yanxuan.dwd_platform_order_detail 
WHERE 
    is_test = '否' 
    AND order_code = '4251220625037780111724544'
    -- AND customer_mobile IN (
    --     '15005598961',
    --     '18256973868',
    --     '17671099701',
    --     '18715004517',
    --     '15856953151',
    --     '18119512842',
    --     '15055105463',
    --     '18755138753'
    -- )

UNION ALL

SELECT 
    order_code, 
    furnish_order_status,
    city_name AS 城市,
    '装修订单' AS 数据来源
FROM 
    yanxuan.dwd_decoration_order_detail 
WHERE 
    -- furnish_type != '维修' 
    -- AND 
    is_refund_order = '否' 
    AND is_test = '否' 
   AND order_code = '4251220625037780111724544'
    -- AND customer_mobile IN (
    --     '15005598961',
    --     '18256973868',
    --     '17671099701',
    --     '18715004517',
    --     '15856953151',
    --     '18119512842',
    --     '15055105463',
    --     '18755138753'
    -- )


CREATE TABLE meiju.ods_diana_t_price_book_detail (
    id bigint NOT NULL,
    book_code character varying(64) DEFAULT ''::character varying, -- 价格本编码
    book_detail_code bigint DEFAULT 1::bigint, -- 价格本明细id(存量的材料数据这里存的是材料id)
    sku_id bigint DEFAULT 0::bigint, -- 关联材料id
    sku_code character varying(64) DEFAULT ''::character varying, -- 编码(这里字段只是为了兼容之前的材料中的)
    purchase_price numeric(12,2), -- 采购价
    supplier_invoicing_type smallint DEFAULT 0::smallint, -- 供应商开票类型：0=普票,1=专票
    supplier_invoicing_tax_rate numeric(10,2) DEFAULT 0.00, -- 供应商开票税率, 这里存的单位是百分比
    arrive_day bigint DEFAULT 0::bigint, -- 到货时间
    status integer DEFAULT 0, -- 状态(0=正常,1=作废)
    creator character varying(50) DEFAULT ''::character varying, -- 创建人
    created_time timestamp without time zone DEFAULT now(), -- 创建时间
    updator character varying(50) DEFAULT ''::character varying, -- 创建人
    updated_time timestamp with time zone DEFAULT now(), -- 更新时间
    deleted integer DEFAULT 0, -- 是否已删除 1：已删除 0：未删除
    delivery_fee numeric(12,2) DEFAULT 0.00, -- 配送费
    purchasing_unit character varying(50) -- 采购单位
);
COMMENT ON TABLE meiju.ods_diana_t_price_book_detail IS '采购价格本明细表';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.book_code IS '价格本编码';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.book_detail_code IS '价格本明细id(存量的材料数据这里存的是材料id)';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.sku_id IS '关联材料id';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.sku_code IS '编码(这里字段只是为了兼容之前的材料中的)';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.purchase_price IS '采购价';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.supplier_invoicing_type IS '供应商开票类型：0=普票,1=专票';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.supplier_invoicing_tax_rate IS '供应商开票税率, 这里存的单位是百分比';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.arrive_day IS '到货时间';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.status IS '状态(0=正常,1=作废)';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.creator IS '创建人';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.created_time IS '创建时间';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.updator IS '创建人';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.updated_time IS '更新时间';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.deleted IS '是否已删除 1：已删除 0：未删除';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.delivery_fee IS '配送费';
COMMENT ON COLUMN meiju.ods_diana_t_price_book_detail.purchasing_unit IS '采购单位';



select * FROM 
meiju.ods_diana_t_price_book_detail
where sku_id = '21723'

id	book_code	book_detail_code	sku_id	sku_code	purchase_price	supplier_invoicing_type	supplier_invoicing_tax_rate	arrive_day	status	creator	created_time	updator	updated_time	deleted	delivery_fee	purchasing_unit
18730	PB00000068	21723	21723	12921723	16.60	1	13.00	7	0	12528922	2025-12-04 22:45:28		2025-12-04 22:45:28+08	0	0.00	片



select 
-- *
company_name,id
from meiju.ods_diana_t_supplier
where deleted = '0'
-- AND company_name ='易欧思系统门窗（山东）有限公司'
-- and supplier_biz_type ='1'