import { useState, useCallback } from 'react'
import { api, getErrorMessage } from '@/lib/api'

/**
 * Custom hook for managing repositories
 */
export function useRepositories() {
  const [repositories, setRepositories] = useState([])
  const [selectedRepo, setSelectedRepo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchRepositories = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      console.log('📋 Fetching repositories...')
      const response = await api.get('/api/repositories')

      if (!response.data || !Array.isArray(response.data.repositories)) {
        throw new Error('Invalid response format from server')
      }

      setRepositories(response.data.repositories)
      console.log(`✅ Fetched ${response.data.repositories.length} repositories`)

      // Auto-select first repo if none selected
      if (response.data.repositories.length > 0 && !selectedRepo) {
        setSelectedRepo(response.data.repositories[0].name)
        console.log(`📌 Auto-selected repository: ${response.data.repositories[0].name}`)
      }

      return response.data.repositories
    } catch (err) {
      const errorMessage = getErrorMessage(err) || 'Failed to fetch repositories'
      console.error('❌ Error fetching repositories:', errorMessage, err)
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [selectedRepo])

  const addRepository = useCallback(async (repoUrl, branch = 'main') => {
    if (!repoUrl || !repoUrl.trim()) {
      const errorMessage = 'Repository URL is required'
      console.error('❌', errorMessage)
      setError(errorMessage)
      throw new Error(errorMessage)
    }

    setLoading(true)
    setError(null)

    try {
      console.log(`➕ Adding repository: ${repoUrl} (branch: ${branch})`)
      const response = await api.post('/api/repositories', {
        repo_url: repoUrl,
        branch
      })

      console.log(`✅ Repository added successfully: ${repoUrl}`)
      await fetchRepositories()
      return response.data
    } catch (err) {
      const errorMessage = getErrorMessage(err) || 'Failed to add repository'
      console.error('❌ Error adding repository:', errorMessage, err)
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [fetchRepositories])

  const deleteRepository = useCallback(async (repoName) => {
    if (!repoName) {
      const errorMessage = 'Repository name is required'
      console.error('❌', errorMessage)
      setError(errorMessage)
      throw new Error(errorMessage)
    }

    setLoading(true)
    setError(null)

    try {
      console.log(`🗑️ Deleting repository: ${repoName}`)
      await api.delete(`/api/repositories/${encodeURIComponent(repoName)}`)
      console.log(`✅ Repository deleted successfully: ${repoName}`)

      await fetchRepositories()

      // Clear selection if deleted repo was selected
      if (selectedRepo === repoName) {
        setSelectedRepo(null)
        console.log('📌 Cleared selected repository')
      }
    } catch (err) {
      const errorMessage = getErrorMessage(err) || 'Failed to delete repository'
      console.error('❌ Error deleting repository:', errorMessage, err)
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [fetchRepositories, selectedRepo])

  const selectRepository = useCallback((repoName) => {
    console.log(`📌 Selecting repository: ${repoName}`)
    setSelectedRepo(repoName)
  }, [])

  return {
    repositories,
    selectedRepo,
    loading,
    error,
    fetchRepositories,
    addRepository,
    deleteRepository,
    selectRepository
  }
}
