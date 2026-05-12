import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Form, Input, Button, Card, App } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined, ReadOutlined } from '@ant-design/icons'
import { authAPI } from '../api'

export default function Register() {
  const navigate = useNavigate()
  const { message } = App.useApp()
  const [loading, setLoading] = useState(false)

  const onFinish = async (values) => {
    if (values.password !== values.confirmPassword) {
      message.error('两次密码不一致')
      return
    }
    setLoading(true)
    try {
      const { data } = await authAPI.register({
        username: values.username,
        email: values.email,
        password: values.password
      })
      localStorage.setItem('token', data.token)
      localStorage.setItem('user', JSON.stringify(data.user))
      message.success('注册成功')
      navigate('/')
    } catch (err) {
      message.error(err.response?.data?.msg || '注册失败')
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
          <h1 style={{ fontSize: 28, fontWeight: 700 }}>创建账号</h1>
          <p style={{ color: 'var(--text-secondary)' }}>开始你的阅读之旅</p>
        </div>

        <Form onFinish={onFinish} size="large" autoComplete="off">
          <Form.Item name="username"
                     rules={[
                       { required: true, message: '请输入用户名' },
                       { min: 3, max: 20, message: '用户名长度3-20位' }
                     ]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item name="email"
                     rules={[
                       { required: true, message: '请输入邮箱' },
                       { type: 'email', message: '请输入有效邮箱' }
                     ]}>
            <Input prefix={<MailOutlined />} placeholder="邮箱" />
          </Form.Item>
          <Form.Item name="password"
                     rules={[
                       { required: true, message: '请输入密码' },
                       { min: 6, message: '密码不少于6位' }
                     ]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>
          <Form.Item name="confirmPassword"
                     rules={[{ required: true, message: '请确认密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="确认密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}
                    style={{ height: 44, fontSize: 16, fontWeight: 600 }}>
              注 册
            </Button>
          </Form.Item>
        </Form>

        <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
          已有账号？<Link to="/login" style={{ color: 'var(--primary)', fontWeight: 600 }}>立即登录</Link>
        </div>
      </Card>
    </div>
  )
}
