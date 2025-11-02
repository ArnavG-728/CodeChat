import { useState, useCallback, useEffect } from 'react'
import { api } from '@/lib/api'

const CHAT_STORAGE_KEY = 'codechat_messages'

/**
 * Custom hook for managing chat messages
 */
export function useChat() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [isHydrated, setIsHydrated] = useState(false)

  // Load messages from sessionStorage on mount
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(CHAT_STORAGE_KEY)
      setMessages(stored ? JSON.parse(stored) : [])
    } catch (error) {
      console.error('Error loading chat history:', error)
    }
    setIsHydrated(true)
  }, [])

  // Save messages to sessionStorage whenever they change
  useEffect(() => {
    if (typeof window !== 'undefined' && isHydrated) {
      try {
        sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages))
      } catch (error) {
        console.error('Error saving chat history:', error)
      }
    }
  }, [messages, isHydrated])

  const sendMessage = useCallback(async (query, repository, topK = 5) => {
    if (!query.trim()) {
      throw new Error('Query cannot be empty')
    }

    // Add user message
    const userMessage = { type: 'user', content: query }
    setMessages(prev => [...prev, userMessage])
    setLoading(true)

    try {
      const response = await api.post('/api/query', {
        query,
        top_k: topK,
        repository
      })

      // Add AI response
      const aiMessage = {
        type: 'ai',
        content: response.data.answer,
        sources: response.data.sources || []
      }
      setMessages(prev => [...prev, aiMessage])

      return response.data
    } catch (error) {
      console.error('Error sending message:', error)
      
      // Add error message
      const errorMessage = {
        type: 'error',
        content: error.response?.data?.detail || 'Failed to get response. Please try again.'
      }
      setMessages(prev => [...prev, errorMessage])
      
      throw error
    } finally {
      setLoading(false)
    }
  }, [])

  const clearChat = useCallback(() => {
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
  }, [])

  return {
    messages,
    loading,
    isHydrated,
    sendMessage,
    clearChat
  }
}
