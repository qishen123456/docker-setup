import React from 'react';
import { Card, Button } from 'antd';
import { useNavigate } from 'react-router-dom';

const Terminology: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2>术语库管理</h2>
        <Button onClick={() => navigate('/dashboard')}>返回仪表盘</Button>
      </div>

      <Card>
        <p>术语库管理页面正在开发中...</p>
        <p>这里将提供以下功能：</p>
        <ul>
          <li>添加业务术语</li>
          <li>配置字段映射</li>
          <li>管理术语库</li>
          <li>术语搜索</li>
        </ul>
      </Card>
    </div>
  );
};

export default Terminology;
