import { useState, useEffect } from 'react'
import { Form, Input, Button, Card, App, Descriptions } from 'antd'
import { UserOutlined, MailOutlined, LockOutlined } from '@ant-design/icons'
import { authAPI } from '../api'

export default function Profile() {
  const { message } = App.useApp()
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const u = localStorage.getItem('user')
    if (u) setUser(JSON.parse(u))
  }, [])

  const handleUpdate = async (values) => {
    setLoading(true)
    try {
      const { data } = await authAPI.updateMe(values)
      localStorage.setItem('user', JSON.stringify(data.user))
      setUser(data.user)
      message.success('更新成功')
    } catch (err) {
      message.error(err.response?.data?.msg || '更新失败')
    } finally {
      setLoading(false)
    }
  }

  if (!user) return null

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <h2 style={{ fontSize: 24, fontWeight: 700, marginBottom: 24 }}>
        <UserOutlined style={{ marginRight: 8 }} />个人设置
      </h2>

      <Card style={{ borderRadius: 12, marginBottom: 24 }}>
        <Descriptions column={1}>
          <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
          <Descriptions.Item label="邮箱">{user.email}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="修改信息" style={{ borderRadius: 12, marginBottom: 24 }}>
        <Form onFinish={handleUpdate} layout="vertical" initialValues={{
          username: user.username, email: user.email
        }}>
          <Form.Item name="username" label="用户名"
                     rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} />
          </Form.Item>
          <Form.Item name="email" label="邮箱"
                     rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '请输入有效邮箱' }]}>
            <Input prefix={<MailOutlined />} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>保存修改</Button>
          </Form.Item>
        </Form>
      </Card>

      <Card title="修改密码" style={{ borderRadius: 12 }}>
        <Form onFinish={(v) => handleUpdate({ password: v.newPassword })} layout="vertical">
          <Form.Item name="newPassword" label="新密码"
                     rules={[{ required: true, min: 6, message: '密码不少于6位' }]}>
            <Input.Password prefix={<LockOutlined />} />
          </Form.Item>
          <Form.Item name="confirmPassword" label="确认新密码"
                     rules={[
                       { required: true, message: '请确认密码' },
                       ({ getFieldValue }) => ({
                         validator(_, value) {
                           if (!value || getFieldValue('newPassword') === value) return Promise.resolve()
                           return Promise.reject(new Error('两次密码不一致'))
                         }
                       })
                     ]}>
            <Input.Password prefix={<LockOutlined />} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>修改密码</Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
