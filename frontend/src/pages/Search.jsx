import { useState } from 'react'
import { Input, Card, Tag, Button, Spin, Empty, App, Row, Col, Typography } from 'antd'
import { SearchOutlined, PlusOutlined, BookOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { booksAPI } from '../api'

const { Title, Text, Paragraph } = Typography

export default function SearchPage() {
  const navigate = useNavigate()
  const { message } = App.useApp()
  const [keyword, setKeyword] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [addingIds, setAddingIds] = useState(new Set())

  const handleSearch = async (value) => {
    const kw = value || keyword
    if (!kw.trim()) {
      message.warning('请输入搜索关键字')
      return
    }
    setLoading(true)
    setSearched(true)
    setResults([])
    try {
      const { data } = await booksAPI.searchBooks(kw.trim())
      setResults(data || [])
    } catch (err) {
      message.error(err.response?.data?.msg || '搜索失败')
    } finally {
      setLoading(false)
    }
  }

  const handleAddBook = async (item) => {
    setAddingIds(prev => new Set([...prev, item.url]))
    try {
      const { data, status } = await booksAPI.addBookFromSearch({
        url: item.url,
        source_name: item.source_name,
        title: item.title
      })
      if (status === 200) {
        message.info(data.msg || '该书已在书架中')
        if (data.book_id) {
          navigate(`/book/${data.book_id}`)
        }
      } else {
        message.success(data.msg || '添加成功')
        if (data.book_id) {
          navigate(`/book/${data.book_id}`)
        }
      }
    } catch (err) {
      message.error(err.response?.data?.msg || '添加失败')
    } finally {
      setAddingIds(prev => {
        const next = new Set(prev)
        next.delete(item.url)
        return next
      })
    }
  }

  return (
    <div>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        marginBottom: 24, flexWrap: 'wrap', gap: 12
      }}>
        <h2 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>
          <SearchOutlined style={{ marginRight: 8 }} />搜书
        </h2>
      </div>

      <div style={{ marginBottom: 24 }}>
        <Input.Search
          placeholder="输入书名、作者名、或书名+作者名搜索"
          allowClear
          enterButton="搜索"
          size="large"
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          onSearch={handleSearch}
          loading={loading}
          style={{ maxWidth: 600 }}
        />
        <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-secondary)' }}>
          优先从已添加的书源站点中搜索，搜不到再从百度搜索。支持 书名、作者名、书名+作者名 等搜索方式。
        </div>
      </div>

      <Spin spinning={loading}>
        {searched && results.length === 0 && !loading ? (
          <Empty description="未找到相关书籍" style={{ marginTop: 60 }} />
        ) : (
          <Row gutter={[16, 16]}>
            {results.map((item, i) => (
              <Col key={i} xs={24} sm={12} md={8} lg={6}>
                <Card
                  hoverable
                  style={{ borderRadius: 12, height: '100%', position: 'relative' }}
                  bodyStyle={{ padding: 16 }}
                  cover={
                    <div style={{
                      height: 180,
                      background: item.cover_url
                        ? `url(${item.cover_url}) center/cover`
                        : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      borderRadius: '12px 12px 0 0'
                    }}>
                      {!item.cover_url && (
                        <BookOutlined style={{ fontSize: 40, color: 'rgba(255,255,255,0.6)' }} />
                      )}
                      {item.from_source && (
                        <Tag color="green" style={{ position: 'absolute', top: 8, left: 8, fontSize: 11 }}>
                          书源匹配
                        </Tag>
                      )}
                    </div>
                  }
                >
                  <div style={{
                    fontWeight: 600, fontSize: 14, marginBottom: 4,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'
                  }}>
                    {item.title}
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 12, marginBottom: 6 }}>
                    {item.author}
                  </div>
                  {item.description && (
                    <Paragraph
                      style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}
                      ellipsis={{ rows: 2 }}
                    >
                      {item.description}
                    </Paragraph>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 4 }}>
                    <Tag color="purple" style={{ margin: 0, fontSize: 11 }}>{item.source_name}</Tag>
                    <Button
                      type="primary"
                      size="small"
                      icon={<PlusOutlined />}
                      loading={addingIds.has(item.url)}
                      onClick={(e) => { e.stopPropagation(); handleAddBook(item) }}
                    >
                      加入书架
                    </Button>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>
    </div>
  )
}
