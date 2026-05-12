import { useState, useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout as AntLayout, Menu, Avatar, Dropdown, Button } from 'antd'
import {
  HomeOutlined, BookOutlined, CloudServerOutlined,
  UserOutlined, LogoutOutlined, ReadOutlined, SearchOutlined
} from '@ant-design/icons'
import { authAPI } from '../api'

const { Header, Content, Footer } = AntLayout

export default function LayoutComp() {
  const navigate = useNavigate()
  const location = useLocation()
  const [user, setUser] = useState(null)

  useEffect(() => {
    const userData = localStorage.getItem('user')
    if (!userData) {
      navigate('/login')
      return
    }
    setUser(JSON.parse(userData))
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    navigate('/login')
  }

  if (!user) return null

  const menuItems = [
    { key: '/', icon: <HomeOutlined />, label: '首页' },
    { key: '/search', icon: <SearchOutlined />, label: '搜书' },
    { key: '/sources', icon: <CloudServerOutlined />, label: '书源管理' },
  ]

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: '个人设置' },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录', danger: true },
  ]

  const handleUserMenu = ({ key }) => {
    if (key === 'logout') handleLogout()
    else if (key === 'profile') navigate('/profile')
  }

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: '#fff', padding: '0 24px', borderBottom: '1px solid var(--border-color)',
        position: 'sticky', top: 0, zIndex: 100, boxShadow: 'var(--shadow-sm)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ReadOutlined style={{ fontSize: 24, color: 'var(--primary)' }} />
          <span style={{ fontSize: 20, fontWeight: 700, color: 'var(--primary)', cursor: 'pointer' }}
                onClick={() => navigate('/')}>
            BookRead
          </span>
        </div>

        <Menu
          mode="horizontal"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ flex: 1, marginLeft: 40, border: 'none', fontWeight: 500 }}
        />

        <Dropdown menu={{ items: userMenuItems, onClick: handleUserMenu }} placement="bottomRight">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
            <Avatar style={{ background: 'var(--primary)' }} icon={<UserOutlined />} />
            <span style={{ fontWeight: 500 }}>{user.username}</span>
          </div>
        </Dropdown>
      </Header>

      <Content style={{ padding: '24px', maxWidth: 1200, margin: '0 auto', width: '100%' }}>
        <Outlet />
      </Content>

      <Footer style={{ textAlign: 'center', color: 'var(--text-secondary)', background: 'transparent' }}>
        BookRead ©{new Date().getFullYear()} - 个人网上书城
      </Footer>
    </AntLayout>
  )
}
