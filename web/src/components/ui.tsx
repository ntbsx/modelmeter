import { type ReactNode, type ReactElement } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

type CardProps = {
  children: ReactNode
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hover?: boolean
}

const paddingClasses = {
  none: '',
  sm: 'p-3 sm:p-4',
  md: 'p-4 sm:p-5',
  lg: 'p-5 sm:p-6',
}

export function Card({ children, className = '', padding = 'md', hover = false }: CardProps) {
  return (
    <div
      className={`ds-surface ${paddingClasses[padding]} ${hover ? 'ds-surface-hover cursor-pointer' : ''} ${className}`}
    >
      {children}
    </div>
  )
}

type StatCardProps = {
  label: string
  value: string
  subtitle?: string
  trend?: {
    value: number
    direction: 'up' | 'down' | 'neutral'
  }
  className?: string
  delay?: number
  accent?: 'default' | 'blue' | 'green' | 'amber' | 'purple'
  icon?: ReactElement
}

const accentStyles = {
  default: '',
  blue: 'border-l-4 border-l-[var(--accent-primary)] bg-[var(--surface-accent)]/30',
  green: 'border-l-4 border-l-[var(--color-success)] bg-[var(--surface-success)]/30',
  amber: 'border-l-4 border-l-[var(--color-warning)] bg-[var(--surface-warning)]/30',
  purple: 'border-l-4 border-l-purple-500 bg-purple-50 dark:bg-purple-950/30',
}

const iconColors = {
  default: 'text-[var(--text-tertiary)]',
  blue: 'text-[var(--accent-primary)]',
  green: 'text-[var(--color-success)]',
  amber: 'text-[var(--color-warning)]',
  purple: 'text-purple-500',
}

export function StatCard({ label, value, subtitle, trend, className = '', delay = 0, accent = 'default', icon }: StatCardProps) {
  return (
    <div 
      className={`ds-surface p-5 sm:p-6 animate-slide-up ${accentStyles[accent]} ${className}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="ds-text-label">{label}</div>
          <div className="ds-text-metric mt-1">{value}</div>
          {subtitle && <div className="ds-text-muted mt-1.5">{subtitle}</div>}
          {trend && (
            <div className={`mt-2 flex items-center gap-1.5 text-xs font-medium ${
              trend.direction === 'up' ? 'text-[var(--color-success)]' :
              trend.direction === 'down' ? 'text-[var(--color-error)]' :
              'text-[var(--text-tertiary)]'
            }`}>
              {trend.direction === 'up' ? (
                <TrendingUp className="w-3.5 h-3.5" />
              ) : trend.direction === 'down' ? (
                <TrendingDown className="w-3.5 h-3.5" />
              ) : (
                <Minus className="w-3.5 h-3.5" />
              )}
              <span>{Math.abs(trend.value)}%</span>
            </div>
          )}
        </div>
        {icon && (
          <div className={`shrink-0 ${iconColors[accent]}`}>
            {icon}
          </div>
        )}
      </div>
    </div>
  )
}

type BadgeVariant = 'default' | 'primary' | 'success' | 'warning' | 'error'

type BadgeProps = {
  children: ReactNode
  variant?: BadgeVariant
  className?: string
  dot?: boolean
  title?: string
}

const badgeVariantClasses: Record<BadgeVariant, string> = {
  default: 'ds-badge-default',
  primary: 'ds-badge-primary',
  success: 'ds-badge-success',
  warning: 'ds-badge-warning',
  error: 'ds-badge-error',
}

export function Badge({ children, variant = 'default', className = '', dot = false, title }: BadgeProps) {
  return (
    <span className={`ds-badge ${badgeVariantClasses[variant]} ${className}`} title={title}>
      {dot && (
        <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
          variant === 'success' ? 'bg-[var(--color-success)]' :
          variant === 'warning' ? 'bg-[var(--color-warning)]' :
          variant === 'error' ? 'bg-[var(--color-error)]' :
          variant === 'primary' ? 'bg-[var(--accent-primary)]' :
          'bg-current'
        }`} />
      )}
      {children}
    </span>
  )
}

type ButtonVariant = 'primary' | 'secondary' | 'ghost'
type ButtonSize = 'sm' | 'md' | 'lg'

type ButtonProps = {
  children: ReactNode
  variant?: ButtonVariant
  size?: ButtonSize
  className?: string
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
  onClick?: () => void
}

const buttonVariantClasses: Record<ButtonVariant, string> = {
  primary: 'ds-btn-primary',
  secondary: 'ds-btn-secondary',
  ghost: 'ds-btn-ghost',
}

const buttonSizeClasses: Record<ButtonSize, string> = {
  sm: 'px-2.5 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  className = '',
  disabled = false,
  type = 'button',
  onClick,
}: ButtonProps) {
  const baseClasses = `${buttonVariantClasses[variant]} ${buttonSizeClasses[size]}`
  const disabledClasses = disabled ? 'opacity-50 cursor-not-allowed' : ''

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseClasses} ${disabledClasses} ${className}`}
    >
      {children}
    </button>
  )
}

type InputProps = {
  type?: 'text' | 'password' | 'email' | 'search' | 'number'
  placeholder?: string
  value?: string
  onChange?: (value: string) => void
  className?: string
  disabled?: boolean
  label?: string
  error?: string
}

export function Input({
  type = 'text',
  placeholder,
  value,
  onChange,
  className = '',
  disabled = false,
  label,
  error,
}: InputProps) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
          {label}
        </label>
      )}
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        disabled={disabled}
        className={`ds-input ${error ? 'border-[var(--color-error)] focus:border-[var(--color-error)] focus:shadow-none' : ''}`}
      />
      {error && (
        <p className="mt-1 text-xs text-[var(--color-error)]">{error}</p>
      )}
    </div>
  )
}

type SelectOption = {
  value: string
  label: string
}

type SelectProps = {
  options: SelectOption[]
  value?: string
  onChange?: (value: string) => void
  className?: string
  label?: string
}

export function Select({ options, value, onChange, className = '', label }: SelectProps) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
          {label}
        </label>
      )}
      <select
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        className="ds-input cursor-pointer"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

type DividerProps = {
  className?: string
  label?: string
}

export function Divider({ className = '', label }: DividerProps) {
  if (label) {
    return (
      <div className={`flex items-center gap-3 ${className}`}>
        <div className="flex-1 h-px bg-[var(--border-default)]" />
        <span className="ds-text-muted">{label}</span>
        <div className="flex-1 h-px bg-[var(--border-default)]" />
      </div>
    )
  }
  return <hr className={`border-[var(--border-default)] ${className}`} />
}
