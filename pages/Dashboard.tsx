import React from 'react';
import { Card, Row, Col, Statistic, Progress, List, Avatar, Tag, Space, Button } from 'antd';
import {
  DatabaseOutlined,
  RobotOutlined,
  MessageOutlined,
  BookOutlined,
  ArrowUpOutlined,
  QuestionCircleOutlined,
  SettingOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const recentQueries = [
    {
      id: 1,
      question: '查询最近7天的客户数据',
      time: '2分钟前',
      status: 'success',
      sql: 'SELECT TOP 10 * FROM Account WHERE createdon >= DATEADD(day, -7, GETDATE())'
    },
    {
      id: 2,
      question: '统计各地区的销售业绩',
      time: '15分钟前',
      status: 'success',
      sql: 'SELECT region, SUM(amount) as total FROM Sales GROUP BY region'
    },
    {
      id: 3,
      question: '查找活跃用户数量',
      time: '1小时前',
      status: 'processing',
      sql: 'SELECT COUNT(*) as active_users FROM Users WHERE last_login >= DATEADD(day, -7, GETDATE())'
    },
  ];

  const quickActions = [
    {
      title: '数据源配置',
      icon: <DatabaseOutlined style={{ fontSize: '24px', color: '#1890ff' }} />,
      description: '连接和管理数据库',
      action: () => navigate('/database')
    },
    {
      title: 'AI模型设置',
      icon: <RobotOutlined style={{ fontSize: '24px', color: '#52c41a' }} />,
      description: '配置AI模型参数',
      action: () => navigate('/ai-model')
    },
    {
      title: '训练数据',
      icon: <BookOutlined style={{ fontSize: '24px', color: '#722ed1' }} />,
      description: '添加训练样本',
      action: () => navigate('/training')
    },
    {
      title: '智能问答',
      icon: <MessageOutlined style={{ fontSize: '24px', color: '#fa8c16' }} />,
      description: '开始AI对话',
      action: () => navigate('/chat')
    },
  ];

  return (
    <div style={{ padding: '0' }}>
      {/* 顶部统计卡片 */}
      <Row gutter={[24, 24]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} md={6}>
          <Card
            style={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '12px',
            }}
          >
            <Statistic
              title="数据源连接"
              value={3}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: 'white' }}
            />
            <div style={{ marginTop: '12px', fontSize: '14px' }}>
              <ArrowUpOutlined /> 2个活跃
            </div>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="AI模型"
              value={2}
              prefix={<RobotOutlined />}
              valueStyle={{ color: 'white' }}
            />
            <div style={{ marginTop: '16px' }}>
              <Button type="link" onClick={() => navigate('/ai-model')}>
                配置模型
              </Button>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="训练数据"
              value={156}
              prefix={<BookOutlined />}
              valueStyle={{ color: 'white' }}
            />
            <div style={{ marginTop: '16px' }}>
              <Button type="link" onClick={() => navigate('/training')}>
                管理数据
              </Button>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="问答次数"
              value={1284}
              prefix={<MessageOutlined />}
              valueStyle={{ color: 'white' }}
            />
            <div style={{ marginTop: '16px' }}>
              <Button type="primary" onClick={() => navigate('/chat')}>
                开始问答
              </Button>
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: '24px' }}>
        <Col xs={24} md={12}>
          <Card title="快速操作" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button type="dashed" block onClick={() => navigate('/chat')}>
                🚀 开始智能问答
              </Button>
              <Button type="dashed" block onClick={() => navigate('/database')}>
                🔗 配置数据库连接
              </Button>
              <Button type="dashed" block onClick={() => navigate('/ai-model')}>
                🤖 设置AI模型
              </Button>
              <Button type="dashed" block onClick={() => navigate('/training')}>
                📚 添加训练数据
              </Button>
            </Space>
          </Card>
        </Col>
        
        <Col xs={24} md={12}>
          <Card title="系统状态" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>✅ 后端服务: 正常运行</div>
              <div>✅ 数据库: 已连接</div>
              <div>✅ AI模型: 已配置</div>
              <div>⚠️ 训练数据: 需要添加</div>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
