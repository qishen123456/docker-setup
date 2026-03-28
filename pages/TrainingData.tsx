import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  Space,
  Tag,
  message,
  Popconfirm,
  Typography,
  Row,
  Col,
  Statistic,
  Tooltip,
  Tabs,
  List,
  Avatar,
  Alert,
  Upload,
  Divider
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  BookOutlined,
  FileTextOutlined,
  CodeOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  UploadOutlined,
  DownloadOutlined,
  EyeOutlined,
  CopyOutlined,
  SearchOutlined,
  FilterOutlined,
  SyncOutlined
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface TrainingData {
  id: number;
  title: string;
  type: 'ddl' | 'documentation' | 'sql';
  content: string;
  description: string;
  tags: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
  database_schema?: string;
  table_name?: string;
}

const TrainingData: React.FC = () => {
  const [data, setData] = useState<TrainingData[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingData, setEditingData] = useState<TrainingData | null>(null);
  const [activeTab, setActiveTab] = useState('list');
  const [searchText, setSearchText] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [form] = Form.useForm();

  // 模拟数据
  useEffect(() => {
    const mockData: TrainingData[] = [
      {
        id: 1,
        title: '客户表结构',
        type: 'ddl',
        content: `CREATE TABLE [dbo].[Account] (
    [AccountId] [uniqueidentifier] NOT NULL,
    [Name] [nvarchar](160) NULL,
    [PrimaryContactId] [uniqueidentifier] NULL,
    [Telephone1] [nvarchar](50) NULL,
    [Address1_Name] [nvarchar](100) NULL,
    [Address1_City] [nvarchar](80) NULL,
    [Address1_StateOrProvince] [nvarchar](50) NULL,
    [Address1_PostalCode] [nvarchar](20) NULL,
    [Address1_Country] [nvarchar](80) NULL,
    [CreatedOn] [datetime] NOT NULL,
    [ModifiedOn] [datetime] NULL,
    [StateCode] [int] NULL,
    [StatusCode] [int] NULL,
    CONSTRAINT [PK_Account] PRIMARY KEY CLUSTERED ([AccountId] ASC)
);`,
        description: '客户基本信息表，包含客户的基本联系信息',
        tags: ['客户', '基础表', 'CRM'],
        is_active: true,
        created_at: '2026-03-15 10:30:00',
        updated_at: '2026-03-18 09:15:00',
        created_by: 'admin',
        database_schema: 'dbo',
        table_name: 'Account'
      },
      {
        id: 2,
        title: '销售订单查询示例',
        type: 'sql',
        content: `-- 查询最近30天的销售订单
SELECT 
    so.SalesOrderId,
    so.OrderDate,
    so.TotalAmount,
    a.Name as CustomerName,
    a.AccountId
FROM SalesOrder so
INNER JOIN Account a ON so.AccountId = a.AccountId
WHERE so.OrderDate >= DATEADD(day, -30, GETDATE())
    AND so.StateCode = 0
ORDER BY so.OrderDate DESC;`,
        description: '查询最近30天的销售订单信息，包含客户名称和订单金额',
        tags: ['销售', '订单查询', '报表'],
        is_active: true,
        created_at: '2026-03-10 14:20:00',
        updated_at: '2026-03-17 16:45:00',
        created_by: 'admin'
      },
      {
        id: 3,
        title: '产品目录说明',
        type: 'documentation',
        content: `产品目录是系统中的核心业务实体，包含以下主要信息：

## 基本信息
- 产品ID：唯一标识符
- 产品名称：显示名称
- 产品分类：所属产品类别
- 价格信息：标准价格和折扣价格

## 业务规则
1. 产品状态：激活/停用
2. 库存管理：库存数量和预警
3. 价格策略：不同客户群体的价格差异

## 相关表
- Product：产品主表
- ProductCategory：产品分类
- ProductPrice：价格表
- Inventory：库存表`,
        description: '产品目录的详细说明文档，包含业务规则和相关表结构',
        tags: ['产品', '文档', '业务规则'],
        is_active: true,
        created_at: '2026-03-08 09:15:00',
        updated_at: '2026-03-16 11:30:00',
        created_by: 'admin'
      },
      {
        id: 4,
        title: '用户权限表',
        type: 'ddl',
        content: `CREATE TABLE [dbo].[SystemUser] (
    [SystemUserId] [uniqueidentifier] NOT NULL,
    [DomainName] [nvarchar](255) NULL,
    [FirstName] [nvarchar](64) NULL,
    [LastName] [nvarchar](64) NULL,
    [FullName] [nvarchar](200) NULL,
    [InternalEMailAddress] [nvarchar](256) NULL,
    [IsDisabled] [bit] NOT NULL,
    [CreatedOn] [datetime] NOT NULL,
    [ModifiedOn] [datetime] NULL,
    CONSTRAINT [PK_SystemUser] PRIMARY KEY CLUSTERED ([SystemUserId] ASC)
);`,
        description: '系统用户表，存储用户基本信息和权限状态',
        tags: ['用户', '权限', '系统表'],
        is_active: false,
        created_at: '2026-03-05 16:20:00',
        updated_at: '2026-03-12 10:45:00',
        created_by: 'admin',
        database_schema: 'dbo',
        table_name: 'SystemUser'
      }
    ];
    setData(mockData);
  }, []);

  const handleAdd = () => {
    setEditingData(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: TrainingData) => {
    setEditingData(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      setLoading(true);
      await new Promise(resolve => setTimeout(resolve, 1000));
      setData(prev => prev.filter(item => item.id !== id));
      message.success('训练数据已删除');
    } catch (error) {
      message.error('删除失败');
    } finally {
      setLoading(false);
    }
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      if (editingData) {
        // 编辑现有数据
        await new Promise(resolve => setTimeout(resolve, 1000));
        setData(prev => prev.map(item => 
          item.id === editingData.id 
            ? { ...item, ...values, updated_at: new Date().toISOString() }
            : item
        ));
        message.success('训练数据已更新');
      } else {
        // 添加新数据
        await new Promise(resolve => setTimeout(resolve, 1000));
        const newData: TrainingData = {
          ...values,
          id: Date.now(),
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          created_by: 'admin'
        };
        setData(prev => [...prev, newData]);
        message.success('训练数据已添加');
      }

      setModalVisible(false);
      form.resetFields();
    } catch (error) {
      message.error('操作失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyContent = (content: string) => {
    navigator.clipboard.writeText(content);
    message.success('内容已复制到剪贴板');
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'ddl':
        return <DatabaseOutlined style={{ color: '#1890ff' }} />;
      case 'sql_example':
        return <CodeOutlined style={{ color: '#52c41a' }} />;
      case 'documentation':
        return <FileTextOutlined style={{ color: '#722ed1' }} />;
      default:
        return <BookOutlined />;
    }
  };

  const getTypeTag = (type: string) => {
    switch (type) {
      case 'ddl':
        return <Tag color="blue">DDL</Tag>;
      case 'sql':
        return <Tag color="green">SQL示例</Tag>;
      case 'documentation':
        return <Tag color="purple">文档</Tag>;
      default:
        return <Tag>其他</Tag>;
    }
  };

  // 过滤数据
  const filteredData = data.filter(item => {
    const matchesSearch = item.title.toLowerCase().includes(searchText.toLowerCase()) ||
                         item.description.toLowerCase().includes(searchText.toLowerCase()) ||
                         item.tags.some(tag => tag.toLowerCase().includes(searchText.toLowerCase()));
    const matchesType = filterType === 'all' || item.type === filterType;
    return matchesSearch && matchesType;
  });

  const columns = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: TrainingData) => (
        <Space>
          {getTypeIcon(record.type)}
          <span>
            {text}
            {!record.is_active && <Tag color="default" style={{ marginLeft: 8 }}>已停用</Tag>}
          </span>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => getTypeTag(type),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <Text>{text}</Text>
        </Tooltip>
      ),
    },
    {
      title: '标签',
      dataIndex: 'tags',
      key: 'tags',
      render: (tags: string[]) => (
        <Space wrap>
          {tags.map(tag => (
            <Tag key={tag}>{tag}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => <Text type="secondary">{text}</Text>,
    },
    {
      title: '操作',
      key: 'actions',
      render: (record: TrainingData) => (
        <Space>
          <Tooltip title="查看内容">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => {
                Modal.info({
                  title: record.title,
                  width: 800,
                  content: (
                    <div>
                      <Paragraph>{record.description}</Paragraph>
                      <Divider />
                      <Text code style={{ display: 'block', whiteSpace: 'pre-wrap', backgroundColor: '#f6f8fa', padding: '16px', borderRadius: '6px' }}>{record.content}</Text>
                    </div>
                  ),
                });
              }}
            />
          </Tooltip>
          
          <Tooltip title="复制内容">
            <Button
              type="text"
              icon={<CopyOutlined />}
              onClick={() => handleCopyContent(record.content)}
            />
          </Tooltip>
          
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          
          <Popconfirm
            title="确定要删除这条训练数据吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const tabItems = [
    {
      key: 'list',
      label: '数据列表',
      children: (
        <div>
          <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={4} style={{ margin: 0 }}>训练数据管理</Title>
            <Button 
              type="primary" 
              icon={<PlusOutlined />} 
              onClick={handleAdd}
              style={{ borderRadius: '6px' }}
            >
              添加数据
            </Button>
          </div>
          
          <div style={{ marginBottom: '16px', display: 'flex', gap: '16px', alignItems: 'center' }}>
            <Input
              placeholder="搜索标题、描述或标签"
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 300 }}
            />
            <Select
              placeholder="筛选类型"
              value={filterType}
              onChange={setFilterType}
              style={{ width: 120 }}
            >
              <Option value="all">全部</Option>
              <Option value="ddl">DDL</Option>
              <Option value="sql">SQL示例</Option>
              <Option value="documentation">文档</Option>
            </Select>
            <Button icon={<SyncOutlined />} onClick={() => window.location.reload()}>
              刷新
            </Button>
          </div>
          
          <Table
            columns={columns}
            dataSource={filteredData}
            rowKey="id"
            loading={loading}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
            }}
          />
        </div>
      ),
    },
    {
      key: 'statistics',
      label: '数据统计',
      children: (
        <div>
          <Title level={4} style={{ marginBottom: '24px' }}>训练数据统计</Title>
          <Row gutter={[24, 24]}>
            <Col xs={24} sm={12} md={6}>
              <Card style={{ borderRadius: '12px' }}>
                <Statistic
                  title="总数据量"
                  value={data.length}
                  prefix={<BookOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card style={{ borderRadius: '12px' }}>
                <Statistic
                  title="DDL语句"
                  value={data.filter(d => d.type === 'ddl').length}
                  prefix={<DatabaseOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card style={{ borderRadius: '12px' }}>
                <Statistic
                  title="SQL示例"
                  value={data.filter(d => d.type === 'sql').length}
                  prefix={<CodeOutlined />}
                  valueStyle={{ color: '#722ed1' }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={12} md={6}>
              <Card style={{ borderRadius: '12px' }}>
                <Statistic
                  title="文档说明"
                  value={data.filter(d => d.type === 'documentation').length}
                  prefix={<FileTextOutlined />}
                  valueStyle={{ color: '#fa8c16' }}
                />
              </Card>
            </Col>
          </Row>
          
          <Row gutter={[24, 24]} style={{ marginTop: '24px' }}>
            <Col xs={24}>
              <Card title="活跃数据" style={{ borderRadius: '12px' }}>
                <List
                  dataSource={data.filter(d => d.is_active)}
                  renderItem={item => (
                    <List.Item>
                      <List.Item.Meta
                        avatar={<Avatar icon={getTypeIcon(item.type)} />}
                        title={item.title}
                        description={item.description}
                      />
                      <div>
                        {getTypeTag(item.type)}
                        <Text type="secondary" style={{ marginLeft: 8 }}>
                          {item.created_at}
                        </Text>
                      </div>
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
          </Row>
        </div>
      ),
    },
  ];

  return (
    <div style={{ padding: '0' }}>
      {/* 统计卡片 */}
      <Row gutter={[24, 24]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={8}>
          <Card style={{ borderRadius: '12px' }}>
            <Statistic
              title="总数据量"
              value={data.length}
              prefix={<BookOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card style={{ borderRadius: '12px' }}>
            <Statistic
              title="活跃数据"
              value={data.filter(d => d.is_active).length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card style={{ borderRadius: '12px' }}>
            <Statistic
              title="数据类型"
              value={new Set(data.map(d => d.type)).size}
              prefix={<FilterOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 主要内容 */}
      <Card style={{ borderRadius: '12px' }}>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>

      {/* 添加/编辑模态框 */}
      <Modal
        title={editingData ? '编辑训练数据' : '添加训练数据'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={loading}
        width={800}
        style={{ borderRadius: '12px' }}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            type: 'ddl',
            is_active: true,
            tags: [],
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="title"
                label="标题"
                rules={[{ required: true, message: '请输入标题' }]}
              >
                <Input placeholder="例如：客户表结构" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="type"
                label="数据类型"
                rules={[{ required: true, message: '请选择数据类型' }]}
              >
                <Select placeholder="选择数据类型">
                  <Option value="ddl">DDL语句</Option>
                  <Option value="sql">SQL示例</Option>
                  <Option value="documentation">文档说明</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="描述"
            rules={[{ required: true, message: '请输入描述' }]}
          >
            <TextArea placeholder="请输入数据描述" rows={2} />
          </Form.Item>

          <Form.Item
            name="content"
            label="内容"
            rules={[{ required: true, message: '请输入内容' }]}
          >
            <TextArea 
              placeholder="请输入DDL语句、SQL示例或文档内容" 
              rows={8}
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>

          <Form.Item
            name="tags"
            label="标签"
          >
            <Select
              mode="tags"
              placeholder="添加标签（按回车确认）"
              style={{ width: '100%' }}
            >
              <Option value="客户">客户</Option>
              <Option value="销售">销售</Option>
              <Option value="产品">产品</Option>
              <Option value="订单">订单</Option>
              <Option value="报表">报表</Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="database_schema"
                label="数据库架构（可选）"
              >
                <Input placeholder="例如：dbo" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="table_name"
                label="表名（可选）"
              >
                <Input placeholder="例如：Account" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="is_active"
            label="启用状态"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TrainingData;
