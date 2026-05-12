import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, List, Button, Tag, Spin, App, Descriptions, Dropdown, Modal, Space, Empty } from 'antd'
import { ArrowLeftOutlined, ReadOutlined, BookOutlined, SwapOutlined, MoreOutlined, FolderOutlined } from '@ant-design/icons'
import { booksAPI, readerAPI } from '../api'

export default function BookDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { message } = App.useApp()
  const [book, setBook] = useState(null)
  const [loading, setLoading] = useState(true)
  const [progress, setProgress] = useState(null)
  const [groups, setGroups] = useState([])

  // 换源
  const [searchResults, setSearchResults] = useState([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [switchModalOpen, setSwitchModalOpen] = useState(false)

  useEffect(() => {
    loadData()
    loadGroups()
  }, [id])

  const loadData = async () => {
    setLoading(true)
    try {
      const { data } = await booksAPI.getBook(id)
      setBook(data)
      try {
        const { data: p } = await readerAPI.getProgress(id)
        setProgress(p)
      } catch { /* ignore */ }
    } catch (err) {
      message.error('加载书籍详情失败')
    } finally {
      setLoading(false)
    }
  }

  const loadGroups = async () => {
    try {
      const { data } = await booksAPI.getGroups()
      setGroups(data)
    } catch { /* ignore */ }
  }

  const handleRead = (chapterId) => {
    navigate(`/read/${id}/${chapterId}`)
  }

  const handleContinueRead = () => {
    if (progress?.chapter_id) {
      navigate(`/read/${id}/${progress.chapter_id}`)
    } else {
      const firstChapter = book?.chapters?.[0]
      if (firstChapter) navigate(`/read/${id}/${firstChapter.id}`)
    }
  }

  // 换源
  const handleSearchSources = async () => {
    setSwitchModalOpen(true)
    setSearchLoading(true)
    setSearchResults([])
    try {
      const { data } = await booksAPI.searchSources(id)
      setSearchResults(data || [])
    } catch (err) {
      message.error('搜索书源失败')
    } finally {
      setSearchLoading(false)
    }
  }

  const handleSwitchSource = async (result) => {
    try {
      const { data } = await booksAPI.switchSource(id, {
        url: result.url,
        source_name: result.source_name
      })
      message.success(data.msg)
      setSwitchModalOpen(false)
      loadData()
    } catch (err) {
      message.error(err.response?.data?.msg || '换源失败')
    }
  }

  const handleSetGroup = async (groupId) => {
    try {
      await booksAPI.setBookGroup(id, { group_id: groupId })
      message.success('分组设置成功')
      loadData()
    } catch (err) {
      message.error('设置失败')
    }
  }

  const menuItems = [
    {
      key: 'switch',
      icon: <SwapOutlined />,
      label: '搜索换源',
      onClick: handleSearchSources
    },
    { type: 'divider' },
    ...groups.length > 0 ? [{
      key: 'group-label',
      type: 'group',
      label: '移入分组',
      children: [
        { key: 'group-none', label: '未分组', onClick: () => handleSetGroup(null) },
        ...groups.map(g => ({
          key: `group-${g.id}`,
          label: `${g.name}${book?.group_id === g.id ? ' ✓' : ''}`,
          onClick: () => handleSetGroup(g.id)
        }))
      ]
    }] : []
  ]

  if (loading) return <div style={{ textAlign: 'center', padding: 80 }}><Spin size="large" /></div>
  if (!book) return <div>书籍不存在</div>

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Button type="link" icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}
                style={{ padding: 0 }}>
          返回
        </Button>
        <Dropdown menu={{ items: menuItems }} trigger={['click']}>
          <Button icon={<MoreOutlined />}>更多操作</Button>
        </Dropdown>
      </div>

      <Card style={{ borderRadius: 12, marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
          <div style={{
            width: 160, height: 220, borderRadius: 8, flexShrink: 0,
            background: book.cover_url
              ? `url(${book.cover_url}) center/cover`
              : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center'
          }}>
            {!book.cover_url && <BookOutlined style={{ fontSize: 48, color: 'rgba(255,255,255,0.6)' }} />}
          </div>

          <div style={{ flex: 1, minWidth: 200 }}>
            <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>{book.title}</h1>
            <Descriptions column={1} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="作者">{book.author}</Descriptions.Item>
              <Descriptions.Item label="分类"><Tag color="blue">{book.category}</Tag></Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={book.status === '完结' ? 'green' : 'orange'}>{book.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="字数">{book.word_count || '未知'}</Descriptions.Item>
              <Descriptions.Item label="章节数">{book.chapters?.length || 0} 章</Descriptions.Item>
              <Descriptions.Item label="书源">
                <Tag color="purple">{book.source_name}</Tag>
                <a href={book.book_url} target="_blank" rel="noreferrer"
                   style={{ fontSize: 12, marginLeft: 8, color: 'var(--text-secondary)' }}>
                  访问原站
                </a>
              </Descriptions.Item>
            </Descriptions>

            {book.description && (
              <p style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.6, marginBottom: 16 }}>
                {book.description}
              </p>
            )}

            <Space>
              <Button type="primary" size="large" icon={<ReadOutlined />} onClick={handleContinueRead}>
                {progress?.chapter_id ? '继续阅读' : '开始阅读'}
              </Button>
              <Button icon={<SwapOutlined />} onClick={handleSearchSources}>
                搜索换源
              </Button>
            </Space>
          </div>
        </div>
      </Card>

      <Card title={<span><BookOutlined style={{ marginRight: 8 }} />章节目录</span>}
            style={{ borderRadius: 12 }}>
        <List
          grid={{ gutter: 16, column: 4, xs: 1, sm: 2, md: 3, lg: 4 }}
          dataSource={book.chapters}
          renderItem={(chapter) => (
            <List.Item>
              <Button block onClick={() => handleRead(chapter.id)}
                      style={{
                        textAlign: 'left', height: 'auto', padding: '8px 12px',
                        borderRadius: 8,
                        border: progress?.chapter_id === chapter.id ? '1px solid var(--primary)' : undefined,
                        color: progress?.chapter_id === chapter.id ? 'var(--primary)' : undefined
                      }}>
                <span style={{
                  overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  display: 'block', fontSize: 13
                }}>
                  {chapter.index + 1}. {chapter.title}
                </span>
              </Button>
            </List.Item>
          )}
        />
      </Card>

      {/* 换源 Modal */}
      <Modal
        title={`搜索换源 - ${book.title}`}
        open={switchModalOpen}
        onCancel={() => setSwitchModalOpen(false)}
        footer={null}
        width={600}
      >
        <div style={{ marginBottom: 12, fontSize: 13, color: 'var(--text-secondary)' }}>
          自动搜索其他站点上同名书籍，选择后可切换书源。换源后章节将重新爬取，阅读进度将重置。
        </div>
        <Spin spinning={searchLoading}>
          {searchResults.length === 0 && !searchLoading ? (
            <Empty description="未找到其他书源" style={{ padding: 40 }} />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {searchResults.map((r, i) => (
                <Card key={i} size="small" hoverable style={{ borderRadius: 8 }}
                      onClick={() => handleSwitchSource(r)}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 14 }}>{r.title}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
                        <Tag color="purple" style={{ marginRight: 4 }}>{r.source_name}</Tag>
                        <span style={{ wordBreak: 'break-all' }}>{r.url}</span>
                      </div>
                    </div>
                    <Button type="primary" size="small" icon={<SwapOutlined />}>换源</Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </Spin>
      </Modal>
    </div>
  )
}
