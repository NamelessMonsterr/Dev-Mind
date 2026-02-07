import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Sidebar } from '@/components/Sidebar'
import { AuthProvider } from '@/context/AuthContext'
import { WorkspaceProvider } from '@/context/WorkspaceContext'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'DevMind - Intelligent Code Assistant',
  description: 'Semantic code search and AI-powered chat for your codebase',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <AuthProvider>
          <WorkspaceProvider>
            <div className="flex h-screen bg-background">
              <Sidebar />
              <main className="flex-1 overflow-hidden">
                {children}
              </main>
            </div>
          </WorkspaceProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
