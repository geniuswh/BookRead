import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Button, Modal, Form, Input, Select, Table, Tag, Space, Popover, Popconfirm, App, Collapse } from 'antd'
import {
  PlusOutlined, CloudSyncOutlined, DeleteOutlined, CloudServerOutlined,
  SettingOutlined, ThunderboltOutlined, SafetyOutlined, InfoCircleOutlined,
  EditOutlined
} from '@ant-design/icons'
import { booksAPI } from '../api'

const { TextArea } = Input

const SPEED_OPTIONS = [
  { value: 'fast', label: '快速', desc: '适合不封IP的站点，间隔约0.3s', color: 'red' },
  { value: 'normal', label: '正常', desc: '默认速度，间隔约1s', color: 'blue' },
  { value: 'slow', label: '慢速', desc: '适合有封禁风险的站点，间隔约2.5s', color: 'orange' },
  { value: 'stealth', label: '隐蔽', desc: '最大防护，间隔约5s+随机抖动', color: 'green' },
]

export default function Sources() {
  const navigate = useNavigate()
  const { message } = App.useApp()
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editingSource, setEditingSource] = useState(null)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [crawling, setCrawling] = useState({})
  const [crawlSpeed, setCrawlSpeed] = useState('normal')
  const [crawlStatus, setCrawlStatus] = useState(null)
  const [form] = Form.useForm()
  const [editForm] = Form.useForm()
  const [proxyForm] = Form.useForm()

  useEffect(() => { loadSources(); loadCrawlStatus() }, [])

  const loadSources = async () => {
    setLoading(true)
    try {
      const { data } = await booksAPI.getSources()
      setSources(data)
    } catch (err) {
      message.error('加载书源失败')
    } finally {
      setLoading(false)
    }
  }

  const loadCrawlStatus = async () => {
    try {
      const { data } = await booksAPI.getCrawlStatus()
      setCrawlStatus(data)
    } catch { /* ignore */ }
  }

  const handleAdd = async (values) => {
    try {
      await booksAPI.addSource(values)
      message.success('书源添加成功')
      setModalOpen(false)
      form.resetFields()
      loadSources()
    } catch (err) {
      message.error(err.response?.data?.msg || '添加失败')
    }
  }

  const handleCrawl = async (id) => {
    setCrawling(prev => ({ ...prev, [id]: true }))
    try {
      const { data } = await booksAPI.crawlSource(id, crawlSpeed)
      message.success(data.msg)
      loadSources()
    } catch (err) {
      message.error(err.response?.data?.msg || '爬取失败')
    } finally {
      setCrawling(prev => ({ ...prev, [id]: false }))
      loadCrawlStatus()
    }
  }

  const handleDelete = async (id) => {
    try {
      await booksAPI.deleteSource(id)
      message.success('删除成功')
      loadSources()
    } catch (err) {
      message.error('删除失败')
    }
  }

  const handleEdit = (record) => {
    setEditingSource(record)
    editForm.setFieldsValue({
      name: record.name,
      url: record.url,
      type: record.type
    })
    setEditModalOpen(true)
  }

  const handleEditSubmit = async (values) => {
    try {
      await booksAPI.updateSource(editingSource.id, values)
      message.success('书源更新成功')
      setEditModalOpen(false)
      editForm.resetFields()
      setEditingSource(null)
      loadSources()
    } catch (err) {
      message.error(err.response?.data?.msg || '更新失败')
    }
  }

  const handleSetSpeed = async (speed) => {
    try {
      await booksAPI.setSpeed(speed)
      setCrawlSpeed(speed)
      const opt = SPEED_OPTIONS.find(s => s.value === speed)
      message.success(`爬取速度已设为: ${opt.label} (${opt.desc})`)
    } catch (err) {
      message.error('设置失败')
    }
  }

  const handleSetProxies = async (values) => {
    const proxies = values.proxies
      .split('\n')
      .map(p => p.trim())
      .filter(p => p.length > 0)

    try {
      await booksAPI.setProxies(proxies)
      message.success(`代理池已更新，共 ${proxies.length} 个代理`)
      setProxyModalOpen(false)
      proxyForm.resetFields()
      loadCrawlStatus()
    } catch (err) {
      message.error('代理设置失败')
    }
  }

  const columns = [
    {
      title: '名称', dataIndex: 'name', key: 'name',
      render: (text) => <span style={{ fontWeight: 600 }}>{text}</span>
    },
    {
      title: 'URL', dataIndex: 'url', key: 'url', ellipsis: true,
      render: (url) => <a href={url} target="_blank" rel="noreferrer"
                          style={{ fontSize: 13 }}>{url}</a>
    },
    {
      title: '类型', dataIndex: 'type', key: 'type',
      render: (type) => <Tag color="purple">{type}</Tag>
    },
    {
      title: '书籍数', dataIndex: 'book_count', key: 'book_count',
      render: (count) => <Tag color="blue">{count} 本</Tag>
    },
    {
      title: '上次爬取', dataIndex: 'last_crawled', key: 'last_crawled',
      render: (v) => v ? new Date(v).toLocaleString('zh-CN') : <Tag>未爬取</Tag>
    },
    {
      title: '操作', key: 'action', width: 340,
      render: (_, record) => (
        <Space>
          <Button type="primary" size="small" icon={<CloudSyncOutlined />}
                  loading={crawling[record.id]}
                  onClick={() => handleCrawl(record.id)}>
            爬取
          </Button>
          <Button size="small" icon={<EditOutlined />}
                  onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Button size="small" onClick={() => navigate('/')}>
            查看书籍
          </Button>
          <Popconfirm title="确定删除该书源及其所有书籍？" onConfirm={() => handleDelete(record.id)}>
            <Button danger size="small" icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <h2 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>
          <CloudServerOutlined style={{ marginRight: 8 }} />书源管理
        </h2>
        <Space wrap>
          <Popover
            content={
              <div style={{ width: 300 }}>
                <div style={{ marginBottom: 8, fontWeight: 600 }}>爬取速度</div>
                <p style={{ fontSize: 12, color: '#666', marginBottom: 12 }}>
                  控制爬取间隔，速度越慢越不容易被封IP
                </p>
                <Space direction="vertical" style={{ width: '100%' }}>
                  {SPEED_OPTIONS.map(opt => (
                    <div key={opt.value}
                         onClick={() => handleSetSpeed(opt.value)}
                         style={{
                           padding: '8px 12px', borderRadius: 8, cursor: 'pointer',
                           border: crawlSpeed === opt.value ? `2px solid ${opt.color}` : '2px solid #e2e8f0',
                           background: crawlSpeed === opt.value ? `${opt.color}11` : 'transparent',
                           transition: 'all 0.2s'
                         }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 600, color: crawlSpeed === opt.value ? opt.color : undefined }}>{opt.label}</span>
                        {crawlSpeed === opt.value && <Tag color={opt.color}>当前</Tag>}
                      </div>
                      <div style={{ fontSize: 12, color: '#666' }}>{opt.desc}</div>
                    </div>
                  ))}
                </Space>
              </div>
            }
            title={false}
            trigger="click"
          >
            <Button icon={<ThunderboltOutlined />}>
              速度: {SPEED_OPTIONS.find(s => s.value === crawlSpeed)?.label}
            </Button>
          </Popover>

          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            添加书源
          </Button>
        </Space>
      </div>

      <Card style={{ borderRadius: 12 }}>
        <Table columns={columns} dataSource={sources} rowKey="id"
               loading={loading} pagination={false} />
      </Card>

      {/* 高级反封禁设置 */}
      <Collapse
        style={{ marginTop: 16, borderRadius: 12, overflow: 'hidden' }}
        activeKey={showAdvanced ? ['advanced'] : []}
        onChange={(keys) => setShowAdvanced(keys.includes('advanced'))}
        items={[{
          key: 'advanced',
          label: <span><SafetyOutlined style={{ marginRight: 8 }} />高级反封禁设置（可选）</span>,
          children: (
            <div>
              <div style={{
                background: '#f0f9ff', padding: 12, borderRadius: 8, marginBottom: 16,
                fontSize: 13, color: '#0369a1'
              }}>
                <p style={{ fontWeight: 600, marginBottom: 4 }}>
                  <InfoCircleOutlined style={{ marginRight: 4 }} />
                  默认无需配置代理即可正常使用。以下设置仅在被目标网站封禁 IP 时才需要。
                </p>
                <ul style={{ margin: '4px 0 0 0', paddingLeft: 16 }}>
                  <li>如果爬取正常，<b>不需要</b>配置代理</li>
                  <li>如果遇到 403 或频繁超时，可尝试添加代理</li>
                  <li>支持 HTTP/HTTPS/SOCKS5 代理，每行一个</li>
                  <li>爬虫会自动轮换使用不同代理，连续失败3次的代理会自动移除</li>
                </ul>
              </div>

              {crawlStatus?.is_cooling_down && (
                <div style={{
                  background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 8,
                  padding: '8px 16px', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8
                }}>
                  <SafetyOutlined style={{ color: '#f97316' }} />
                  <span style={{ color: '#9a3412', fontSize: 13 }}>
                    爬虫正在冷却中（目标站点返回了限流响应），自动降速等待后继续...
                  </span>
                </div>
              )}

              <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'flex-start' }}>
                <div style={{ flex: 1, minWidth: 300 }}>
                  <Form form={proxyForm} onFinish={handleSetProxies} layout="vertical">
                    <Form.Item name="proxies" label="代理列表（留空则不使用代理）"
                               initialValue="">
                      <TextArea rows={5} placeholder={"http://127.0.0.1:7890\nsocks5://127.0.0.1:1080\nhttp://user:pass@proxy:8080"}
                                style={{ fontFamily: 'monospace', fontSize: 13 }} />
                    </Form.Item>
                    <Form.Item>
                      <Space>
                        <Button type="primary" htmlType="submit">保存代理</Button>
                        <Button onClick={loadCrawlStatus} icon={<InfoCircleOutlined />}>
                          查看状态
                          {crawlStatus && ` (${crawlStatus.request_count}次请求, ${crawlStatus.proxy_count}个代理)`}
                        </Button>
                      </Space>
                    </Form.Item>
                  </Form>
                </div>
              </div>
            </div>
          )
        }]}
      />

      {/* 添加书源 Modal */}
      <Modal title="添加书源" open={modalOpen} onCancel={() => setModalOpen(false)}
             footer={null} width={520}>
        <Form form={form} onFinish={handleAdd} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="书源名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如：笔趣阁" />
          </Form.Item>
          <Form.Item name="url" label="书源URL" rules={[{ required: true, message: '请输入URL' }]}>
            <Input placeholder="例如：https://www.biquge.com/book/123/" />
          </Form.Item>
          <Form.Item name="type" label="站点类型" initialValue="custom">
            <Select options={[
              { value: 'custom', label: '自动识别' },
              { value: 'biquge', label: '笔趣阁系列' },
              { value: 'tianya', label: '天涯论坛' },
            ]} />
          </Form.Item>
          <Form.Item>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <Button onClick={() => setModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit">添加并爬取</Button>
            </div>
          </Form.Item>
        </Form>
        <div style={{ background: '#f1f5f9', padding: 12, borderRadius: 8, fontSize: 13, color: 'var(--text-secondary)' }}>
          <p style={{ fontWeight: 600, marginBottom: 4 }}>支持的站点类型：</p>
          <ul style={{ margin: 0, paddingLeft: 16 }}>
            <li><b>笔趣阁系列</b>：biquge/bqgui/biquwx 等同结构站点</li>
            <li><b>天涯论坛</b>：填入帖子页面 URL</li>
            <li><b>自动识别</b>：系统会尝试自动识别站点结构</li>
          </ul>
        </div>
      </Modal>

      {/* 编辑书源 Modal */}
      <Modal title="编辑书源" open={editModalOpen} onCancel={() => { setEditModalOpen(false); setEditingSource(null) }}
             footer={null} width={520}>
        <Form form={editForm} onFinish={handleEditSubmit} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="书源名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如：笔趣阁" />
          </Form.Item>
          <Form.Item name="url" label="书源URL" rules={[{ required: true, message: '请输入URL' }]}>
            <Input placeholder="例如：https://www.biquge.com/book/123/" />
          </Form.Item>
          <Form.Item name="type" label="站点类型">
            <Select options={[
              { value: 'custom', label: '自动识别' },
              { value: 'biquge', label: '笔趣阁系列' },
              { value: 'tianya', label: '天涯论坛' },
            ]} />
          </Form.Item>
          <Form.Item>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <Button onClick={() => { setEditModalOpen(false); setEditingSource(null) }}>取消</Button>
              <Button type="primary" htmlType="submit">保存修改</Button>
            </div>
          </Form.Item>
        </Form>
      </Modal>

    </div>
  )
}
