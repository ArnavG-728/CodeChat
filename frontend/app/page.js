'use client'

import { useState, useEffect, useRef, useCallback, useMemo, memo } from 'react'
import axios from 'axios'
import { Send, Github, Database, Code2, Loader2, MessageSquare, Info, Plus, Trash2, CheckCircle, XCircle, AlertCircle, Settings, Activity, RefreshCw, Trash, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import AnimatedList from '@/components/AnimatedList'
import Button from '@/components/Button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/Card'
import Badge from '@/components/Badge'
import Input from '@/components/Input'
import { Alert, AlertIcon, AlertTitle, AlertDescription } from '@/components/Alert'
import { ThemeToggle } from '@/components/ThemeToggle'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Chat storage key for session storage
const CHAT_STORAGE_KEY = 'codechat_messages'

// Refresh strategy constants
const REFRESH_INTERVALS = {
  HEALTH: 10000,        // 10 seconds
  REPOS_IDLE: 30000,    // 30 seconds when idle
  REPOS_ACTIVE: 5000,   // 5 seconds when processing
  STATS: 15000,         // 15 seconds
}

// Debounce utility for performance
function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// Axios instance with timeout
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
})

export default function HomePage() {
  // Initialize messages from session storage
  const [messages, setMessages] = useState([])
  const [isHydrated, setIsHydrated] = useState(false)

  // Load messages from sessionStorage only after hydration
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(CHAT_STORAGE_KEY)
      setMessages(stored ? JSON.parse(stored) : [])
    } catch (error) {
      console.error('Error loading chat history:', error)
    }
    setIsHydrated(true)
  }, [])
  
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [repositories, setRepositories] = useState([])
  const [selectedRepo, setSelectedRepo] = useState(null)
  const [stats, setStats] = useState(null)
  const [health, setHealth] = useState(null)
  const [showAddRepo, setShowAddRepo] = useState(false)
  const [newRepoUrl, setNewRepoUrl] = useState('')
  const [addingRepo, setAddingRepo] = useState(false)
  const [processingStatus, setProcessingStatus] = useState({})
  const [lastRefresh, setLastRefresh] = useState({})
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState(null)
  const messagesEndRef = useRef(null)
  const wsRef = useRef(null)
  const healthIntervalRef = useRef(null)
  const reposIntervalRef = useRef(null)
  const statsIntervalRef = useRef(null)

  // Smart refresh strategy: Adaptive polling based on activity
  useEffect(() => {
    // Initial fetch
    fetchRepositories()
    fetchHealth()
    connectWebSocket()
    
    // Health check - constant interval
    healthIntervalRef.current = setInterval(fetchHealth, REFRESH_INTERVALS.HEALTH)
    
    // Repositories - adaptive interval based on processing activity
    const setupReposInterval = () => {
      if (reposIntervalRef.current) clearInterval(reposIntervalRef.current)
      
      const hasActiveProcessing = Object.values(processingStatus).some(status =>
        status?.status === 'pending' || status?.status === 'loading' || 
        status?.status === 'parsing' || status?.status === 'ingesting' ||
        status?.status === 'embeddings' || status?.status === 'summaries'
      )
      
      const interval = hasActiveProcessing ? REFRESH_INTERVALS.REPOS_ACTIVE : REFRESH_INTERVALS.REPOS_IDLE
      reposIntervalRef.current = setInterval(fetchRepositories, interval)
    }
    
    setupReposInterval()
    
    // Stats refresh when repo selected
    if (selectedRepo) {
      statsIntervalRef.current = setInterval(() => fetchStats(selectedRepo), REFRESH_INTERVALS.STATS)
    }
    
    return () => {
      if (healthIntervalRef.current) clearInterval(healthIntervalRef.current)
      if (reposIntervalRef.current) clearInterval(reposIntervalRef.current)
      if (statsIntervalRef.current) clearInterval(statsIntervalRef.current)
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [selectedRepo, processingStatus])

  // Save messages to session storage whenever they change
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages))
      } catch (error) {
        console.error('Error saving chat history:', error)
      }
    }
  }, [messages])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const connectWebSocket = () => {
    try {
      const wsUrl = API_BASE_URL.replace('http', 'ws') + '/ws'
      const ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        console.log('WebSocket connected')
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'repository_status') {
            setProcessingStatus(prev => ({
              ...prev,
              [data.data.repository]: data.data
            }))
            // Refresh repositories list when processing completes
            if (data.data.status === 'complete') {
              fetchRepositories()
            }
          }
        } catch (e) {
          console.error('WebSocket message error:', e)
        }
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
      
      ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting...')
        setTimeout(connectWebSocket, 3000)
      }
      
      wsRef.current = ws
    } catch (error) {
      console.error('WebSocket connection error:', error)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const fetchHealth = useCallback(async () => {
    try {
      const response = await api.get('/api/health')
      setHealth(response.data)
      setLastRefresh(prev => ({ ...prev, health: Date.now() }))
      setRefreshError(null)
    } catch (error) {
      console.error('Error fetching health:', error)
      setHealth({
        status: 'error',
        components: {},
        timestamp: new Date().toISOString()
      })
      setRefreshError('Failed to fetch health status')
    }
  }, [])

  const fetchRepositories = useCallback(async () => {
    try {
      const response = await api.get('/api/repositories')
      setRepositories(response.data.repositories)
      setLastRefresh(prev => ({ ...prev, repositories: Date.now() }))
      setRefreshError(null)
      
      if (response.data.repositories.length > 0 && !selectedRepo) {
        const firstRepo = response.data.repositories[0]
        setSelectedRepo(firstRepo.name)
        fetchStats(firstRepo.name)
      }
    } catch (error) {
      console.error('Error fetching repositories:', error)
      setRefreshError('Failed to fetch repositories')
    }
  }, [])

  const fetchStats = useCallback(async (repoName) => {
    if (!repoName) return
    try {
      const response = await api.get(`/api/repositories/${repoName}/stats`)
      setStats(response.data)
      setLastRefresh(prev => ({ ...prev, stats: Date.now() }))
      setRefreshError(null)
    } catch (error) {
      console.error('Error fetching stats:', error)
      setRefreshError('Failed to fetch repository stats')
    }
  }, [])

  // Manual refresh function
  const handleManualRefresh = async () => {
    setIsRefreshing(true)
    try {
      await Promise.all([
        fetchRepositories(),
        fetchHealth(),
        selectedRepo && fetchStats(selectedRepo)
      ])
    } finally {
      setIsRefreshing(false)
    }
  }

  // Get time since last refresh
  const getTimeSinceRefresh = (key) => {
    const lastTime = lastRefresh[key]
    if (!lastTime) return 'Never'
    
    const seconds = Math.floor((Date.now() - lastTime) / 1000)
    if (seconds < 60) return `${seconds}s ago`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
    return `${Math.floor(seconds / 3600)}h ago`
  }

  // Clear chat history
  const handleClearChat = () => {
    if (confirm('Are you sure you want to clear the chat history? This cannot be undone.')) {
      setMessages([])
      if (typeof window !== 'undefined') {
        try {
          sessionStorage.removeItem(CHAT_STORAGE_KEY)
        } catch (error) {
          console.error('Error clearing chat history:', error)
        }
      }
    }
  }

  const handleRepoChange = (repoName) => {
    setSelectedRepo(repoName)
    fetchStats(repoName)
  }

  const parseGitUrl = (input) => {
    // Parse various GitHub URL formats to owner/repo-name format
    let url = input.trim()
    
    // If it's already in owner/repo format, return as is
    if (url.match(/^[a-zA-Z0-9_-]+\/[a-zA-Z0-9_-]+$/)) {
      return url
    }
    
    // Remove .git suffix if present
    url = url.replace(/\.git$/, '')
    
    // Extract from full GitHub URLs
    // https://github.com/owner/repo-name
    // git@github.com:owner/repo-name
    const githubMatch = url.match(/github\.com[/:]([\w-]+)\/([\w-]+)/)
    if (githubMatch) {
      return `${githubMatch[1]}/${githubMatch[2]}`
    }
    
    return url
  }

  const handleAddRepository = async () => {
    if (!newRepoUrl.trim() || addingRepo) return
    
    setAddingRepo(true)
    try {
      // Parse the URL to get owner/repo format
      const parsedUrl = parseGitUrl(newRepoUrl)
      
      await axios.post(`${API_BASE_URL}/api/repositories`, {
        repo_url: parsedUrl,
        branch: 'main'
      })
      
      setNewRepoUrl('')
      setShowAddRepo(false)
      
      // Show success message
      alert('Repository added! Processing will start in the background.')
    } catch (error) {
      alert(error.response?.data?.detail || 'Error adding repository')
    } finally {
      setAddingRepo(false)
    }
  }

  const handleDeleteRepository = async (repoDbName) => {
    if (!confirm('Are you sure you want to delete this repository?')) return
    
    try {
      await axios.delete(`${API_BASE_URL}/api/repositories/${repoDbName}`)
      
      // Clear selection if deleted repo was selected
      if (selectedRepo === repoDbName) {
        setSelectedRepo(null)
        setStats(null)
      }
      
      fetchRepositories()
    } catch (error) {
      alert(error.response?.data?.detail || 'Error deleting repository')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!query.trim() || loading) return

    const userMessage = {
      type: 'user',
      content: query
    }

    setMessages(prev => [...prev, userMessage])
    setQuery('')
    setLoading(true)

    try {
      const response = await axios.post(`${API_BASE_URL}/api/query`, {
        query: query,
        top_k: 5,
        repository: selectedRepo
      })

      const aiMessage = {
        type: 'ai',
        content: response.data.answer,
        sources: response.data.sources
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      console.error('Error querying:', error)
      const errorMessage = {
        type: 'error',
        content: 'Sorry, there was an error processing your request. Please try again.'
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected':
      case 'configured':
      case 'ready':
        return <CheckCircle className="w-3 h-3 text-green-500" />
      case 'disconnected':
      case 'not_configured':
        return <XCircle className="w-3 h-3 text-red-500" />
      default:
        return <AlertCircle className="w-3 h-3 text-yellow-500" />
    }
  }

  const getOverallStatus = () => {
    if (!health) return { color: 'gray', text: 'Checking...' }
    if (health.status === 'healthy') return { color: 'green', text: 'All Systems Online' }
    if (health.status === 'degraded') return { color: 'yellow', text: 'Partial Outage' }
    return { color: 'red', text: 'System Error' }
  }

  const overallStatus = getOverallStatus()

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar */}
      <div className="w-80 bg-white dark:bg-black border-r border-border dark:border-red-900 flex flex-col shadow-sm">
        {/* Header */}
        <div className="p-5 border-b border-border dark:border-red-900">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-gradient-to-br from-blue-500 to-blue-600 dark:from-red-700 dark:to-red-600 rounded-xl shadow-md">
                <Code2 className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">CodeChat</h1>
                <p className="text-xs text-gray-500 dark:text-gray-400">By Arnav Gupta</p>
              </div>
            </div>
            {/* Manual Refresh Button */}
            <button
              onClick={handleManualRefresh}
              disabled={isRefreshing}
              title="Refresh all data"
              className={cn(
                "p-2 rounded-lg transition-all duration-200",
                isRefreshing
                  ? "bg-blue-50 text-blue-600 dark:bg-red-950 dark:text-red-400 cursor-not-allowed"
                  : "hover:bg-gray-100 dark:hover:bg-red-950 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-red-400"
              )}
            >
              <RefreshCw className={cn("w-5 h-5", isRefreshing && "animate-spin")} />
            </button>
          </div>
          
          {/* Refresh Status */}
          {refreshError && (
            <div className="mb-3 p-2.5 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-900 rounded-lg text-xs text-red-700 dark:text-red-300 animate-slide-in-down">
              ⚠️ {refreshError}
            </div>
          )}
          
          {/* Last Refresh Info */}
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-3 flex items-center justify-between">
            <span>Last updated: {getTimeSinceRefresh('repositories')}</span>
          </div>

          {/* Connection Status */}
          <div className="relative group">
            <div className={cn(
              "flex items-center gap-2 px-3.5 py-2.5 rounded-lg cursor-pointer transition-all duration-200 border",
              overallStatus.color === 'green' ? "bg-green-50 border-green-200 hover:bg-green-100" : 
              overallStatus.color === 'yellow' ? "bg-yellow-50 border-yellow-200 hover:bg-yellow-100" : 
              "bg-red-50 border-red-200 hover:bg-red-100"
            )}>
              <div className={cn(
                "w-2 h-2 rounded-full animate-pulse-soft",
                overallStatus.color === 'green' ? "bg-green-500" : overallStatus.color === 'yellow' ? "bg-yellow-500" : "bg-red-500"
              )}></div>
              <span className="text-xs font-medium text-gray-700 flex-1">{overallStatus.text}</span>
              <Settings className="w-3.5 h-3.5 text-gray-400" />
            </div>

            {/* Tooltip */}
            <div className="absolute left-0 top-full mt-2 w-72 bg-white dark:bg-black rounded-xl shadow-lg border border-border dark:border-red-900 p-4 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50 animate-scale-in">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">System Components</h3>
              <div className="space-y-2">
                {health && Object.entries(health.components).map(([name, component]) => (
                  <div key={name} className="flex items-start gap-2 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-red-950 transition-colors">
                    {getStatusIcon(component.status)}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-gray-900 dark:text-gray-100 capitalize">{name}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{component.message}</p>
                    </div>
                  </div>
                ))}
              </div>
              {health && (
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-3 pt-3 border-t border-border dark:border-red-900">
                  Last checked: {new Date(health.timestamp).toLocaleTimeString()}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between px-5 py-4 border-b border-border dark:border-red-900">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <Database className="w-4 h-4 text-gray-600 dark:text-red-400" />
            Repositories
          </h2>
          <button
            onClick={() => setShowAddRepo(true)}
            className="p-1.5 hover:bg-blue-50 dark:hover:bg-red-950 rounded-lg transition-all duration-200 text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-red-400"
            title="Add Repository"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* Repositories Section */}
        <div className="flex-1 overflow-y-auto p-2">
          <div>
            {/* Add Repository Modal */}
            {showAddRepo && (
              <Card className="mb-4 border-blue-200 dark:border-red-900 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-red-950 dark:to-black animate-slide-in-down">
                <CardHeader className="border-b border-blue-200 dark:border-red-900 pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base text-gray-900 dark:text-gray-100">Add GitHub Repository</CardTitle>
                    <button
                      onClick={() => setShowAddRepo(false)}
                      disabled={addingRepo}
                      className="p-1.5 hover:bg-blue-200 dark:hover:bg-red-900 rounded-lg transition-all duration-200"
                    >
                      <X className="w-4 h-4 text-gray-600" />
                    </button>
                  </div>
                </CardHeader>
                <CardContent className="pt-4">
                  <Input
                    value={newRepoUrl}
                    onChange={(e) => setNewRepoUrl(e.target.value)}
                    placeholder="facebook/react or https://github.com/facebook/react.git"
                    disabled={addingRepo}
                    className="mb-3"
                  />
                  <p className="text-xs text-gray-600 dark:text-gray-400 mb-4">
                    💡 Any format works: owner/repo, full URL, or .git URL
                  </p>
                  <div className="flex gap-2">
                    <Button
                      onClick={handleAddRepository}
                      disabled={addingRepo || !newRepoUrl.trim()}
                      size="sm"
                    >
                      {addingRepo ? (
                        <>
                          <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                          Adding...
                        </>
                      ) : (
                        <>
                          <Plus className="w-3 h-3 mr-1" />
                          Add
                        </>
                      )}
                    </Button>
                    <Button
                      onClick={() => setShowAddRepo(false)}
                      disabled={addingRepo}
                      variant="outline"
                      size="sm"
                    >
                      Cancel
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Repository List */}
            {repositories.length === 0 ? (
              <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-12 animate-fade-in">
                <div className="w-16 h-16 bg-gray-100 dark:bg-black rounded-full flex items-center justify-center mx-auto mb-3 border dark:border-red-900">
                  <Database className="w-8 h-8 text-gray-400 dark:text-gray-500" />
                </div>
                <p className="text-gray-600 dark:text-gray-400 font-medium">No repositories loaded</p>
                <button
                  onClick={() => setShowAddRepo(true)}
                  className="mt-3 text-blue-600 hover:text-blue-700 dark:text-red-400 dark:hover:text-red-300 text-xs font-medium transition-colors"
                >
                  Add your first repository
                </button>
              </div>
            ) : (
              <AnimatedList
                items={repositories}
                onItemSelect={(repo) => handleRepoChange(repo.name)}
                showGradients={true}
                enableArrowNavigation={true}
                displayScrollbar={true}
                className="flex-1"
                itemClassName="repo-item"
                initialSelectedIndex={repositories.findIndex(r => r.name === selectedRepo)}
              >
                {(repo) => (
                  <div className="w-full">
                    <div className="flex items-center gap-2">
                      <Github className="w-4 h-4 flex-shrink-0" />
                      <span className="truncate text-sm font-medium">{repo.name}</span>
                      {processingStatus[repo.name]?.status === 'pending' ||
                       processingStatus[repo.name]?.status === 'loading' ||
                       processingStatus[repo.name]?.status === 'parsing' ||
                       processingStatus[repo.name]?.status === 'ingesting' ||
                       processingStatus[repo.name]?.status === 'embeddings' ||
                       processingStatus[repo.name]?.status === 'summaries' ? (
                        <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
                      ) : null}
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteRepository(repo.name)
                        }}
                        className="ml-auto p-1 opacity-0 hover:opacity-100 hover:bg-red-50 rounded transition-all"
                        title="Delete Repository"
                      >
                        <Trash2 className="w-3 h-3 text-red-600" />
                      </button>
                    </div>
                    {repo.stats && (
                      <div className="text-xs ">
                        {repo.stats.files} files • {repo.stats.functions} functions
                      </div>
                    )}
                    {processingStatus[repo.name] && (
                      <div className="mt-1">
                        <div className="flex items-center gap-2 text-sm px-3 py-1.5 rounded-lg bg-gray-50 dark:bg-black dark:border dark:border-red-900">
                          <Activity className="w-3 h-3" />
                          <span>{processingStatus[repo.name].message}</span>
                        </div>
                        <div className="mt-1 h-1 bg-gray-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-600 transition-all duration-300"
                            style={{ width: `${processingStatus[repo.name].progress}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </AnimatedList>
            )}
          </div>

        </div>
        {/* Stats Card */}
        {stats && (
          <Card className="mx-2 mb-3 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-red-950 dark:to-black border-blue-200 dark:border-red-900 animate-slide-in-up">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2 text-gray-900 dark:text-gray-100">
                <Info className="w-4 h-4 text-blue-600 dark:text-red-400" />
                Repository Stats
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5">
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-600 dark:text-gray-400">Files</span>
                <Badge variant="default">{stats.file_count}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-600 dark:text-gray-400">Classes</span>
                <Badge variant="default">{stats.class_count}</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-600 dark:text-gray-400">Functions</span>
                <Badge variant="default">{stats.function_count}</Badge>
              </div>
              <div className="pt-2.5 mt-2.5 border-t border-blue-200 dark:border-red-900 flex justify-between items-center">
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Total Nodes</span>
                <Badge variant="success">{stats.total_nodes}</Badge>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Footer */}
        <div className="px-5 py-3 border-t border-border dark:border-red-900 bg-gray-50 dark:bg-black">
          <p className="text-xs text-gray-500 dark:text-gray-500 text-center">
            Powered by Neo4j & Gemini
          </p>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-background">
        {/* Header */}
        <div className="bg-white dark:bg-black border-b border-border px-7 py-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                {selectedRepo ? repositories.find(r => r.name === selectedRepo)?.name || selectedRepo : 'Select a Repository'}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                Ask questions about your codebase
              </p>
            </div>
            <div className="flex items-center gap-4">
              {/* Theme Toggle */}
              <ThemeToggle />
              
              {/* Clear Chat Button */}
              {isHydrated && messages.length > 0 && (
                <button
                  onClick={handleClearChat}
                  title="Clear chat history"
                  className="p-2.5 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg transition-all duration-200 text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                >
                  <Trash className="w-5 h-5" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-7 space-y-5">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center animate-fade-in">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-red-950 dark:to-black rounded-full flex items-center justify-center mb-5 shadow-md border dark:border-red-900">
                <MessageSquare className="w-10 h-10 text-blue-600 dark:text-red-400" />
              </div>
              <h3 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">Start a conversation</h3>
              <p className="text-gray-500 dark:text-gray-400 max-w-md mb-8">
                Ask questions about your code structure, functions, classes, or implementation details.
              </p>
              {selectedRepo && (
                <div className="grid grid-cols-1 gap-3 w-full max-w-2xl">
                  <button
                    onClick={() => setQuery("What are the main functions in this repository?")}
                    className="text-left p-4 bg-white dark:bg-black rounded-xl border border-border dark:border-red-900 hover:border-blue-300 dark:hover:border-red-800 hover:bg-blue-50 dark:hover:bg-red-950 transition-all duration-200 shadow-sm hover:shadow-md"
                  >
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">What are the main functions?</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5">Explore the repository structure</p>
                  </button>
                  <button
                    onClick={() => setQuery("Explain the main classes and their purposes")}
                    className="text-left p-4 bg-white dark:bg-black rounded-xl border border-border dark:border-red-900 hover:border-blue-300 dark:hover:border-red-800 hover:bg-blue-50 dark:hover:bg-red-950 transition-all duration-200 shadow-sm hover:shadow-md"
                  >
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">Explain the main classes</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5">Understand the architecture</p>
                  </button>
                </div>
              )}
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={cn(
                  "flex gap-4 animate-slide-in-up",
                  message.type === 'user' ? "justify-end" : "justify-start"
                )}
              >
                {message.type !== 'user' && (
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 dark:from-red-600 dark:to-red-700 flex items-center justify-center flex-shrink-0 shadow-md">
                    <Code2 className="w-5 h-5 text-white" />
                  </div>
                )}
                <div
                  className={cn(
                    "max-w-3xl rounded-2xl px-6 py-4 transition-all duration-200",
                    message.type === 'user'
                      ? "bg-gradient-to-br from-blue-500 to-blue-600 dark:from-red-600 dark:to-red-700 text-white shadow-md"
                      : message.type === 'error'
                      ? "bg-red-50 dark:bg-red-950 text-red-900 dark:text-red-300 border border-red-200 dark:border-red-900 shadow-sm"
                      : "bg-white dark:bg-black shadow-md border border-border dark:border-red-900 dark:text-gray-200"
                  )}
                >
                  <div className="markdown-content">
                    {message.type === 'user' ? (
                      <div className="whitespace-pre-wrap">{message.content}</div>
                    ) : (
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                          h1: ({node, ...props}) => <h1 {...props} />,
                          h2: ({node, ...props}) => <h2 {...props} />,
                          h3: ({node, ...props}) => <h3 {...props} />,
                          h4: ({node, ...props}) => <h4 {...props} />,
                          h5: ({node, ...props}) => <h5 {...props} />,
                          h6: ({node, ...props}) => <h6 {...props} />,
                          p: ({node, ...props}) => <p {...props} />,
                          ul: ({node, ...props}) => <ul {...props} />,
                          ol: ({node, ...props}) => <ol {...props} />,
                          li: ({node, ...props}) => <li {...props} />,
                          code: ({node, inline, ...props}) => 
                            inline ? <code {...props} /> : <code {...props} />,
                          pre: ({node, ...props}) => <pre {...props} />,
                          blockquote: ({node, ...props}) => <blockquote {...props} />,
                          a: ({node, ...props}) => <a {...props} />,
                          table: ({node, ...props}) => <table {...props} />,
                          thead: ({node, ...props}) => <thead {...props} />,
                          tbody: ({node, ...props}) => <tbody {...props} />,
                          tr: ({node, ...props}) => <tr {...props} />,
                          th: ({node, ...props}) => <th {...props} />,
                          td: ({node, ...props}) => <td {...props} />,
                          hr: ({node, ...props}) => <hr {...props} />,
                          strong: ({node, ...props}) => <strong {...props} />,
                          em: ({node, ...props}) => <em {...props} />,
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    )}
                  </div>
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-border dark:border-red-900">
                      <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-3">📚 Sources</p>
                      <div className="space-y-2">
                        {message.sources.slice(0, 3).map((source, idx) => (
                          <div
                            key={idx}
                            className="text-xs bg-gray-50 dark:bg-black rounded-lg p-3 border border-gray-100 dark:border-red-900 hover:bg-gray-100 dark:hover:bg-red-950 hover:border-gray-200 dark:hover:border-red-800 transition-all duration-200 cursor-pointer"
                          >
                            <div className="flex items-center gap-2 mb-1.5">
                              <span className="font-semibold text-gray-900 dark:text-gray-100">{source.name}</span>
                              <span className="text-gray-500 dark:text-red-200 text-xs px-2 py-0.5 bg-gray-200 dark:bg-red-900 rounded">({source.type})</span>
                            </div>
                            <p className="text-gray-600 dark:text-gray-300 line-clamp-2">{source.summary}</p>
                            <p className="text-gray-400 dark:text-gray-500 mt-1.5">⭐ {source.score.toFixed(4)}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                {message.type === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-semibold text-gray-700">U</span>
                  </div>
                )}
              </div>
            ))
          )}
          {loading && (
            <div className="flex gap-4 animate-slide-in-up">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 dark:from-red-600 dark:to-red-700 flex items-center justify-center shadow-md">
                <Loader2 className="w-5 h-5 text-white animate-spin" />
              </div>
              <div className="bg-white dark:bg-black rounded-2xl px-6 py-4 shadow-md border border-border dark:border-red-900">
                <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm font-medium">Thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="bg-white dark:bg-black border-t border-border dark:border-red-900 px-7 py-5 shadow-sm">
          <form onSubmit={handleSubmit} className="mx-auto">
            <div className="flex gap-3">
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  // Send on Enter (without Shift)
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSubmit(e)
                  }
                  // Allow Shift+Enter for new line (default behavior)
                }}
                placeholder="Ask a question about your code... (Enter to send, Shift+Enter for new line)"
                className="flex-1 px-4 py-3 border border-border dark:border-red-900 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-red-600 focus:border-transparent resize-none transition-all duration-200 bg-white dark:bg-black dark:text-gray-100 dark:placeholder:text-gray-500"
                disabled={loading || !selectedRepo}
                rows={3}
              />
              <button
                type="submit"
                disabled={loading || !query.trim() || !selectedRepo}
                className={cn(
                  "px-6 py-3 rounded-xl font-semibold transition-all duration-200 flex items-center gap-2 h-fit shadow-md hover:shadow-lg",
                  loading || !query.trim() || !selectedRepo
                    ? "bg-gray-200 text-gray-500 cursor-not-allowed"
                    : "bg-gradient-to-br from-blue-500 to-blue-600 dark:from-red-600 dark:to-red-700 text-white hover:from-blue-600 hover:to-blue-700 dark:hover:from-red-700 dark:hover:to-red-800"
                )}
              >
                {loading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
                Send
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
