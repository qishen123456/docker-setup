import React, { useState } from 'react';
import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';
import './Login.css';

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const { login } = useAuthStore();

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      console.log('尝试登录:', values);
      const success = await login(values.email, values.password);
      console.log('登录结果:', success);
      if (success) {
        message.success('登录成功！');
      } else {
        message.error('邮箱或密码错误');
      }
    } catch (error) {
      console.error('登录异常:', error);
      message.error('登录失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <Card
        title="Vanna AI Platform"
        className="login-card"
        styles={{
          header: { textAlign: 'center', fontSize: '24px', fontWeight: 'bold' }
        }}
      >
        <Form
          name="login"
          onFinish={onFinish}
          autoComplete="off"
          size="large"
          initialValues={{
            email: 'admin@example.com',
            password: 'password'
          }}
        >
          <Form.Item
            name="email"
            rules={[
              { required: true, message: '请输入邮箱!' },
              { type: 'email', message: '请输入有效的邮箱地址!' }
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="邮箱"
              defaultValue="admin@example.com"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码!' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              defaultValue="password"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{ height: '45px' }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>
        
        <div className="login-tips">
          <p>测试账号：admin@example.com</p>
          <p>测试密码：password</p>
        </div>
      </Card>
    </div>
  );
};

export default Login;
