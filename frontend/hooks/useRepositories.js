import { useState, useCallback } from 'react'
import { api } from '@/lib/api'

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
      const response = await api.get('/api/repositories')
      setRepositories(response.data.repositories)
      
      // Auto-select first repo if none selected
      if (response.data.repositories.length > 0 && !selectedRepo) {
        setSelectedRepo(response.data.repositories[0].name)
      }
      
      return response.data.repositories
    } catch (err) {
      console.error('Error fetching repositories:', err)
      setError('Failed to fetch repositories')
      throw err
    } finally {
      setLoading(false)
    }
  }, [selectedRepo])

  const addRepository = useCallback(async (repoUrl, branch = 'main') => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.post('/api/repositories', {
        repo_url: repoUrl,
        branch
      })
      await fetchRepositories()
      return response.data
    } catch (err) {
      console.error('Error adding repository:', err)
      const errorMessage = err.response?.data?.detail || 'Failed to add repository'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [fetchRepositories])

  const deleteRepository = useCallback(async (repoName) => {
    setLoading(true)
    setError(null)
    try {
      await api.delete(`/api/repositories/${repoName}`)
      await fetchRepositories()
      
      // Clear selection if deleted repo was selected
      if (selectedRepo === repoName) {
        setSelectedRepo(null)
      }
    } catch (err) {
      console.error('Error deleting repository:', err)
      const errorMessage = err.response?.data?.detail || 'Failed to delete repository'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [fetchRepositories, selectedRepo])

  const selectRepository = useCallback((repoName) => {
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
