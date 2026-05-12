import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Input, Select, Card, Tag, Empty, Spin, Row, Col, Pagination, App, Dropdown, Modal, Form, Button, Space } from 'antd'
import {
  SearchOutlined, BookOutlined, DeleteOutlined, FolderOutlined,
  PlusOutlined, EditOutlined, SwapOutlined, MoreOutlined
} from '@ant-design/icons'
import { booksAPI } from '../api'

const { Search } = Input

export default function Home() {
  const navigate = useNavigate()
  const { message, modal } = App.useApp()
  const [books, setBooks] = useState([])
  const [loading, setLoading] = useState(true)
  const [keyword, setKeyword] = useState('')
  const [sourceId, setSourceId] = useState(null)
  const [category, setCategory] = useState('')
  const [categories, setCategories] = useState([])
  const [sources, setSources] = useState([])
  const [pagination, setPagination] = useState({ page: 1, per_page: 20, total: 0, pages: 0 })

  // 分组相关
  const [groups, setGroups] = useState([])
  const [selectedGroup, setSelectedGroup] = useState(null)
  const [groupModalOpen, setGroupModalOpen] = useState(false)
  const [groupForm] = Form.useForm()

  // 换源相关
  const [searchResults, setSearchResults] = useState([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [switchModalOpen, setSwitchModalOpen] = useState(false)
  const [switchingBook, setSwitchingBook] = useState(null)

  useEffect(() => {
    loadSources()
    loadCategories()
    loadGroups()
  }, [])

  useEffect(() => {
    loadBooks()
  }, [pagination.page, keyword, sourceId, category, selectedGroup])

  const loadBooks = async () => {
    setLoading(true)
    try {
      const params = {
        page: pagination.page, per_page: pagination.per_page,
        keyword, source_id: sourceId, category
      }
      if (selectedGroup) params.group_id = selectedGroup
      const { data } = await booksAPI.getBooks(params)
      setBooks(data.books)
      setPagination(prev => ({ ...prev, total: data.total, pages: data.pages }))
    } catch (err) {
      message.error('加载书籍失败')
    } finally {
      setLoading(false)
    }
  }

  const loadSources = async () => {
    try {
      const { data } = await booksAPI.getSources()
      setSources(data)
    } catch (err) { /* ignore */ }
  }

  const loadCategories = async () => {
    try {
      const { data } = await booksAPI.getCategories()
      setCategories(data)
    } catch (err) { /* ignore */ }
  }

  const loadGroups = async () => {
    try {
      const { data } = await booksAPI.getGroups()
      setGroups(data)
    } catch (err) { /* ignore */ }
  }

  const handleDelete = async (e, id) => {
    e.stopPropagation()
    try {
      await booksAPI.deleteBook(id)
      message.success('删除成功')
      loadBooks()
    } catch (err) {
      message.error('删除失败')
    }
  }

  // 分组操作
  const handleAddGroup = async (values) => {
    try {
      await booksAPI.addGroup(values)
      message.success('分组创建成功')
      setGroupModalOpen(false)
      groupForm.resetFields()
      loadGroups()
    } catch (err) {
      message.error(err.response?.data?.msg || '创建失败')
    }
  }

  const handleDeleteGroup = async (groupId) => {
    try {
      await booksAPI.deleteGroup(groupId)
      message.success('分组删除成功')
      if (selectedGroup === groupId) setSelectedGroup(null)
      loadGroups()
      loadBooks()
    } catch (err) {
      message.error('删除失败')
    }
  }

  const handleSetBookGroup = async (bookId, groupId) => {
    try {
      await booksAPI.setBookGroup(bookId, { group_id: groupId })
      message.success('分组设置成功')
      loadBooks()
    } catch (err) {
      message.error('设置失败')
    }
  }

  // 换源操作
  const handleSearchSources = async (book) => {
    setSwitchingBook(book)
    setSwitchModalOpen(true)
    setSearchLoading(true)
    setSearchResults([])
    try {
      const { data } = await booksAPI.searchSources(book.id)
      setSearchResults(data || [])
    } catch (err) {
      message.error('搜索书源失败')
    } finally {
      setSearchLoading(false)
    }
  }

  const handleSwitchSource = async (result) => {
    try {
      const { data } = await booksAPI.switchSource(switchingBook.id, {
        url: result.url,
        source_name: result.source_name
      })
      message.success(data.msg)
      setSwitchModalOpen(false)
      setSwitchingBook(null)
      loadBooks()
    } catch (err) {
      message.error(err.response?.data?.msg || '换源失败')
    }
  }

  const getBookMenuItems = (book) => [
    {
      key: 'switch',
      icon: <SwapOutlined />,
      label: '搜索换源',
      onClick: () => {
        handleSearchSources(book)
      }
    },
    {
      type: 'divider'
    },
    ...groups.length > 0 ? [{
      key: 'group-label',
      type: 'group',
      label: '移入分组',
      children: [
        { key: 'group-none', label: '未分组', onClick: () => handleSetBookGroup(book.id, null) },
        ...groups.map(g => ({
          key: `group-${g.id}`,
          label: g.name,
          onClick: () => handleSetBookGroup(book.id, g.id)
        }))
      ]
    }] : []
  ]

  return (
    <div>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 24, flexWrap: 'wrap', gap: 12
      }}>
        <h2 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>
          <BookOutlined style={{ marginRight: 8 }} />我的书架
        </h2>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <Search
            placeholder="搜索书名或作者"
            allowClear
            onSearch={v => { setKeyword(v); setPagination(p => ({ ...p, page: 1 })) }}
            style={{ width: 240 }}
          />
          <Select
            placeholder="按书源筛选"
            allowClear
            style={{ width: 160 }}
            onChange={v => { setSourceId(v); setPagination(p => ({ ...p, page: 1 })) }}
            options={sources.map(s => ({ label: s.name, value: s.id }))}
          />
          <Select
            placeholder="按分类筛选"
            allowClear
            style={{ width: 150 }}
            onChange={v => { setCategory(v); setPagination(p => ({ ...p, page: 1 })) }}
            options={categories.map(c => ({ label: c, value: c }))}
          />
          <Button icon={<PlusOutlined />} onClick={() => setGroupModalOpen(true)}>
            新建分组
          </Button>
        </div>
      </div>

      {/* 分组标签 */}
      {groups.length > 0 && (
        <div style={{
          display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center'
        }}>
          <Tag
            style={{ cursor: 'pointer', padding: '4px 12px', fontSize: 13, borderRadius: 6 }}
            color={selectedGroup === null ? 'blue' : 'default'}
            onClick={() => { setSelectedGroup(null); setPagination(p => ({ ...p, page: 1 })) }}
          >
            全部
          </Tag>
          {groups.map(g => (
            <Tag
              key={g.id}
              style={{ cursor: 'pointer', padding: '4px 12px', fontSize: 13, borderRadius: 6, display: 'inline-flex', alignItems: 'center', gap: 4 }}
              color={selectedGroup === g.id ? 'blue' : 'default'}
              closable
              onClose={(e) => { e.preventDefault(); handleDeleteGroup(g.id) }}
              onClick={() => { setSelectedGroup(g.id); setPagination(p => ({ ...p, page: 1 })) }}
            >
              <FolderOutlined /> {g.name} ({g.book_count})
            </Tag>
          ))}
        </div>
      )}

      <Spin spinning={loading}>
        {books.length === 0 && !loading ? (
          <Empty description="还没有书籍，去添加书源并爬取吧" style={{ marginTop: 80 }}>
            <a onClick={() => navigate('/sources')}>前往添加书源</a>
          </Empty>
        ) : (
          <Row gutter={[16, 16]}>
            {books.map(book => (
              <Col key={book.id} xs={12} sm={8} md={6} lg={4} xl={4}>
                <Card
                  hoverable
                  onClick={() => navigate(`/book/${book.id}`)}
                  style={{ borderRadius: 12, overflow: 'hidden', position: 'relative' }}
                  bodyStyle={{ padding: 12 }}
                  cover={
                    <div style={{
                      height: 200, background: book.cover_url
                        ? `url(${book.cover_url}) center/cover`
                        : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>
                      {!book.cover_url && (
                        <BookOutlined style={{ fontSize: 48, color: 'rgba(255,255,255,0.6)' }} />
                      )}
                    </div>
                  }
                >
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {book.title}
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12, marginBottom: 6 }}>
                    {book.author}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 4 }}>
                    <Tag color="blue" style={{ margin: 0, fontSize: 11, maxWidth: 90, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{book.category}</Tag>
                    <Tag color="purple" style={{ margin: 0, fontSize: 11, maxWidth: 80, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{book.source_name}</Tag>
                  </div>
                  {book.progress && (
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 4 }}>
                      已读到第 {book.progress.chapter_index + 1} 章
                    </div>
                  )}
                  <div style={{ position: 'absolute', top: 8, right: 8, display: 'flex', gap: 4, zIndex: 10 }}
                       onClick={e => e.stopPropagation()}>
                    <Dropdown menu={{ items: getBookMenuItems(book) }} trigger={['click']}>
                      <Button
                        type="text" size="small"
                        icon={<MoreOutlined />}
                        style={{ background: 'rgba(255,255,255,0.8)', borderRadius: 4, minWidth: 24, padding: '0 4px' }}
                      />
                    </Dropdown>
                    <DeleteOutlined
                      style={{ color: '#ef4444', cursor: 'pointer', fontSize: 14, background: 'rgba(255,255,255,0.8)', borderRadius: 4, padding: 4 }}
                      onClick={e => handleDelete(e, book.id)}
                    />
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>

      {pagination.pages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', marginTop: 32 }}>
          <Pagination
            current={pagination.page}
            total={pagination.total}
            pageSize={pagination.per_page}
            onChange={page => setPagination(p => ({ ...p, page }))}
            showSizeChanger={false}
          />
        </div>
      )}

      {/* 新建分组 Modal */}
      <Modal title="新建分组" open={groupModalOpen} onCancel={() => setGroupModalOpen(false)}
             footer={null} width={400}>
        <Form form={groupForm} onFinish={handleAddGroup} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="分组名称" rules={[{ required: true, message: '请输入分组名称' }]}>
            <Input placeholder="例如：玄幻、已完结、追更中" />
          </Form.Item>
          <Form.Item>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <Button onClick={() => setGroupModalOpen(false)}>取消</Button>
              <Button type="primary" htmlType="submit">创建</Button>
            </div>
          </Form.Item>
        </Form>
        {groups.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>已有分组（点击 x 删除）：</div>
            <Space wrap>
              {groups.map(g => (
                <Tag key={g.id} closable onClose={() => handleDeleteGroup(g.id)} color="blue">
                  {g.name} ({g.book_count}本)
                </Tag>
              ))}
            </Space>
          </div>
        )}
      </Modal>

      {/* 换源 Modal */}
      <Modal
        title={`搜索换源 - ${switchingBook?.title || ''}`}
        open={switchModalOpen}
        onCancel={() => { setSwitchModalOpen(false); setSwitchingBook(null) }}
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
