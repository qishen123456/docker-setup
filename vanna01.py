

class DeepSeekChat(VannaBase):
    def __init__(self, config=None):
        if config is None:
            raise ValueError("For DeepSeek, config must be provided with an api_key and model")

        if "api_key" not in config:
            raise ValueError("config must contain a DeepSeek api_key")

        if "model" not in config:
            raise ValueError("config must contain a DeepSeek model")

        api_key = config["api_key"]
        self.model = config["model"]
        self.client = OpenAI(api_key=api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

    def system_message(self, message: str) -> dict:
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> dict:
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> dict:
        return {"role": "assistant", "content": message}

    def generate_sql(self, question: str, **kwargs) -> str:
        sql = super().generate_sql(question, **kwargs)
        return sql.replace("\\_", "_")

    def submit_prompt(self, prompt, **kwargs) -> str:
        chat_response = self.client.chat.completions.create(
            model=self.model,
            messages=prompt,
            stream=False
        )
        return chat_response.choices[0].message.content


class MyVanna(ChromaDB_VectorStore, DeepSeekChat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        DeepSeekChat.__init__(self, config=config)


if __name__ == "__main__":
    # 定义配置信息
    config = {
        'api_key': 'sk-76585a8711f84d45a60b9dc36497213e',  # DeepSeek API Key
        'model': 'qwen-max',  # 使用的模型
        # SQL Server 连接参数
        'server': 'crmproddbread.angelgroup.com.cn',  # 服务器名称或IP
        'database': 'CRM01_MSCRM',  # 数据库名称
        'username': 'dc',  # 登录用户名
        'password': 'angel@oa!@#3',  # 登录密码
        'driver': 'ODBC Driver 17 for SQL Server'  # ODBC驱动版本
    }

    # 定义ODBC连接字符串
    odbc_conn_str = (
        f"DRIVER={{{config['driver']}}};"
        f"SERVER={config['server']};"
        f"DATABASE={config['database']};"
        f"UID={config['username']};"
        f"PWD={config['password']}"
    )

    # 创建Vanna实例
    vn = MyVanna(config=config)

    # 使用定义好的ODBC连接字符串连接到SQL Server
    vn.connect_to_mssql(odbc_conn_str=odbc_conn_str)
    # 训练模型（根据实际情况添加文档）
    documentation = """
    表名	表描述	字段名	字段显示名
Account	Account	accountratingcode	客户等级
Account	Account	address2_upszone	地址 2: UPS 区域
Account	Account	websiteurl	网站
Account	Account	name	客户名称
Account	Account	address2_latitude	地址 2: 纬度
Account	Account	createdby	创建者
Account	Account	address1_primarycontactname	地址 1: 主要联系人姓名
Account	Account	shippingmethodcode	送货方式
Account	Account	lastusedincampaign	上次参与市场活动的日期
Account	Account	address2_line1	地址 2: 街道 1
Account	Account	ftpsiteurl	FTP 站点
Account	Account	numberofemployees	员工数
Account	Account	address1_postalcode	地址 1: 邮政编码
Account	Account	merged	合并
Account	Account	address1_name	地址 1: 名称
Account	Account	createdon	创建时间
Account	Account	address1_telephone1	联络电话
Account	Account	parentaccountid	上级单位
Account	Account	address1_addressid	地址 1: ID
Account	Account	donotsendmm	发送市场营销资料
Account	Account	emailaddress1	电子邮件
Account	Account	modifiedby	修改者
Account	Account	address1_telephone3	地址 1: 电话 3
Account	Account	donotfax	不允许使用传真
Account	Account	address1_utcoffset	地址 1: UTC 时差
Account	Account	statecode	状态
Account	Account	address1_line3	地址 1: 街道 3
Account	Account	address1_stateorprovince	地址 1: 省/市/自治区
Account	Account	primarycontactid	主要联系人
Account	Account	emailaddress3	电子邮件地址 3
Account	Account	address1_fax	地址 1: 传真
Account	Account	address1_line1	地址 1: 街道 1
Account	Account	address2_county	地址 2: 县
Account	Account	preferredserviceid	首选服务
Account	Account	address1_freighttermscode	地址 1: 货运条款
Account	Account	address2_postalcode	地址 2: 邮政编码
Account	Account	defaultpricelevelid	价目表
Account	Account	address2_freighttermscode	地址 2: 货运条款
Account	Account	accountcategorycode	类别
Account	Account	address2_country	地址 2: 国家/地区
Account	Account	sic	行业编码
Account	Account	statuscode	状态描述
Account	Account	address1_county	地址 1: 县
Account	Account	ggd_maintenancedatecustomerinformation	保养提醒日期（客情）
Account	Account	ggd_primarycontactname	主要联系人名称
Account	Account	creditlimit_base	信用额度(基础货币)
Account	Account	aging60_base	时效 60 (基础货币)
Account	Account	stageid	流程阶段
Account	Account	ggd_custproperty	客户性质
Account	Account	ggd_expectedcallondate	期望上门时段
Account	Account	ggd_idtype	证件类型
Account	Account	ggd_mobilephone	移动电话
Account	Account	ggd_searchname	搜索名
Account	Account	ggd_totalunpaidbillamount	未付账单金额
Account	Account	ggd_duebillamount_base	到期账单金额(基础货币)
Account	Account	ggd_city	市/区
Account	Account	ggd_paymode	付款方式
Account	Account	ggd_defaultsalesgroup	默认销售组
Account	Account	ggd_accountnum	客户编号
Account	Account	ggd_zipcode	邮政编码
Account	Account	overriddencreatedon	创建记录的时间
Account	Account	ggd_location	定位位置
Account	Account	ggd_long	经度
Account	Account	marketcap_base	市值(基础货币)
Account	Account	importsequencenumber	导入序列号
Account	Account	entityimageid	实体图像 ID
Account	Account	address1_composite	地址 1
Account	Account	businesstypecode	商业类型
Account	Account	donotbulkpostalmail	不允许使用批量邮件
Account	Account	donotpostalmail	不允许使用邮件
Account	Account	ggd_invoiceaccount	发票客户
Account	Account	ggd_longitude	经度（已弃用）
Account	Account	ggd_taobaoalias	淘宝昵称
Account	Account	ggd_totalbillamount	合计账单金额
Account	Account	preferredcontactmethodcode	首选联系方式
Account	Account	preferredequipmentid	首选设施/设备
Account	Account	telephone3	电话 3
Account	Account	telephone3	电话3
Account	Account	telephone3	电话 3
Account	Account	telephone3	电话3
Account	Account	yominame	Yomi 客户名称
Account	Account	tickersymbol	股票代号
Account	Account	sharesoutstanding	已发行股票
Account	Account	originatingleadid	原始潜在顾客
Account	Account	modifiedon	修改时间
Account	Account	ggd_finishedtype	完工类型
Account	Account	ggd_displayaddress	详细地址
Account	Account	ggd_customerinformationtype	客情分类
Account	Account	entityimage	默认图像
Account	Account	description	说明
Account	Account	customertypecode	关系类型
Account	Account	address2_telephone3	地址 2: 电话 3
Account	Account	address2_postofficebox	地址 2: 邮政信箱
Account	Account	address1_postofficebox	地址 1: 邮政信箱
Account	Account	emailaddress2	电子邮件地址 2
Account	Account	ggd_areacode	地区区号
Account	Account	ownerid	负责人
Account	Account	owningteam	负责团队
Account	Account	paymenttermscode	付款方式
Account	Account	paymenttermscode	付款方式
Account	Account	paymenttermscode	付款方式
Account	Account	paymenttermscode	付款方式
Account	Account	processid	流程
Account	Account	timezoneruleversionnumber	时区规则版本号
Account	Account	territoryid	区域
Account	Account	preferredappointmentdaycode	首选日
Account	Account	participatesinworkflow	参与工作流
Account	Account	owninguser	负责人用户
Account	Account	ggd_vkmemberid	官方商城会员ID
Account	Account	ggd_servicezone	服务网格
Account	Account	ggd_processingtagfield	合并处理标记字段
Account	Account	ggd_payterm	付款条款
Account	Account	ggd_partnersornot	合作伙伴
Account	Account	ggd_customerinformationinstructions	客情指令领导
Account	Account	customersizecode	客户规模
Account	Account	aging90_base	时效 90 (基础货币)
Account	Account	aging90	时效 90
Account	Account	aging30_base	时效 30 (基础货币)
Account	Account	address2_line2	地址 2: 街道 2
Account	Account	address2_city	地址 2: 市/县
Account	Account	address2_addressid	地址 2: ID
Account	Account	address1_upszone	地址 1: UPS 区域
Account	Account	address1_addresstypecode	地址 1: 地址类型
Account	Account	accountid	客户
Account	Account	ggd_latitude	纬度（弃用）
Account	Account	marketcap	市值
Account	Account	stockexchange	证券交易所
Account	Account	telephone1	主要电话
Account	Account	telephone1	固定电话
Account	Account	telephone1	主要电话
Account	Account	telephone1	固定电话
Account	Account	owningbusinessunit	负责的业务部门
Account	Account	ggd_taobaoaccount	淘宝账号
Account	Account	ggd_street	街道
Account	Account	ggd_jobid	Job Id
Account	Account	ggd_country	国家
Account	Account	donotphone	不允许电话联络
Account	Account	donotemail	不允许使用电子邮件
Account	Account	creditonhold	信用冻结
Account	Account	createdonbehalfby	创建者(代理)
Account	Account	aging60	时效 60
Account	Account	aging30	时效 30
Account	Account	address2_utcoffset	地址 2: UTC 时差
Account	Account	address2_name	地址 2: 名称
Account	Account	ggd_custsource	客户来源
Account	Account	ggd_state	省/直辖市
Account	Account	masterid	主 ID
Account	Account	preferredsystemuserid	首选用户
Account	Account	revenue	年收入
Account	Account	telephone2	其他电话
Account	Account	versionnumber	版本号
Account	Account	territorycode	区域代码
Account	Account	ownershipcode	所有权
Account	Account	modifiedonbehalfby	修改者(代理)
Account	Account	industrycode	行业
Account	Account	ggd_payplan	付款计划
Account	Account	ggd_mobilephone2	备选移动电话
Account	Account	ggd_erpaccount	ERP客户
Account	Account	ggd_county	区/县
Account	Account	fax	传真
Account	Account	address2_telephone2	地址 2: 电话 2
Account	Account	address2_telephone1	地址 2: 电话 1
Account	Account	address2_shippingmethodcode	地址 2: 送货方式
Account	Account	address2_longitude	地址 2: 经度
Account	Account	address2_line3	地址 2: 街道 3
Account	Account	address2_fax	地址 2: 传真
Account	Account	address2_composite	地址 2
Account	Account	address1_shippingmethodcode	地址 1: 送货方式
Account	Account	address1_latitude	地址 1: 纬度
Account	Account	address1_country	地址 1: 国家/地区
Account	Account	address2_addresstypecode	地址 2: 地址类型
Account	Account	address1_city	地址 1: 市/县
Account	Account	ggd_totalbillamount_base	合计账单金额(基础货币)
Account	Account	preferredappointmenttimecode	首选时间
Account	Account	transactioncurrencyid	货币
Account	Account	utcconversiontimezonecode	UTC 转换时区代码
Account	Account	revenue_base	年收入(基础货币)
Account	Account	ggd_totalunpaidbillamount_base	未付账单金额(基础货币)
Account	Account	ggd_lat	纬度
Account	Account	ggd_informmanagerornot	通知客服经理
Account	Account	ggd_idnumber	证件号
Account	Account	ggd_duebillamount	到期账单金额
Account	Account	exchangerate	汇率
Account	Account	donotbulkemail	不允许使用批量电子邮件
Account	Account	creditlimit	信用额度
Account	Account	address2_stateorprovince	地址 2: 省/市/自治区
Account	Account	address2_primarycontactname	地址 2: 主要联系人姓名
Account	Account	address1_telephone2	地址 1: 电话 2
Account	Account	address1_line2	地址 1: 街道 2
Account	Account	accountclassificationcode	分类
Account	Account	accountclassificationcode	客户分类
Account	Account	accountclassificationcode	分类
Account	Account	accountclassificationcode	客户分类
Account	Account	address1_longitude	地址 1: 经度
Account	Account	accountnumber	客户编号

    """  # 这里可以添加数据库文档说明


    # vn.train(
    #     documentation=f"Database schema documentation: {documentation}"
    # )
    #     #
    #     vn.train(
    #         question="近3天每天的用户数",
    #         sql="""SELECT
    #     CAST(DATEADD(HOUR, 8, CreatedOn) AS DATE) AS CreatedDate,
    #     COUNT(*) AS UserCount
    # FROM Account
    # WHERE CAST(DATEADD(HOUR, 8, CreatedOn) AS DATE) >= CAST(GETDATE() - 2 AS DATE)
    # GROUP BY CAST(DATEADD(HOUR, 8, CreatedOn) AS DATE)
    # ORDER BY CreatedDate;"""
    #     )

    # response = vn.ask('今年每周的用户数，增长率怎样？图表中文显示，横坐标为年周，用户数为柱形图，显示数据标签，增占率为线图百分比格式')
    # print(response)

    # print(vn.generate_plotly_code())

    #
    # 启动Flask应用
    from vanna.flask import VannaFlaskApp

    # app = VannaFlaskApp(vn)
    # app.run()
    class SimplePassword(AuthInterface):
        def __init__(self, users: dict):
            self.users = users

        def get_user(self, flask_request) -> any:
            return flask_request.cookies.get('user')

        def is_logged_in(self, user: any) -> bool:
            return user is not None

        def override_config_for_user(self, user: any, config: dict) -> dict:
            return config

        def login_form(self) -> str:
            return '''
      <div class="p-4 sm:p-7">
        <div class="text-center">
          <h1 class="block text-2xl font-bold text-gray-800 dark:text-white">Sign in</h1>
          <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">

          </p>
        </div>

        <div class="mt-5">

          <!-- Form -->
          <form action="/auth/login" method="POST">
            <div class="grid gap-y-4">
              <!-- Form Group -->
              <div>
                <label for="email" class="block text-sm mb-2 dark:text-white">Email address</label>
                <div class="relative">
                  <input type="email" id="email" type="email" name="email" class="py-3 px-4 block w-full border border-gray-200 rounded-lg text-sm focus:border-blue-500 focus:ring-blue-500 disabled:opacity-50 disabled:pointer-events-none dark:bg-slate-900 dark:border-gray-700 dark:text-gray-400 dark:focus:ring-gray-600" required aria-describedby="email-error">
                  <div class="hidden absolute inset-y-0 end-0 pointer-events-none pe-3">
                    <svg class="size-5 text-red-500" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
                      <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zM8 4a.905.905 0 0 0-.9.995l.35 3.507a.552.552 0 0 0 1.1 0l.35-3.507A.905.905 0 0 0 8 4zm.002 6a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"/>
                    </svg>
                  </div>
                </div>
                <p class="hidden text-xs text-red-600 mt-2" id="email-error">Please include a valid email address so we can get back to you</p>
              </div>
              <!-- End Form Group -->

              <!-- Form Group -->
              <div>
                <div class="flex justify-between items-center">
                  <label for="password" class="block text-sm mb-2 dark:text-white">Password</label>

                </div>
                <div class="relative">
                  <input type="password" id="password" name="password" class="py-3 px-4 block w-full border border-gray-200 rounded-lg text-sm focus:border-blue-500 focus:ring-blue-500 disabled:opacity-50 disabled:pointer-events-none dark:bg-slate-900 dark:border-gray-700 dark:text-gray-400 dark:focus:ring-gray-600" required aria-describedby="password-error">
                  <div class="hidden absolute inset-y-0 end-0 pointer-events-none pe-3">
                    <svg class="size-5 text-red-500" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
                      <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zM8 4a.905.905 0 0 0-.9.995l.35 3.507a.552.552 0 0 0 1.1 0l.35-3.507A.905.905 0 0 0 8 4zm.002 6a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"/>
                    </svg>
                  </div>
                </div>
                <p class="hidden text-xs text-red-600 mt-2" id="password-error">8+ characters required</p>
              </div>
              <!-- End Form Group -->

              <button type="submit" class="w-full py-3 px-4 inline-flex justify-center items-center gap-x-2 text-sm font-semibold rounded-lg border border-transparent bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:pointer-events-none">Sign in</button>
            </div>
          </form>
          <!-- End Form -->
        </div>
      </div>
            '''

        def login_handler(self, flask_request) -> str:
            email = flask_request.form['email']
            password = flask_request.form['password']
            # Find the user and password in the users dict
            for user in self.users:
                if user["email"] == email and user["password"] == password:
                    response = flask.make_response('Logged in as ' + email)
                    response.set_cookie('user', email)
                    # Redirect to the main page
                    response.headers['Location'] = '/'
                    response.status_code = 302
                    return response
            else:
                return 'Login failed'

        def callback_handler(self, flask_request) -> str:
            user = flask_request.args['user']
            response = flask.make_response('Logged in as ' + user)
            response.set_cookie('user', user)
            return response

        def logout_handler(self, flask_request) -> str:
            response = flask.make_response('Logged out')
            response.delete_cookie('user')
            return response


    VannaFlaskApp(
        vn=vn,
        auth=SimplePassword(users=[{"email": "admin@example.com", "password": "password"}]),
        allow_llm_to_see_data=True,
        title="Hello World",
        subtitle="This is a test",
        show_training_data=True,
        sql=True,
        table=True,
        chart=True,
        summarization=False,
        ask_results_correct=True,
    ).run()
