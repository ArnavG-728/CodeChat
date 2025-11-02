'use client'

import { useState, useRef, useEffect } from 'react'
import { Code2, Database, Plus, X, RefreshCw, Settings, Github, Zap, MoreVertical } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardHeader, CardTitle, CardContent } from './Card'
import { Button } from './Button'
import { Input } from './Input'
import { Badge } from './Badge'

/**
 * Enhanced Sidebar Component using React Bits Registry patterns
 * Features:
 * - Smooth animations and transitions
 * - Interactive hover effects
 * - Status indicators with animations
 * - Responsive design
 * - Modern glassmorphism effects
 */

export default function SidebarUpgraded({
  repositories = [],
  selectedRepo = null,
  onRepoSelect = () => {},
  onAddRepo = () => {},
  onRefresh = () => {},
  isRefreshing = false,
  health = null,
  stats = null,
  showAddRepo = false,
  onShowAddRepo = () => {},
  processingStatus = {},
}) {
  const [hoveredRepo, setHoveredRepo] = useState(null)
  const [mouseX, setMouseX] = useState(0)
  const sidebarRef = useRef(null)

  // Smooth mouse tracking for enhanced interactions
  const handleMouseMove = (e) => {
    if (sidebarRef.current) {
      const rect = sidebarRef.current.getBoundingClientRect()
      setMouseX(e.clientX - rect.left)
    }
  }

  const getStatusColor = (status) => {
    if (!status) return 'gray'
    if (status === 'healthy') return 'green'
    if (status === 'degraded') return 'yellow'
    return 'red'
  }

  const getStatusIcon = (status) => {
    const statusColor = getStatusColor(status)
    const colors = {
      green: 'bg-green-500',
      yellow: 'bg-yellow-500',
      red: 'bg-red-500',
      gray: 'bg-gray-400',
    }
    return (
      <div className={cn(
        'w-2 h-2 rounded-full animate-pulse-soft',
        colors[statusColor]
      )} />
    )
  }

  const getRepoStatus = (repoName) => {
    const status = processingStatus[repoName]
    if (!status) return null
    
    const statusColors = {
      pending: 'bg-blue-100 text-blue-700 border-blue-200',
      loading: 'bg-blue-100 text-blue-700 border-blue-200',
      parsing: 'bg-purple-100 text-purple-700 border-purple-200',
      ingesting: 'bg-indigo-100 text-indigo-700 border-indigo-200',
      embeddings: 'bg-pink-100 text-pink-700 border-pink-200',
      summaries: 'bg-orange-100 text-orange-700 border-orange-200',
      completed: 'bg-green-100 text-green-700 border-green-200',
      error: 'bg-red-100 text-red-700 border-red-200',
    }

    return (
      <Badge variant="outline" className={cn('text-xs', statusColors[status.status] || statusColors.pending)}>
        {status.status}
      </Badge>
    )
  }

  return (
    <div
      ref={sidebarRef}
      onMouseMove={handleMouseMove}
      className="w-80 bg-gradient-to-b from-white to-gray-50 border-r border-border flex flex-col shadow-sm overflow-hidden"
    >
      {/* Header with Glassmorphism Effect */}
      <div className="relative p-5 border-b border-border backdrop-blur-sm">
        {/* Animated background gradient */}
        <div className="absolute inset-0 opacity-0 hover:opacity-5 transition-opacity duration-300"
          style={{
            background: `radial-gradient(circle at ${mouseX}px 50%, rgba(59, 130, 246, 0.1), transparent)`,
          }}
        />

        <div className="relative z-10">
          {/* Logo Section with Enhanced Animation */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3 group cursor-pointer">
              <div className="p-2.5 bg-gradient-to-br from-blue-500 via-blue-600 to-indigo-600 rounded-xl shadow-lg group-hover:shadow-xl transition-all duration-300 group-hover:scale-110">
                <Code2 className="w-5 h-5 text-white" />
              </div>
              <div className="transition-all duration-300">
                <h1 className="text-lg font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                  CodeChat
                </h1>
                <p className="text-xs text-gray-500 font-medium">AI Assistant</p>
              </div>
            </div>

            {/* Refresh Button with Enhanced Feedback */}
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              title="Refresh all data"
              className={cn(
                'p-2 rounded-lg transition-all duration-300 transform hover:scale-110',
                isRefreshing
                  ? 'bg-blue-100 text-blue-600 cursor-not-allowed'
                  : 'hover:bg-blue-50 text-gray-600 hover:text-blue-600 active:scale-95'
              )}
            >
              <RefreshCw className={cn('w-5 h-5', isRefreshing && 'animate-spin')} />
            </button>
          </div>

          {/* Status Indicator with Tooltip */}
          <div className="relative group">
            <div className={cn(
              'flex items-center gap-2 px-3.5 py-2.5 rounded-lg cursor-pointer transition-all duration-300 border backdrop-blur-sm',
              health?.status === 'healthy' ? 'bg-green-50 border-green-200 hover:bg-green-100 hover:border-green-300' :
              health?.status === 'degraded' ? 'bg-yellow-50 border-yellow-200 hover:bg-yellow-100 hover:border-yellow-300' :
              'bg-red-50 border-red-200 hover:bg-red-100 hover:border-red-300'
            )}>
              {getStatusIcon(health?.status)}
              <span className="text-xs font-semibold text-gray-700 flex-1">
                {health?.status === 'healthy' ? '✓ All Systems' :
                 health?.status === 'degraded' ? '⚠ Partial' :
                 '✕ Offline'}
              </span>
              <Settings className="w-3.5 h-3.5 text-gray-400 group-hover:text-gray-600 transition-colors" />
            </div>

            {/* Enhanced Tooltip */}
            <div className="absolute left-0 top-full mt-2 w-72 bg-white rounded-xl shadow-xl border border-border p-4 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-300 z-50 animate-scale-in">
              <h3 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                <Zap className="w-4 h-4 text-blue-600" />
                System Status
              </h3>
              <div className="space-y-2.5">
                {health && Object.entries(health.components).map(([name, component]) => (
                  <div key={name} className="flex items-start gap-2 p-2.5 rounded-lg hover:bg-gray-50 transition-all duration-200">
                    {getStatusIcon(component.status)}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-gray-900 capitalize">{name}</p>
                      <p className="text-xs text-gray-500 truncate">{component.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Repositories Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border hover:bg-gray-50 transition-colors duration-200">
        <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
          <Database className="w-4 h-4 text-blue-600" />
          Repositories
          {repositories.length > 0 && (
            <Badge variant="secondary" className="ml-1 text-xs">
              {repositories.length}
            </Badge>
          )}
        </h2>
        <button
          onClick={onShowAddRepo}
          className="p-1.5 hover:bg-blue-100 rounded-lg transition-all duration-200 text-gray-600 hover:text-blue-600 active:scale-95 transform hover:scale-110"
          title="Add Repository"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Repositories List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {/* Add Repository Modal */}
        {showAddRepo && (
          <Card className="mb-2 border-blue-200 bg-gradient-to-br from-blue-50 to-blue-100 animate-slide-in-down shadow-lg">
            <CardHeader className="border-b border-blue-200 pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base text-gray-900 flex items-center gap-2">
                  <Github className="w-4 h-4 text-blue-600" />
                  Add Repository
                </CardTitle>
                <button
                  onClick={() => onShowAddRepo(false)}
                  className="p-1.5 hover:bg-blue-200 rounded-lg transition-all duration-200 active:scale-95"
                >
                  <X className="w-4 h-4 text-gray-600" />
                </button>
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              <Input
                placeholder="owner/repo or full URL"
                className="mb-3"
              />
              <p className="text-xs text-gray-600 mb-4">
                💡 Supports: owner/repo, full URL, or .git URL
              </p>
              <div className="flex gap-2">
                <Button onClick={onAddRepo} size="sm" className="flex-1">
                  <Plus className="w-3 h-3 mr-1" />
                  Add
                </Button>
                <Button onClick={() => onShowAddRepo(false)} variant="outline" size="sm" className="flex-1">
                  Cancel
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Empty State */}
        {repositories.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center animate-fade-in">
            <div className="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 rounded-full flex items-center justify-center mb-4 shadow-md">
              <Database className="w-8 h-8 text-gray-400" />
            </div>
            <p className="text-gray-600 font-medium text-sm">No repositories</p>
            <button
              onClick={onShowAddRepo}
              className="mt-3 text-blue-600 hover:text-blue-700 text-xs font-semibold transition-colors"
            >
              Add your first repository
            </button>
          </div>
        ) : (
          /* Repository Items with Enhanced Interactions */
          repositories.map((repo) => {
            const isSelected = selectedRepo === repo.name
            const repoStatus = getRepoStatus(repo.name)
            const isProcessing = repoStatus !== null

            return (
              <div
                key={repo.name}
                onMouseEnter={() => setHoveredRepo(repo.name)}
                onMouseLeave={() => setHoveredRepo(null)}
                onClick={() => onRepoSelect(repo.name)}
                className={cn(
                  'group relative p-3 rounded-xl transition-all duration-300 cursor-pointer overflow-hidden',
                  'border border-transparent hover:border-blue-200',
                  isSelected
                    ? 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-300 shadow-md'
                    : 'bg-white hover:bg-gray-50 shadow-sm hover:shadow-md'
                )}
              >
                {/* Animated background gradient on hover */}
                <div className={cn(
                  'absolute inset-0 opacity-0 transition-opacity duration-300',
                  hoveredRepo === repo.name && 'opacity-5'
                )}
                  style={{
                    background: 'radial-gradient(circle at top right, rgba(59, 130, 246, 0.1), transparent)',
                  }}
                />

                <div className="relative z-10">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1 min-w-0">
                      <h3 className={cn(
                        'text-sm font-bold truncate transition-colors duration-200',
                        isSelected ? 'text-blue-700' : 'text-gray-900 group-hover:text-blue-600'
                      )}>
                        {repo.name}
                      </h3>
                      {repo.url && (
                        <p className="text-xs text-gray-500 truncate mt-0.5">
                          {repo.url.replace('https://github.com/', '')}
                        </p>
                      )}
                    </div>
                    {hoveredRepo === repo.name && (
                      <button className="p-1 hover:bg-gray-200 rounded transition-colors ml-2">
                        <MoreVertical className="w-4 h-4 text-gray-400" />
                      </button>
                    )}
                  </div>

                  {/* Status Badge */}
                  {repoStatus && (
                    <div className="mt-2">
                      {repoStatus}
                    </div>
                  )}

                  {/* Repository Stats */}
                  {repo.stats && (
                    <div className="flex gap-2 mt-2 text-xs text-gray-600">
                      <span>📁 {repo.stats.file_count}</span>
                      <span>⚙️ {repo.stats.function_count}</span>
                    </div>
                  )}
                </div>

                {/* Selection Indicator */}
                {isSelected && (
                  <div className="absolute right-0 top-0 w-1 h-full bg-gradient-to-b from-blue-500 to-indigo-500 rounded-r-xl" />
                )}
              </div>
            )
          })
        )}
      </div>

      {/* Stats Card Footer */}
      {stats && (
        <div className="px-3 pb-3">
          <Card className="bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200 animate-slide-in-up shadow-md">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs flex items-center gap-2 text-gray-900">
                <Zap className="w-3 h-3 text-blue-600" />
                Repository Stats
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600">Files</span>
                <Badge variant="default" className="text-xs">{stats.file_count}</Badge>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600">Classes</span>
                <Badge variant="default" className="text-xs">{stats.class_count}</Badge>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600">Functions</span>
                <Badge variant="default" className="text-xs">{stats.function_count}</Badge>
              </div>
              <div className="pt-1.5 mt-1.5 border-t border-blue-200 flex justify-between items-center">
                <span className="text-xs font-semibold text-gray-700">Total Nodes</span>
                <Badge variant="success" className="text-xs">{stats.total_nodes}</Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Footer */}
      <div className="px-5 py-3 border-t border-border bg-gradient-to-r from-gray-50 to-blue-50">
        <p className="text-xs text-gray-500 text-center font-medium">
          Powered by Neo4j & Gemini
        </p>
      </div>
    </div>
  )
}
