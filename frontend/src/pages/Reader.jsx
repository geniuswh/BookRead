import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button, Slider, Select, Switch, Popover, App, Spin } from 'antd'
import {
  ArrowLeftOutlined, ArrowLeftOutlined as PrevOutlined,
  ArrowRightOutlined, SettingOutlined, MenuOutlined,
  FontSizeOutlined, ColumnWidthOutlined
} from '@ant-design/icons'
import { readerAPI } from '../api'

const THEMES = {
  light: { bg: '#ffffff', text: '#333333', name: '默认白' },
  warm: { bg: '#f5f0e1', text: '#5b4636', name: '羊皮纸' },
  green: { bg: '#e0eed2', text: '#3a5a2b', name: '护眼绿' },
  dark: { bg: '#1a1a2e', text: '#e0e0e0', name: '夜间模式' },
  gray: { bg: '#2d2d2d', text: '#cccccc', name: '灰色暗黑' }
}

const FONTS = [
  { label: 'Noto Serif SC', value: "'Noto Serif SC', serif" },
  { label: '宋体', value: "SimSun, serif" },
  { label: '楷体', value: "KaiTi, serif" },
  { label: '黑体', value: "SimHei, sans-serif" },
  { label: '微软雅黑', value: "'Microsoft YaHei', sans-serif" },
  { label: '仿宋', value: "FangSong, serif" }
]

export default function Reader() {
  const { bookId, chapterId } = useParams()
  const navigate = useNavigate()
  const { message } = App.useApp()
  const contentRef = useRef(null)
  const saveTimerRef = useRef(null)

  const [chapter, setChapter] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)

  // 阅读偏好
  const [prefs, setPrefs] = useState({
    font_family: "'Noto Serif SC', serif",
    font_size: 18,
    line_height: 1.8,
    letter_spacing: 0.5,
    paragraph_spacing: 16,
    page_width: 800,
    theme: 'light'
  })

  useEffect(() => {
    loadPrefs()
  }, [])

  useEffect(() => {
    loadChapter()
  }, [chapterId])

  const loadPrefs = async () => {
    try {
      const { data } = await readerAPI.getPreferences()
      setPrefs(prev => ({ ...prev, ...data }))
    } catch { /* use defaults */ }
  }

  const loadChapter = async () => {
    setLoading(true)
    try {
      const { data } = await readerAPI.getChapter(chapterId)
      setChapter(data)
      if (contentRef.current) contentRef.current.scrollTop = 0
      // 保存进度
      readerAPI.saveProgress(bookId, {
        chapter_id: parseInt(chapterId),
        chapter_index: data.chapter_index
      }).catch(() => {})
    } catch (err) {
      message.error('加载章节失败')
    } finally {
      setLoading(false)
    }
  }

  const savePrefs = useCallback(async (newPrefs) => {
    try {
      await readerAPI.updatePreferences(newPrefs)
    } catch { /* ignore */ }
  }, [])

  const updatePref = (key, value) => {
    const newPrefs = { ...prefs, [key]: value }
    setPrefs(newPrefs)
    // 防抖保存
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => savePrefs(newPrefs), 1000)
  }

  const handleScroll = useCallback(() => {
    if (!contentRef.current) return
    const el = contentRef.current
    const scrollPercent = el.scrollTop / (el.scrollHeight - el.clientHeight)
    // 防抖保存滚动位置
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => {
      readerAPI.saveProgress(bookId, { scroll_position: scrollPercent }).catch(() => {})
    }, 2000)
  }, [bookId])

  // 恢复滚动位置
  useEffect(() => {
    if (!chapter || !contentRef.current) return
    const restoreScroll = async () => {
      try {
        const { data } = await readerAPI.getProgress(bookId)
        if (data.scroll_position && contentRef.current) {
          const el = contentRef.current
          el.scrollTop = data.scroll_position * (el.scrollHeight - el.clientHeight)
        }
      } catch { /* ignore */ }
    }
    setTimeout(restoreScroll, 100)
  }, [chapter])

  const theme = THEMES[prefs.theme] || THEMES.light

  const renderContent = () => {
    if (!chapter?.content) return '内容为空'
    const paragraphs = chapter.content.split('\n').filter(p => p.trim())
    return paragraphs.map((p, i) => (
      <p key={i} style={{
        textIndent: '2em', margin: 0,
        marginBottom: `${prefs.paragraph_spacing}px`
      }}>{p}</p>
    ))
  }

  const SettingsPanel = () => (
    <div style={{ width: 300, padding: 8 }}>
      <h4 style={{ marginBottom: 12 }}>阅读设置</h4>

      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>主题</label>
        <div style={{ display: 'flex', gap: 6 }}>
          {Object.entries(THEMES).map(([key, t]) => (
            <div key={key} onClick={() => updatePref('theme', key)}
                 style={{
                   width: 36, height: 36, borderRadius: 8, cursor: 'pointer',
                   background: t.bg, border: prefs.theme === key ? '2px solid var(--primary)' : '2px solid #e2e8f0',
                   display: 'flex', alignItems: 'center', justifyContent: 'center',
                   fontSize: 10, color: t.text, fontWeight: 600
                 }}>
              {t.name.slice(0, 1)}
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>字体</label>
        <Select value={prefs.font_family} onChange={v => updatePref('font_family', v)}
                options={FONTS} style={{ width: '100%' }} size="small" />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between' }}>
          字号 <span>{prefs.font_size}px</span>
        </label>
        <Slider min={12} max={32} value={prefs.font_size}
                onChange={v => updatePref('font_size', v)} />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between' }}>
          行高 <span>{prefs.line_height}</span>
        </label>
        <Slider min={1.2} max={3} step={0.1} value={prefs.line_height}
                onChange={v => updatePref('line_height', v)} />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between' }}>
          字间距 <span>{prefs.letter_spacing}px</span>
        </label>
        <Slider min={0} max={5} step={0.5} value={prefs.letter_spacing}
                onChange={v => updatePref('letter_spacing', v)} />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between' }}>
          段间距 <span>{prefs.paragraph_spacing}px</span>
        </label>
        <Slider min={4} max={40} value={prefs.paragraph_spacing}
                onChange={v => updatePref('paragraph_spacing', v)} />
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between' }}>
          页面宽度 <span>{prefs.page_width}px</span>
        </label>
        <Slider min={500} max={1200} step={50} value={prefs.page_width}
                onChange={v => updatePref('page_width', v)} />
      </div>
    </div>
  )

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <Spin size="large" />
    </div>
  )

  return (
    <div style={{
      background: theme.bg, minHeight: '100vh',
      transition: 'background 0.3s, color 0.3s'
    }}>
      {/* 顶部工具栏 */}
      <div style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
        background: theme.bg, borderBottom: `1px solid ${prefs.theme === 'dark' || prefs.theme === 'gray' ? '#333' : '#e2e8f0'}`,
        padding: '8px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        transition: 'background 0.3s'
      }}>
        <Button type="text" icon={<ArrowLeftOutlined />}
                onClick={() => navigate(`/book/${bookId}`)}
                style={{ color: theme.text }}>
          返回
        </Button>

        <span style={{ color: theme.text, fontWeight: 500, fontSize: 14 }}>
          {chapter?.book_title} - {chapter?.title}
        </span>

        <div style={{ display: 'flex', gap: 4 }}>
          <Popover content={SettingsPanel} trigger="click" placement="bottomRight">
            <Button type="text" icon={<SettingOutlined />} style={{ color: theme.text }} />
          </Popover>
        </div>
      </div>

      {/* 内容区域 */}
      <div ref={contentRef} onScroll={handleScroll}
           style={{
             maxWidth: `${prefs.page_width}px`, margin: '0 auto',
             padding: '60px 24px 80px', color: theme.text,
             fontFamily: prefs.font_family,
             fontSize: `${prefs.font_size}px`,
             lineHeight: prefs.line_height,
             letterSpacing: `${prefs.letter_spacing}px`,
             overflowY: 'auto', height: '100vh',
             transition: 'all 0.3s'
           }}>
        <h2 style={{
          textAlign: 'center', marginBottom: 32,
          fontSize: `${prefs.font_size + 6}px`,
          fontWeight: 700, color: theme.text
        }}>
          {chapter?.title}
        </h2>
        {renderContent()}
      </div>

      {/* 底部导航 */}
      <div style={{
        position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 100,
        background: theme.bg, borderTop: `1px solid ${prefs.theme === 'dark' || prefs.theme === 'gray' ? '#333' : '#e2e8f0'}`,
        padding: '8px 16px', display: 'flex', justifyContent: 'center', gap: 16,
        transition: 'background 0.3s'
      }}>
        <Button disabled={!chapter?.prev_chapter_id}
                onClick={() => navigate(`/read/${bookId}/${chapter.prev_chapter_id}`)}
                icon={<ArrowLeftOutlined />} style={{ minWidth: 120 }}>
          上一章
        </Button>
        <span style={{ color: theme.text, lineHeight: '32px', fontSize: 13 }}>
          {chapter?.chapter_index + 1} / {chapter?.total_chapters}
        </span>
        <Button disabled={!chapter?.next_chapter_id}
                onClick={() => navigate(`/read/${bookId}/${chapter.next_chapter_id}`)}
                style={{ minWidth: 120 }}>
          下一章 <ArrowRightOutlined />
        </Button>
      </div>
    </div>
  )
}
