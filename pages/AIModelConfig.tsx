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
  Progress,
  Alert
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  RobotOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  SettingOutlined,
  ApiOutlined,
  KeyOutlined,
  ThunderboltOutlined,
  CloudServerOutlined,
  ExperimentOutlined
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface AIModel {
  id: number;
  name: string;
  provider: string;
  model_id: string;
  display_name: string;
  base_url: string;
  api_key: string;
  api_type: string;
  is_default: boolean;
  is_active: boolean;
  connection_status: 'connected' | 'disconnected' | 'testing';
  response_time?: number;
  created_at: string;
  updated_at: string;
}

interface ModelProvider {
  key: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  default_base_url: string;
  default_models: Array<{ id: string; name: string }>;
  api_types: string[];
}

const AIModelConfig: React.FC = () => {
  const [models, setModels] = useState<AIModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [testingModel, setTestingModel] = useState<number | null>(null);
  const [editingModel, setEditingModel] = useState<AIModel | null>(null);
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('list');

  // 模型提供商配置
  const providers: ModelProvider[] = [
    {
      key: 'openai',
      name: 'OpenAI',
      description: 'OpenAI GPT系列模型',
      icon: <RobotOutlined style={{ color: '#10a37f' }} />,
      default_base_url: 'https://api.openai.com/v1',
      default_models: [
        { id: 'gpt-4', name: 'GPT-4' },
        { id: 'gpt-4-turbo', name: 'GPT-4 Turbo' },
        { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo' },
        { id: 'gpt-3.5-turbo-16k', name: 'GPT-3.5 Turbo 16K' }
      ],
      api_types: ['openai-completions', 'openai-chat']
    },
    {
      key: 'deepseek',
      name: 'DeepSeek',
      description: 'DeepSeek AI大模型',
      icon: <ThunderboltOutlined style={{ color: '#ff6b35' }} />,
      default_base_url: 'https://api.deepseek.com/v1',
      default_models: [
        { id: 'deepseek-chat', name: 'DeepSeek Chat' },
        { id: 'deepseek-coder', name: 'DeepSeek Coder' }
      ],
      api_types: ['openai-completions', 'openai-chat']
    },
    {
      key: 'minimax',
      name: 'MiniMax',
      description: 'MiniMax AI模型',
      icon: <CloudServerOutlined style={{ color: '#722ed1' }} />,
      default_base_url: 'https://api.edgefn.net/v1',
      default_models: [
        { id: 'MiniMax-M2.5', name: 'MiniMax M2.5' },
        { id: 'MiniMax-M2.5-highspeed', name: 'MiniMax M2.5 Highspeed' }
      ],
      api_types: ['openai-completions', 'openai-chat']
    },
    {
      key: 'custom',
      name: '自定义模型',
      description: '其他兼容OpenAI API的模型',
      icon: <ApiOutlined style={{ color: '#1890ff' }} />,
      default_base_url: '',
      default_models: [],
      api_types: ['openai-completions', 'openai-chat']
    }
  ];

  // 模拟数据
  useEffect(() => {
    const mockData: AIModel[] = [
      {
        id: 1,
        name: 'DeepSeek Chat',
        provider: 'deepseek',
        model_id: 'deepseek-chat',
        display_name: 'DeepSeek Chat',
        base_url: 'https://api.deepseek.com/v1',
        api_key: 'sk-***',
        api_type: 'openai-chat',
        is_default: true,
        is_active: true,
        connection_status: 'connected',
        response_time: 850,
        created_at: '2026-03-15 10:30:00',
        updated_at: '2026-03-18 09:15:00'
      },
      {
        id: 2,
        name: 'MiniMax M2.5',
        provider: 'minimax',
        model_id: 'MiniMax-M2.5',
        display_name: 'MiniMax M2.5',
        base_url: 'https://api.edgefn.net/v1',
        api_key: 'sk-8XArZVija21W4cEn0610Ba0578Ad470b8aC4AdAdB83b96F0',
        api_type: 'openai-completions',
        is_default: false,
        is_active: false,
        connection_status: 'disconnected',
        created_at: '2026-03-10 14:20:00',
        updated_at: '2026-03-17 16:45:00'
      }
    ];
    setModels(mockData);
  }, []);

  const handleAdd = () => {
    setEditingModel(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: AIModel) => {
    setEditingModel(record);
    form.setFieldsValue({
      ...record,
      api_key: record.api_key && record.api_key.includes('***') ? '' : record.api_key
    });
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      setLoading(true);
      
      // 获取认证token
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      // 调用后端API删除
      const response = await fetch(`http://localhost:5000/api/ai-models/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        message.success('AI模型已删除');
        fetchModels(); // 重新加载数据
      } else {
        const error = await response.json();
        message.error(`删除失败: ${error.error}`);
      }
    } catch (error) {
      message.error('删除失败');
    } finally {
      setLoading(false);
    }
  };

  const handleTest = async (id: number) => {
    try {
      setTestingModel(id);
      
      // 获取认证token
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      console.log('🔑 测试使用的token:', token);
      console.log('🔗 测试URL:', `http://localhost:5000/api/ai-models/${id}/test`);

      // 调用后端API测试
      const response = await fetch(`http://localhost:5000/api/ai-models/${id}/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      console.log('📊 测试响应状态:', response.status);
      
      const responseText = await response.text();
      console.log('📝 测试响应内容:', responseText);

      if (response.ok) {
        message.success('模型测试成功');
        fetchModels(); // 重新加载数据
      } else {
        try {
          const error = JSON.parse(responseText);
          message.error(`测试失败: ${error.error}`);
        } catch {
          message.error(`测试失败: ${responseText}`);
        }
      }
    } catch (error) {
      console.error('❌ 测试异常:', error);
      message.error('模型测试失败');
    } finally {
      setTestingModel(null);
    }
  };

  const handleSetDefault = async (id: number) => {
    try {
      setLoading(true);
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setModels(prev => prev.map(model => ({
        ...model,
        is_default: model.id === id
      })));
      message.success('默认模型已设置');
    } catch (error) {
      message.error('设置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // 获取认证token
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      if (editingModel) {
        // 编辑现有模型 - 调用后端API
        // 字段映射：前端字段 -> 后端字段
        const backendData = {
          name: values.display_name || values.name,
          provider: values.provider,
          model: values.model_id,
          base_url: values.base_url,
          api_key: values.api_key,
          is_active: values.is_active,
          max_tokens: values.max_tokens || 2048,
          temperature: values.temperature || 0.7
        };

        const response = await fetch(`http://localhost:5000/api/ai-models/${editingModel.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(backendData)
        });

        if (response.ok) {
          const result = await response.json();
          message.success('AI模型已更新');
          fetchModels(); // 重新加载数据
        } else {
          const error = await response.json();
          message.error(`更新失败: ${error.error}`);
        }
      } else {
        // 添加新模型 - 调用后端API
        // 字段映射：前端字段 -> 后端字段
        const backendData = {
          name: values.display_name || values.name,
          provider: values.provider,
          model: values.model_id,
          base_url: values.base_url,
          api_key: values.api_key,
          is_active: values.is_active,
          max_tokens: values.max_tokens || 2048,
          temperature: values.temperature || 0.7
        };

        const response = await fetch('http://localhost:5000/api/ai-models', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(backendData)
        });

        if (response.ok) {
          const result = await response.json();
          message.success('AI模型已添加');
          fetchModels(); // 重新加载数据
        } else {
          const error = await response.json();
          message.error(`添加失败: ${error.error}`);
        }
      }

      setModalVisible(false);
      form.resetFields();
    } catch (error) {
      message.error('操作失败');
    } finally {
      setLoading(false);
    }
  };

  // 从后端获取模型列表
  const fetchModels = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await fetch('http://localhost:5000/api/ai-models', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        // 字段映射：后端字段 -> 前端字段
        const mappedModels = (data.models || []).map((model: any) => ({
          ...model,
          model_id: model.model,  // 后端model -> 前端model_id
          display_name: model.name,  // 后端name -> 前端display_name
          api_key: model.api_key || '***',  // 确保api_key存在
          connection_status: model.is_active ? 'connected' : 'disconnected',  // 添加连接状态
          is_default: model.is_active,  // 临时使用is_active作为is_default
        }));
        setModels(mappedModels);
      }
    } catch (error) {
      console.error('获取模型列表失败:', error);
    }
  };

  // 组件加载时获取数据
  useEffect(() => {
    fetchModels();
  }, []);

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'connected':
        return <Tag color="success" icon={<CheckCircleOutlined />}>已连接</Tag>;
      case 'testing':
        return <Tag color="processing" icon={<ReloadOutlined spin />}>测试中</Tag>;
      default:
        return <Tag color="error" icon={<ExclamationCircleOutlined />}>未连接</Tag>;
    }
  };

  const getProviderIcon = (provider: string) => {
    const providerConfig = providers.find(p => p.key === provider);
    return providerConfig?.icon || <RobotOutlined />;
  };

  const columns = [
    {
      title: '模型名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string, record: AIModel) => (
        <Space>
          {getProviderIcon(record.provider)}
          <span>
            {text}
            {record.is_default && <Tag color="blue" style={{ marginLeft: 8 }}>默认</Tag>}
          </span>
        </Space>
      ),
    },
    {
      title: '提供商',
      dataIndex: 'provider',
      key: 'provider',
      render: (provider: string) => {
        const config = providers.find(p => p.key === provider);
        return <Tag color="blue">{config?.name || provider}</Tag>;
      },
    },
    {
      title: '模型ID',
      dataIndex: 'model_id',
      key: 'model_id',
      render: (text: string) => <Text code>{text}</Text>,
    },
    {
      title: 'API类型',
      dataIndex: 'api_type',
      key: 'api_type',
      render: (type: string) => <Tag color="purple">{type}</Tag>,
    },
    {
      title: '响应时间',
      dataIndex: 'response_time',
      key: 'response_time',
      render: (time?: number) => 
        time ? <Text>{time}ms</Text> : <Text type="secondary">-</Text>,
    },
    {
      title: '连接状态',
      dataIndex: 'connection_status',
      key: 'connection_status',
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '操作',
      key: 'actions',
      render: (record: AIModel) => (
        <Space>
          <Tooltip title="测试连接">
            <Button
              type="text"
              icon={<ExperimentOutlined />}
              loading={testingModel === record.id}
              onClick={() => handleTest(record.id)}
            />
          </Tooltip>
          
          {!record.is_default && (
            <Tooltip title="设为默认">
              <Button
                type="text"
                icon={<SettingOutlined />}
                onClick={() => handleSetDefault(record.id)}
              />
            </Tooltip>
          )}
          
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          
          <Popconfirm
            title="确定要删除这个AI模型吗？"
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

  const handleProviderChange = (provider: string) => {
    const providerConfig = providers.find(p => p.key === provider);
    if (providerConfig) {
      form.setFieldsValue({
        base_url: providerConfig.default_base_url,
        api_type: providerConfig.api_types[0]
      });
    }
  };

  const tabItems = [
    {
      key: 'list',
      label: '模型列表',
      children: (
        <div>
          <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={4} style={{ margin: 0 }}>AI模型管理</Title>
            <Button 
              type="primary" 
              icon={<PlusOutlined />} 
              onClick={handleAdd}
              style={{ borderRadius: '6px' }}
            >
              添加模型
            </Button>
          </div>
          
          <Table
            columns={columns}
            dataSource={models}
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
      key: 'providers',
      label: '提供商配置',
      children: (
        <div>
          <Title level={4} style={{ marginBottom: '24px' }}>支持的模型提供商</Title>
          <List
            grid={{ gutter: 16, xs: 1, sm: 2, md: 2, lg: 3, xl: 3, xxl: 4 }}
            dataSource={providers}
            renderItem={provider => (
              <List.Item>
                <Card
                  hoverable
                  style={{ borderRadius: '12px', height: '200px' }}
                  bodyStyle={{ padding: '20px' }}
                >
                  <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                    <Avatar size={48} style={{ backgroundColor: '#f0f0f0' }}>
                      {provider.icon}
                    </Avatar>
                  </div>
                  <Title level={5} style={{ textAlign: 'center', margin: '8px 0' }}>
                    {provider.name}
                  </Title>
                  <Paragraph 
                    type="secondary" 
                    style={{ textAlign: 'center', margin: 0, fontSize: '12px' }}
                  >
                    {provider.description}
                  </Paragraph>
                </Card>
              </List.Item>
            )}
          />
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
              title="总模型数"
              value={models.length}
              prefix={<RobotOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card style={{ borderRadius: '12px' }}>
            <Statistic
              title="活跃模型"
              value={models.filter(m => m.connection_status === 'connected').length}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card style={{ borderRadius: '12px' }}>
            <Statistic
              title="默认模型"
              value={models.filter(m => m.is_default).length}
              prefix={<SettingOutlined />}
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
        title={editingModel ? '编辑AI模型' : '添加AI模型'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={loading}
        width={700}
        style={{ borderRadius: '12px' }}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            provider: 'openai',
            api_type: 'openai-chat',
            is_active: true,
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="模型名称"
                rules={[{ required: true, message: '请输入模型名称' }]}
              >
                <Input placeholder="例如：DeepSeek Chat" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="provider"
                label="提供商"
                rules={[{ required: true, message: '请选择提供商' }]}
              >
                <Select placeholder="选择提供商" onChange={handleProviderChange}>
                  {providers.map(provider => (
                    <Option key={provider.key} value={provider.key}>
                      <Space>
                        {provider.icon}
                        {provider.name}
                      </Space>
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="model_id"
                label="模型ID"
                rules={[{ required: true, message: '请输入模型ID' }]}
              >
                <Input placeholder="例如：deepseek-chat" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="display_name"
                label="显示名称"
                rules={[{ required: true, message: '请输入显示名称' }]}
              >
                <Input placeholder="例如：DeepSeek Chat" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="base_url"
            label="API地址"
            rules={[{ required: true, message: '请输入API地址' }]}
          >
            <Input placeholder="https://api.example.com/v1" />
          </Form.Item>

          <Form.Item
            name="api_key"
            label="API密钥"
            rules={[{ required: true, message: '请输入API密钥' }]}
          >
            <Input.Password placeholder="输入API密钥" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="api_type"
                label="API类型"
                rules={[{ required: true, message: '请选择API类型' }]}
              >
                <Select placeholder="选择API类型">
                  <Option value="openai-completions">OpenAI Completions</Option>
                  <Option value="openai-chat">OpenAI Chat</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="is_active"
                label="启用模型"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default AIModelConfig;
