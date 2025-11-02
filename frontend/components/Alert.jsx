import { forwardRef } from 'react'
import { cn } from '@/lib/utils'
import { AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react'

const Alert = forwardRef(({ className, variant = 'default', ...props }, ref) => {
  const variants = {
    default: 'bg-blue-50 border border-blue-200 text-blue-900 dark:bg-black dark:border-red-900 dark:text-red-300',
    destructive: 'bg-red-50 border border-red-200 text-red-900 dark:bg-red-950 dark:border-red-900 dark:text-red-300',
    success: 'bg-green-50 border border-green-200 text-green-900 dark:bg-black dark:border-green-900 dark:text-green-300',
    warning: 'bg-yellow-50 border border-yellow-200 text-yellow-900 dark:bg-black dark:border-yellow-900 dark:text-yellow-300',
  }

  return (
    <div
      ref={ref}
      role="alert"
      className={cn('rounded-lg p-4 flex gap-3', variants[variant], className)}
      {...props}
    />
  )
})

Alert.displayName = 'Alert'

const AlertIcon = ({ variant = 'default' }) => {
  const icons = {
    default: <Info className="h-4 w-4" />,
    destructive: <AlertCircle className="h-4 w-4" />,
    success: <CheckCircle className="h-4 w-4" />,
    warning: <AlertTriangle className="h-4 w-4" />,
  }
  return icons[variant]
}

const AlertTitle = forwardRef(({ className, ...props }, ref) => (
  <h5
    ref={ref}
    className={cn('mb-1 font-medium leading-tight', className)}
    {...props}
  />
))
AlertTitle.displayName = 'AlertTitle'

const AlertDescription = forwardRef(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('text-sm [&_p]:leading-relaxed', className)}
    {...props}
  />
))
AlertDescription.displayName = 'AlertDescription'

export { Alert, AlertIcon, AlertTitle, AlertDescription }
