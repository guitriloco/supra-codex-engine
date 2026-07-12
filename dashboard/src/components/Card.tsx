import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  hover?: boolean
}

export function Card({ children, className = '', hover = false }: CardProps) {
  return (
    <div
      className={`rounded-xl border border-surface-800 bg-surface-900 p-5 
        ${hover ? 'hover:border-surface-700 transition-colors duration-200' : ''} 
        ${className}`}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`flex items-center justify-between mb-4 ${className}`}>{children}</div>
}

export function CardTitle({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <h3 className={`text-sm font-semibold text-surface-200 ${className}`}>{children}</h3>
}

export function CardValue({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <p className={`text-2xl font-bold text-white ${className}`}>{children}</p>
}

export function CardLabel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <p className={`text-xs text-surface-500 mt-1 ${className}`}>{children}</p>
}