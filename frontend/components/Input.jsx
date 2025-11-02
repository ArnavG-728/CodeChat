import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

const Input = forwardRef(({ className, type = 'text', ...props }, ref) => (
  <input
    type={type}
    className={cn(
      'flex h-10 w-full rounded-lg border border-gray-300 dark:border-red-900 bg-white dark:bg-black px-3 py-2 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-red-600 focus:ring-offset-0 focus:border-transparent disabled:cursor-not-allowed disabled:opacity-50 transition-colors duration-200 text-gray-900 dark:text-gray-100',
      className
    )}
    ref={ref}
    {...props}
  />
))

Input.displayName = 'Input'

export default Input
