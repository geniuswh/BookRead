import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Form, Input, Button, Card, App } from 'antd'
import { UserOutlined, LockOutlined, ReadOutlined } from '@ant-design/icons'
import { authAPI } from '../api'

export default function Login() {
  const navigate = useNavigate()
  const { message } = App.useApp()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values) => {
    setLoading(true)
    try {
      const { data } = await authAPI.login(values)
      localStorage.setItem('token', data.token)
      localStorage.setItem('user', JSON.stringify(data.user))
      message.success('登录成功')
      navigate('/')
    } catch (err) {
      message.error(err.response?.data?.msg || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      <Card style={{ width: 420, borderRadius: 16, boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <ReadOutlined style={{ fontSize: 48, color: 'var(--primary)', marginBottom: 12 }} />
          <h1 style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)' }}>欢迎回来</h1>
          <p style={{ color: 'var(--text-secondary)' }}>登录你的 BookRead 账号</p>
        </div>

        <Form onFinish={onFinish} size="large" autoComplete="off">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名或邮箱" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}
                    style={{ height: 44, fontSize: 16, fontWeight: 600 }}>
              登 录
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
          还没有账号？<Link to="/register" style={{ color: 'var(--primary)', fontWeight: 600 }}>立即注册</Link>
        </div>
      </Card>
    </div>
  )
}
