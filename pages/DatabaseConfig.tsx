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
  Tooltip
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ReloadOutlined,
  SettingOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { Option } = Select;

interface DatabaseConnection {
  id: number;
  name: string;
  type: string;
  host: string;
  port: number;
  database_name: string;
  username: string;
  password?: string;
  is_default: boolean;
  is_active: boolean;
  connection_status: 'connected' | 'disconnected' | 'testing';
  created_at: string;
  updated_at: string;
}

const DatabaseConfig: React.FC = () => {
  const [connections, setConnections] = useState<DatabaseConnection[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingConnection, setEditingConnection] = useState<DatabaseConnection | null>(null);
  const [testingConnection, setTestingConnection] = useState<number | null>(null);
  const [form] = Form.useForm();

  // 从后端获取数据库连接列表
  const fetchConnections = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await fetch('http://localhost:5000/api/databases', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        const mappedConnections = (data.databases || []).map((db: any) => ({
          ...db,
          connection_status: db.is_active ? 'connected' : 'disconnected',
          is_default: db.is_default || false
        }));
        setConnections(mappedConnections);
      }
    } catch (error) {
      console.error('获取数据库连接失败:', error);
    }
  };

  // 组件加载时获取数据
  useEffect(() => {
    fetchConnections();
  }, []);

  const handleAdd = () => {
    setEditingConnection(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: DatabaseConnection) => {
    setEditingConnection(record);
    form.setFieldsValue({
      ...record,
      password: record.password && record.password.includes('***') ? '' : record.password
    });
    setModalVisible(true);
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      if (editingConnection) {
        // 编辑现有连接 - 调用后端API
        const token = localStorage.getItem('token');
        if (!token) {
          message.error('请先登录');
          return;
        }

        const response = await fetch(`http://localhost:5000/api/databases/${editingConnection.id}`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(values)
        });

        if (response.ok) {
          message.success('数据库连接已更新');
          fetchConnections(); // 重新加载数据
        } else {
          const error = await response.json();
          message.error(`更新失败: ${error.error}`);
        }
      } else {
        // 添加新连接 - 调用后端API
        const token = localStorage.getItem('token');
        if (!token) {
          message.error('请先登录');
          return;
        }

        const response = await fetch('http://localhost:5000/api/databases', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(values)
        });

        if (response.ok) {
          message.success('数据库连接已添加');
          fetchConnections(); // 重新加载数据
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

  const handleDelete = async (id: number) => {
    try {
      setLoading(true);
      
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      const response = await fetch(`http://localhost:5000/api/databases/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        message.success('数据库连接已删除');
        fetchConnections();
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
      setTestingConnection(id);
      
      const token = localStorage.getItem('token');
      if (!token) {
        message.error('请先登录');
        return;
      }

      const response = await fetch(`http://localhost:5000/api/databases/${id}/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        message.success('数据库连接测试成功');
        fetchConnections();
      } else {
        const error = await response.json();
        message.error(`测试失败: ${error.error}`);
      }
    } catch (error) {
      message.error('数据库连接测试失败');
    } finally {
      setTestingConnection(null);
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag color="blue">{type.toUpperCase()}</Tag>
    },
    {
      title: '主机',
      dataIndex: 'host',
      key: 'host'
    },
    {
      title: '端口',
      dataIndex: 'port',
      key: 'port'
    },
    {
      title: '数据库',
      dataIndex: 'database_name',
      key: 'database_name'
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username'
    },
    {
      title: '状态',
      dataIndex: 'connection_status',
      key: 'connection_status',
      render: (status: string) => {
        switch (status) {
          case 'connected':
            return <Tag color="success" icon={<CheckCircleOutlined />}>已连接</Tag>;
          case 'testing':
            return <Tag color="processing" icon={<ReloadOutlined spin />}>测试中</Tag>;
          default:
            return <Tag color="error" icon={<ExclamationCircleOutlined />}>未连接</Tag>;
        }
      }
    },
    {
      title: '默认',
      dataIndex: 'is_default',
      key: 'is_default',
      render: (isDefault: boolean) => (
        isDefault ? <Tag color="gold">默认</Tag> : null
      )
    },
    {
      title: '操作',
      key: 'actions',
      render: (text: any, record: DatabaseConnection) => (
        <Space size="small">
          <Tooltip title="测试连接">
            <Button
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              loading={testingConnection === record.id}
              onClick={() => handleTest(record.id)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Popconfirm
              title="确定要删除这个数据库连接吗？"
              onConfirm={() => handleDelete(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
              />
            </Popconfirm>
          </Tooltip>
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="数据库连接"
              value={connections.length}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已连接"
              value={connections.filter(c => c.connection_status === 'connected').length}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="未连接"
              value={connections.filter(c => c.connection_status === 'disconnected').length}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="默认连接"
              value={connections.filter(c => c.is_default).length}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title="数据库连接配置"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAdd}
          >
            添加连接
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={connections}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
      </Card>

      <Modal
        title={editingConnection ? '编辑数据库连接' : '添加数据库连接'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={loading}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            type: 'mysql',
            port: 3306,
            is_active: true,
            is_default: false
          }}
        >
          <Form.Item
            label="连接名称"
            name="name"
            rules={[{ required: true, message: '请输入连接名称' }]}
          >
            <Input placeholder="例如：生产数据库" />
          </Form.Item>

          <Form.Item
            label="数据库类型"
            name="type"
            rules={[{ required: true, message: '请选择数据库类型' }]}
          >
            <Select placeholder="选择数据库类型">
              <Option value="mysql">MySQL</Option>
              <Option value="postgresql">PostgreSQL</Option>
              <Option value="sqlserver">SQL Server</Option>
              <Option value="sqlite">SQLite</Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="主机地址"
                name="host"
                rules={[{ required: true, message: '请输入主机地址' }]}
              >
                <Input placeholder="localhost" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="端口"
                name="port"
                rules={[{ required: true, message: '请输入端口号' }]}
              >
                <Input type="number" placeholder="3306" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="数据库名称"
            name="database_name"
            rules={[{ required: true, message: '请输入数据库名称' }]}
          >
            <Input placeholder="数据库名称" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="用户名"
                name="username"
                rules={[{ required: true, message: '请输入用户名' }]}
              >
                <Input placeholder="用户名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="密码"
                name="password"
                rules={[{ required: true, message: '请输入密码' }]}
              >
                <Input.Password placeholder="密码" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="启用连接"
                name="is_active"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="设为默认"
                name="is_default"
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

export default DatabaseConfig;
