import axios from 'axios'

const api = axios.create({
    baseURL: '/api',
    timeout: 30000
})

api.interceptors.request.use(config => {
    const token = localStorage.getItem('token')
    if (token) {
        config.headers.Authorization = `Bearer ${token}`
    }
    return config
})

api.interceptors.response.use(
    res => res,
    err => {
        if (err.response?.status === 401) {
            localStorage.removeItem('token')
            localStorage.removeItem('user')
            window.location.href = '/login'
        }
        return Promise.reject(err)
    }
)

// Auth
export const authAPI = {
    register: (data) => api.post('/auth/register', data),
    login: (data) => api.post('/auth/login', data),
    getMe: () => api.get('/auth/me'),
    updateMe: (data) => api.put('/auth/me', data)
}

// Books
export const booksAPI = {
    getSources: () => api.get('/books/sources'),
    addSource: (data) => api.post('/books/sources', data),
    updateSource: (id, data) => api.put(`/books/sources/${id}`, data),
    deleteSource: (id) => api.delete(`/books/sources/${id}`),
    crawlSource: (id, speed) => api.post(`/books/sources/${id}/crawl`, speed ? { speed } : {}, { timeout: 600000 }),
    getBooks: (params) => api.get('/books/list', { params }),
    getBook: (id) => api.get(`/books/${id}`),
    deleteBook: (id) => api.delete(`/books/${id}`),
    getCategories: () => api.get('/books/categories'),
    // 爬虫配置
    setProxies: (proxies) => api.post('/books/config/proxies', { proxies }),
    setSpeed: (speed) => api.post('/books/config/speed', { speed }),
    getCrawlStatus: () => api.get('/books/config/status'),
    // 搜索换源
    searchSources: (bookId) => api.get(`/books/${bookId}/search-sources`, { timeout: 60000 }),
    switchSource: (bookId, data) => api.post(`/books/${bookId}/switch-source`, data),
    // 搜书
    searchBooks: (keyword) => api.get('/books/search', { params: { keyword }, timeout: 60000 }),
    addBookFromSearch: (data) => api.post('/books/search/add', data, { timeout: 120000 }),
    // 分组
    getGroups: () => api.get('/books/groups'),
    addGroup: (data) => api.post('/books/groups', data),
    updateGroup: (id, data) => api.put(`/books/groups/${id}`, data),
    deleteGroup: (id) => api.delete(`/books/groups/${id}`),
    setBookGroup: (bookId, data) => api.put(`/books/${bookId}/group`, data),
    // 导出TXT
    exportBookTxt: (bookId) => api.get(`/books/${bookId}/export`, { timeout: 300000, responseType: 'blob' }),
}

// Reader
export const readerAPI = {
    getPreferences: () => api.get('/reader/preferences'),
    updatePreferences: (data) => api.put('/reader/preferences', data),
    getChapter: (id) => api.get(`/reader/chapter/${id}`),
    getProgress: (bookId) => api.get(`/reader/progress/${bookId}`),
    saveProgress: (bookId, data) => api.post(`/reader/progress/${bookId}`, data)
}

export default api
