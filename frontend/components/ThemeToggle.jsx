'use client'

import { useState, useEffect } from 'react'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from './ThemeProvider'
import { cn } from '@/lib/utils'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Don't render until hydrated to prevent hydration mismatch
  if (!mounted) {
    return null
  }

  return (
    <button
      onClick={toggleTheme}
      className={cn(
        'relative inline-flex items-center justify-center p-2.5 rounded-lg transition-all duration-300',
        'hover:shadow-md active:scale-95',
        theme === 'light'
          ? 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          : 'bg-red-950 text-red-200 hover:bg-red-900'
      )}
      title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
    >
      {theme === 'light' ? (
        <Moon className="w-5 h-5 transition-transform duration-300 rotate-0" />
      ) : (
        <Sun className="w-5 h-5 transition-transform duration-300 rotate-0" />
      )}
    </button>
  )
}
