import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Axios instance with default configuration
 */
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Request interceptor for logging and validation
 */
api.interceptors.request.use(
  (config) => {
    // Validate URL
    if (!config.url) {
      console.error('❌ API Request Error: No URL provided')
      return Promise.reject(new Error('No URL provided for API request'))
    }

    if (process.env.NODE_ENV === 'development') {
      console.log(`🔵 API Request: ${config.method?.toUpperCase()} ${config.url}`, {
        params: config.params,
        data: config.data
      })
    }
    return config
  },
  (error) => {
    console.error('❌ API Request Setup Error:', error)
    return Promise.reject(error)
  }
)

/**
 * Response interceptor for comprehensive error handling
 */
api.interceptors.response.use(
  (response) => {
    if (process.env.NODE_ENV === 'development') {
      console.log(`✅ API Response: ${response.status} ${response.config.url}`)
    }
    return response
  },
  (error) => {
    // Enhanced error handling with categorization
    const errorDetails = {
      timestamp: new Date().toISOString(),
      url: error.config?.url,
      method: error.config?.method?.toUpperCase(),
    }

    if (error.response) {
      // Server responded with error status (4xx, 5xx)
      errorDetails.status = error.response.status
      errorDetails.statusText = error.response.statusText
      errorDetails.data = error.response.data

      console.error('❌ API Error Response:', errorDetails)

      // Categorize errors for better user experience
      const status = error.response.status
      let userMessage = error.response.data?.detail || error.response.data?.message || 'An error occurred'

      if (status === 400) {
        userMessage = `Bad Request: ${userMessage}`
      } else if (status === 401) {
        userMessage = 'Authentication required. Please check your credentials.'
      } else if (status === 403) {
        userMessage = 'Access forbidden. You don\'t have permission to perform this action.'
      } else if (status === 404) {
        userMessage = 'Resource not found. Please check the URL or try again.'
      } else if (status === 422) {
        userMessage = `Validation Error: ${userMessage}`
      } else if (status === 429) {
        userMessage = 'Too many requests. Please slow down and try again later.'
      } else if (status >= 500) {
        userMessage = `Server Error: ${userMessage}. Please try again later.`
      }

      // Attach user-friendly message
      error.userMessage = userMessage

    } else if (error.request) {
      // Request made but no response received (network error, timeout)
      errorDetails.message = 'No response from server'
      errorDetails.code = error.code

      console.error('❌ API No Response:', errorDetails)

      let userMessage = 'Unable to connect to server.'

      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        userMessage = 'Request timeout. The server took too long to respond. Please try again.'
      } else if (error.code === 'ERR_NETWORK') {
        userMessage = 'Network error. Please check your internet connection and try again.'
      } else if (error.code === 'ECONNREFUSED') {
        userMessage = 'Connection refused. The server might be down. Please try again later.'
      }

      error.userMessage = userMessage

    } else {
      // Error in request setup
      errorDetails.message = error.message

      console.error('❌ API Request Setup Error:', errorDetails)
      error.userMessage = `Configuration error: ${error.message}`
    }

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.group('🔴 API Error Details')
      console.table(errorDetails)
      console.log('Full Error:', error)
      console.groupEnd()
    }

    return Promise.reject(error)
  }
)

/**
 * Helper function to extract user-friendly error message
 * @param {Error} error - The error object
 * @returns {string} - User-friendly error message
 */
export function getErrorMessage(error) {
  if (error.userMessage) {
    return error.userMessage
  }
  if (error.response?.data?.detail) {
    return error.response.data.detail
  }
  if (error.response?.data?.message) {
    return error.response.data.message
  }
  if (error.message) {
    return error.message
  }
  return 'An unexpected error occurred. Please try again.'
}

export default api
