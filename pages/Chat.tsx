import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Input, 
  Button, 
  Space, 
  Typography, 
  Spin, 
  Alert, 
  Table, 
  Tag, 
  Tooltip,
  Collapse,
  Statistic,
  Row,
  Col,
  message,
  Dropdown,
  MenuProps,
  Divider
} from 'antd';
import { 
  SendOutlined, 
  RobotOutlined, 
  UserOutlined,
  CopyOutlined,
  DownloadOutlined,
  EyeOutlined,
  MoreOutlined,
  BarChartOutlined,
  TableOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { TextArea } = Input;
const { Title, Text } = Typography;
const { Panel } = Collapse;

interface Message {
  id: string;
  type: 'user' | 'ai';
  content: string;
  sql?: string;
  sql_result?: any[];
  execution_time?: number;
  timestamp: Date;
  error?: string;
  chart_type?: 'table' | 'line' | 'pie' | 'column';
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const navigate = useNavigate();

  // 获取存储的token
  const getToken = () => {
    return localStorage.getItem('token') || '';
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    const question = input;
    setInput('');
    setLoading(true);

    try {
      // 调用真实的聊天API
      const response = await fetch('http://localhost:5000/api/chat/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken()}`,
        },
        body: JSON.stringify({
          question: question,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // 分析返回的数据类型，自动选择图表类型
      let chartType: Message['chart_type'] = 'table';
      if (data.sql_result && Array.isArray(data.sql_result) && data.sql_result.length > 0) {
        const firstResult = data.sql_result[0];
        const keys = Object.keys(firstResult);
        
        // 检查是否适合图表展示
        if (keys.length === 2) {
          const key1 = keys[0];
          const key2 = keys[1];
          const value1 = firstResult[key1];
          const value2 = firstResult[key2];
          
          // 检查是否为数值类型
          if (typeof value2 === 'number' && data.sql_result.length <= 20) {
            chartType = 'column'; // 柱状图
          } else if (typeof value1 === 'string' && typeof value2 === 'number') {
            chartType = 'pie'; // 饼图
          }
        } else if (keys.some(key => {
          const value = firstResult[key];
          return typeof value === 'number' && (key.toLowerCase().includes('date') || key.toLowerCase().includes('time'));
        })) {
          chartType = 'line'; // 折线图
        }
      }

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: data.answer || '抱歉，我无法回答这个问题。',
        sql: data.sql_query,
        sql_result: data.sql_result,
        execution_time: data.execution_time,
        timestamp: new Date(),
        chart_type: chartType,
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('发送消息失败:', error);
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'ai',
        content: `抱歉，处理您的问题时出现了错误：${error instanceof Error ? error.message : '未知错误'}`,
        timestamp: new Date(),
        error: error instanceof Error ? error.message : '未知错误',
      };

      setMessages(prev => [...prev, errorMessage]);
      message.error('发送消息失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCopySQL = (sql: string) => {
    navigator.clipboard.writeText(sql);
    message.success('SQL已复制到剪贴板');
  };

  const handleCopyData = (data: any[]) => {
    const csv = data.map(row => Object.values(row).join(',')).join('\n');
    navigator.clipboard.writeText(csv);
    message.success('数据已复制到剪贴板');
  };

  const handleDownloadData = (data: any[], filename: string) => {
    const csv = [
      Object.keys(data[0]).join(','),
      ...data.map(row => Object.values(row).join(','))
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
    message.success('数据已下载');
  };

  const handleChartTypeChange = (messageId: string, chartType: Message['chart_type']) => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageId ? { ...msg, chart_type: chartType } : msg
    ));
  };

  const renderChart = (message: Message) => {
    if (!message.sql_result || message.sql_result.length === 0) return null;

    const data = message.sql_result;
    
    switch (message.chart_type) {
      case 'line':
        return renderLineChart(data);
      case 'pie':
        return renderPieChart(data);
      case 'column':
        return renderColumnChart(data);
      default:
        return renderDataTable(data);
    }
  };

  const renderDataTable = (data: any[]) => {
    if (!data || data.length === 0) return null;

    const columns = Object.keys(data[0]).map(key => ({
      title: key,
      dataIndex: key,
      key: key,
      render: (value: any) => {
        if (typeof value === 'number') {
          return <Text strong>{value.toLocaleString()}</Text>;
        }
        return <Text>{value}</Text>;
      },
    }));

    return (
      <Table
        columns={columns}
        dataSource={data}
        pagination={{ pageSize: 10, size: 'small' }}
        size="small"
        scroll={{ x: 'max-content' }}
        rowKey={(_, index) => index || 0}
      />
    );
  };

  const renderLineChart = (data: any[]) => {
    const keys = Object.keys(data[0]);
    const dateKey = keys.find(key => 
      key.toLowerCase().includes('date') || key.toLowerCase().includes('time')
    );
    const valueKey = keys.find(key => typeof data[0][key] === 'number');

    if (!dateKey || !valueKey) return renderDataTable(data);

    return (
      <div style={{ padding: '16px' }}>
        <Title level={5}>折线图</Title>
        <div style={{ height: '200px', position: 'relative', border: '1px solid #f0f0f0', borderRadius: '4px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', height: '100%' }}>
            {data.slice(0, 10).map((item, index) => {
              const maxValue = Math.max(...data.map(d => d[valueKey]));
              const height = (item[valueKey] / maxValue) * 100;
              return (
                <div key={index} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
                  <div 
                    style={{ 
                      width: '20px', 
                      height: `${height}%`, 
                      backgroundColor: '#1890ff', 
                      borderRadius: '2px',
                      marginBottom: '4px'
                    }} 
                  />
                  <Text style={{ fontSize: '10px', transform: 'rotate(-45deg)', transformOrigin: 'center' }}>
                    {item[dateKey]?.toString().slice(0, 8)}
                  </Text>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  const renderPieChart = (data: any[]) => {
    const keys = Object.keys(data[0]);
    const labelKey = keys.find(key => typeof data[0][key] === 'string');
    const valueKey = keys.find(key => typeof data[0][key] === 'number');

    if (!labelKey || !valueKey) return renderDataTable(data);

    const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2'];
    const total = data.reduce((sum, item) => sum + item[valueKey], 0);

    return (
      <div style={{ padding: '16px' }}>
        <Title level={5}>饼图</Title>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {data.slice(0, 6).map((item, index) => {
            const percentage = ((item[valueKey] / total) * 100).toFixed(1);
            return (
              <div key={index} style={{ 
                display: 'flex', 
                alignItems: 'center', 
                padding: '4px 8px', 
                border: '1px solid #f0f0f0', 
                borderRadius: '4px',
                minWidth: '120px'
              }}>
                <div 
                  style={{ 
                    width: '12px', 
                    height: '12px', 
                    backgroundColor: colors[index % colors.length], 
                    borderRadius: '50%',
                    marginRight: '8px'
                  }} 
                />
                <Text style={{ fontSize: '12px' }}>
                  {item[labelKey]}: {percentage}%
                </Text>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderColumnChart = (data: any[]) => {
    const keys = Object.keys(data[0]);
    const labelKey = keys.find(key => typeof data[0][key] === 'string');
    const valueKey = keys.find(key => typeof data[0][key] === 'number');

    if (!labelKey || !valueKey) return renderDataTable(data);

    return (
      <div style={{ padding: '16px' }}>
        <Title level={5}>柱状图</Title>
        <div style={{ height: '200px', position: 'relative', border: '1px solid #f0f0f0', borderRadius: '4px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'flex-end', height: '100%' }}>
            {data.slice(0, 8).map((item, index) => {
              const maxValue = Math.max(...data.map(d => d[valueKey]));
              const height = (item[valueKey] / maxValue) * 100;
              const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2'];
              return (
                <div key={index} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1 }}>
                  <Text style={{ fontSize: '12px', marginBottom: '4px' }}>
                    {item[valueKey]}
                  </Text>
                  <div 
                    style={{ 
                      width: '30px', 
                      height: `${height}%`, 
                      backgroundColor: colors[index % colors.length], 
                      borderRadius: '2px',
                      marginBottom: '4px'
                    }} 
                  />
                  <Text style={{ fontSize: '10px' }}>
                    {item[labelKey]?.toString().slice(0, 6)}
                  </Text>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  const getChartMenuItems = (message: Message): MenuProps['items'] => [
    {
      key: 'table',
      label: '表格',
      icon: <TableOutlined />,
      onClick: () => handleChartTypeChange(message.id, 'table'),
    },
    {
      key: 'line',
      label: '折线图',
      icon: <BarChartOutlined />,
      onClick: () => handleChartTypeChange(message.id, 'line'),
    },
    {
      key: 'pie',
      label: '饼图',
      icon: <BarChartOutlined />,
      onClick: () => handleChartTypeChange(message.id, 'pie'),
    },
    {
      key: 'column',
      label: '柱状图',
      icon: <BarChartOutlined />,
      onClick: () => handleChartTypeChange(message.id, 'column'),
    },
  ];

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <Title level={2}>智能问答</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => setMessages([])}>
            清空对话
          </Button>
          <Button onClick={() => navigate('/dashboard')}>返回仪表盘</Button>
        </Space>
      </div>

      <Card style={{ height: '70vh', display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px', backgroundColor: '#f5f5f5' }}>
          {messages.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#999', marginTop: '50px' }}>
              <RobotOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
              <div>开始向AI提问吧！</div>
              <div style={{ marginTop: '8px', fontSize: '14px' }}>
                例如：查询最近7天的客户数据
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                style={{
                  marginBottom: '16px',
                  display: 'flex',
                  justifyContent: message.type === 'user' ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '80%',
                    padding: '12px',
                    borderRadius: '12px',
                    backgroundColor: message.type === 'user' ? '#1890ff' : '#fff',
                    color: message.type === 'user' ? '#fff' : '#333',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                    {message.type === 'user' ? <UserOutlined /> : <RobotOutlined />}
                    <span style={{ marginLeft: '8px', fontSize: '12px', opacity: 0.8 }}>
                      {message.type === 'user' ? '我' : 'AI助手'}
                    </span>
                    {message.execution_time && (
                      <Tag color="blue" style={{ marginLeft: '8px', fontSize: '10px' }}>
                        {message.execution_time.toFixed(2)}s
                      </Tag>
                    )}
                  </div>
                  <div>{message.content}</div>
                  
                  {message.sql && (
                    <Collapse ghost style={{ marginTop: '12px' }}>
                      <Panel 
                        key="sql"
                        header="SQL查询" 
                        extra={
                          <Button 
                            size="small" 
                            type="text" 
                            icon={<CopyOutlined />}
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCopySQL(message.sql!);
                            }}
                          >
                            复制SQL
                          </Button>
                        }
                      >
                        <Text 
                          code 
                          style={{ 
                            fontSize: '12px', 
                            backgroundColor: '#f6f8fa', 
                            padding: '8px', 
                            borderRadius: '4px', 
                            display: 'block',
                            whiteSpace: 'pre-wrap'
                          }}
                        >
                          {message.sql}
                        </Text>
                      </Panel>
                    </Collapse>
                  )}
                  
                  {message.sql_result && (
                    <div style={{ marginTop: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <Text strong>查询结果 ({message.sql_result.length} 条)</Text>
                        <Space>
                          <Dropdown menu={{ items: getChartMenuItems(message) }} trigger={['click']}>
                            <Button size="small" icon={<MoreOutlined />}>
                              切换图表
                            </Button>
                          </Dropdown>
                          <Button 
                            size="small" 
                            icon={<CopyOutlined />}
                            onClick={() => handleCopyData(message.sql_result!)}
                          >
                            复制数据
                          </Button>
                          <Button 
                            size="small" 
                            icon={<DownloadOutlined />}
                            onClick={() => handleDownloadData(message.sql_result!, 'query_result.csv')}
                          >
                            下载CSV
                          </Button>
                        </Space>
                      </div>
                      
                      <div style={{ backgroundColor: '#fff', padding: '12px', borderRadius: '8px', border: '1px solid #d9d9d9' }}>
                        {renderChart(message)}
                      </div>
                    </div>
                  )}
                  
                  {message.error && (
                    <Alert
                      message="错误"
                      description={message.error}
                      type="error"
                      style={{ marginTop: '12px' }}
                    />
                  )}
                </div>
              </div>
            ))
          )}
          
          {loading && (
            <div style={{ textAlign: 'center', marginTop: '16px' }}>
              <Spin />
              <div style={{ marginTop: '8px', color: '#999' }}>AI正在思考...</div>
            </div>
          )}
        </div>

        <div style={{ padding: '16px', borderTop: '1px solid #f0f0f0' }}>
          <Space.Compact style={{ width: '100%' }}>
            <TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入您的问题..."
              autoSize={{ minRows: 1, maxRows: 4 }}
              disabled={loading}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSend}
              disabled={!input.trim() || loading}
              style={{ height: 'auto' }}
            >
              发送
            </Button>
          </Space.Compact>
        </div>
      </Card>
    </div>
  );
};

export default Chat;
