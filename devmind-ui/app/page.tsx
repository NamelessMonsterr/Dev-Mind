import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { MessageSquare, Search, Upload, BarChart3, Settings } from 'lucide-react'

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center h-full p-8 space-y-8 bg-gradient-to-br from-teal-50 via-mint-50 to-peach-50/30">
      <div className="text-center space-y-4">
        <h1 className="text-6xl font-bold bg-gradient-to-r from-coral via-teal to-mint bg-clip-text text-transparent drop-shadow-sm">
          DevMind
        </h1>
        <p className="text-xl text-navy-600 font-medium">
          Intelligent Code Assistant with Semantic Search & AI Chat
        </p>
        <div className="flex gap-2 items-center justify-center text-sm text-muted-foreground">
          <div className="w-2 h-2 rounded-full bg-mint animate-pulse"></div>
          <span>Powered by semantic embeddings & LLM orchestration</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl w-full">
        <Link href="/chat">
          <Card className="hover:border-coral hover:shadow-lg hover:shadow-coral/20 transition-all duration-300 cursor-pointer bg-white/80 backdrop-blur-sm">
            <CardHeader>
              <MessageSquare className="w-10 h-10 mb-2 text-coral" />
              <CardTitle className="text-navy">Chat</CardTitle>
              <CardDescription>
                Ask questions about your codebase with AI-powered answers
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link href="/search">
          <Card className="hover:border-teal hover:shadow-lg hover:shadow-teal/20 transition-all duration-300 cursor-pointer bg-white/80 backdrop-blur-sm">
            <CardHeader>
              <Search className="w-10 h-10 mb-2 text-teal" />
              <CardTitle className="text-navy">Search</CardTitle>
              <CardDescription>
                Semantic code search across your entire codebase
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link href="/ingest">
          <Card className="hover:border-mint hover:shadow-lg hover:shadow-mint/20 transition-all duration-300 cursor-pointer bg-white/80 backdrop-blur-sm">
            <CardHeader>
              <Upload className="w-10 h-10 mb-2 text-mint-600" />
              <CardTitle className="text-navy">Ingestion</CardTitle>
              <CardDescription>
                Index new codebases and manage ingestion jobs
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link href="/stats">
          <Card className="hover:border-peach hover:shadow-lg hover:shadow-peach/20 transition-all duration-300 cursor-pointer bg-white/80 backdrop-blur-sm">
            <CardHeader>
              <BarChart3 className="w-10 h-10 mb-2 text-peach" />
              <CardTitle className="text-navy">Stats</CardTitle>
              <CardDescription>
                View system statistics and performance metrics
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>

        <Link href="/settings">
          <Card className="hover:border-navy hover:shadow-lg hover:shadow-navy/20 transition-all duration-300 cursor-pointer bg-white/80 backdrop-blur-sm">
            <CardHeader>
              <Settings className="w-10 h-10 mb-2 text-navy" />
              <CardTitle className="text-navy">Settings</CardTitle>
              <CardDescription>
                Configure models, theme, and system preferences
              </CardDescription>
            </CardHeader>
          </Card>
        </Link>
      </div>

      <div className="text-center text-sm text-muted-foreground">
        <p>Powered by semantic embeddings, vector search, and LLM orchestration</p>
      </div>
    </div>
  )
}
