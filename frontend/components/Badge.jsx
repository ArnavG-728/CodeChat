import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

const Badge = forwardRef(({ className, variant = 'default', ...props }, ref) => {
  const variants = {
    default: 'bg-blue-100 text-blue-800 border border-blue-200 dark:bg-red-950 dark:text-red-300 dark:border-red-900',
    secondary: 'bg-gray-100 text-gray-800 border border-gray-200 dark:bg-neutral-900 dark:text-neutral-200 dark:border-red-900',
    destructive: 'bg-red-100 text-red-800 border border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-900',
    success: 'bg-green-100 text-green-800 border border-green-200 dark:bg-black dark:text-green-300 dark:border-green-900',
    warning: 'bg-yellow-100 text-yellow-800 border border-yellow-200 dark:bg-black dark:text-yellow-300 dark:border-yellow-900',
    outline: 'border border-gray-300 text-gray-700 dark:border-red-900 dark:text-gray-300',
  }

  return (
    <div
      ref={ref}
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors',
        variants[variant],
        className
      )}
      {...props}
    />
  )
})

Badge.displayName = 'Badge'

export default Badge
