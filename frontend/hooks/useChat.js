import { useState, useCallback, useEffect } from 'react'
import { api, getErrorMessage } from '@/lib/api'

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
      console.log('📝 Loading chat history from session storage...')
      const stored = sessionStorage.getItem(CHAT_STORAGE_KEY)
      const loadedMessages = stored ? JSON.parse(stored) : []
      setMessages(loadedMessages)
      console.log(`✅ Loaded ${loadedMessages.length} messages from history`)
    } catch (error) {
      console.error('❌ Error loading chat history:', error)
      // Don't fail if we can't load history
      setMessages([])
    }
    setIsHydrated(true)
  }, [])

  // Save messages to sessionStorage whenever they change
  useEffect(() => {
    if (typeof window !== 'undefined' && isHydrated) {
      try {
        sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages))
        console.log(`💾 Saved ${messages.length} messages to session storage`)
      } catch (error) {
        console.error('❌ Error saving chat history:', error)
        // Don't fail if we can't save history
      }
    }
  }, [messages, isHydrated])

  const sendMessage = useCallback(async (query, repository, topK = 5) => {
    // Validation
    if (!query || !query.trim()) {
      const errorMsg = 'Query cannot be empty'
      console.error('❌', errorMsg)
      throw new Error(errorMsg)
    }

    if (topK < 1 || topK > 20) {
      console.warn(`⚠️ Invalid topK value: ${topK}, using default 5`)
      topK = 5
    }

    console.log(`💬 Sending message: "${query.substring(0, 50)}..." (repository: ${repository || 'all'}, topK: ${topK})`)

    // Add user message
    const userMessage = {
      type: 'user',
      content: query,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    setLoading(true)

    try {
      const response = await api.post('/api/query', {
        query,
        top_k: topK,
        repository
      })

      if (!response.data || !response.data.answer) {
        throw new Error('Invalid response format from server')
      }

      console.log(`✅ Received response (${response.data.answer.length} chars, ${response.data.sources?.length || 0} sources)`)

      // Add AI response
      const aiMessage = {
        type: 'ai',
        content: response.data.answer,
        sources: response.data.sources || [],
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, aiMessage])

      return response.data
    } catch (error) {
      const errorMessage = getErrorMessage(error) || 'Failed to get response. Please try again.'
      console.error('❌ Error sending message:', errorMessage, error)

      // Add error message to chat
      const errorMsg = {
        type: 'error',
        content: errorMessage,
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, errorMsg])

      throw error
    } finally {
      setLoading(false)
    }
  }, [])

  const clearChat = useCallback(() => {
    if (confirm('Are you sure you want to clear the chat history? This cannot be undone.')) {
      console.log('🗑️ Clearing chat history...')
      setMessages([])

      if (typeof window !== 'undefined') {
        try {
          sessionStorage.removeItem(CHAT_STORAGE_KEY)
          console.log('✅ Chat history cleared from session storage')
        } catch (error) {
          console.error('❌ Error clearing chat history:', error)
        }
      }
    } else {
      console.log('❌ Chat clear cancelled by user')
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
