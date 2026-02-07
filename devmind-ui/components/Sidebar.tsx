'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import { MessageSquare, Search, Upload, BarChart3, Settings, Home, LogOut, User } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'

const navItems = [
  { name: 'Home', href: '/', icon: Home },
  { name: 'Chat', href: '/chat', icon: MessageSquare },
  { name: 'Search', href: '/search', icon: Search },
  { name: 'Ingest', href: '/ingest', icon: Upload },
  { name: 'Stats', href: '/stats', icon: BarChart3 },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const router = useRouter()

  // Don't show sidebar on auth pages
  if (pathname === '/login' || pathname === '/register') {
    return null
  }

  const handleLogout = async () => {
    await logout()
  }

  return (
    <div className="w-64 border-r border-border bg-card p-4 flex flex-col">
      <div className="mb-8">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
          DevMind
        </h2>
        <p className="text-xs text-muted-foreground mt-1">
          Code Intelligence
        </p>
      </div>

      <nav className="space-y-2 flex-1">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-md transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-accent hover:text-accent-foreground'
              )}
            >
              <Icon className="w-5 h-5" />
              <span>{item.name}</span>
            </Link>
          )
        })}
      </nav>

      {user && (
        <div className="mt-auto pt-4 border-t border-border space-y-2">
          <div className="flex items-center gap-2 px-3 py-2 bg-accent/50 rounded-md">
            <User className="w-4 h-4 text-muted-foreground" />
            <div className="flex-1 overflow-hidden">
              <p className="text-sm font-medium truncate">{user.username}</p>
              <p className="text-xs text-muted-foreground truncate">{user.role}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-md text-red-500 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span>Logout</span>
          </button>
        </div>
      )}

      <div className="text-xs text-muted-foreground mt-4 space-y-1">
        <p>v0.1.0</p>
        <p>Enterprise Edition</p>
      </div>
    </div>
  )
}
