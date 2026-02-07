'use client'

import { useState, useEffect } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { api, type SystemStats } from '@/lib/api'
import { Database, Search, Upload, Cpu, Loader2 } from 'lucide-react'

export default function StatsPage() {
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      const data = await api.getStats()
      setStats(data)
    } catch (error) {
      console.error('Failed to load stats:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted-foreground">Failed to load stats</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border p-4">
        <h1 className="text-2xl font-bold">System Statistics</h1>
        <p className="text-sm text-muted-foreground">
          Performance metrics and system overview
        </p>
      </div>

      {/* Stats Grid */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Index Stats */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5 text-primary" />
                <CardTitle className="text-lg">Index Statistics</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Object.entries(stats.index_stats).map(([index, data]) => (
                  <div key={index} className="flex justify-between items-center">
                    <span className="text-sm capitalize">{index}</span>
                    <span className="text-lg font-bold">{data.count.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Search Stats */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Search className="w-5 h-5 text-primary" />
                <CardTitle className="text-lg">Search Statistics</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div>
                  <p className="text-sm text-muted-foreground">Total Searches</p>
                  <p className="text-2xl font-bold">{stats.search_stats.total_searches.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Avg Latency</p>
                  <p className="text-2xl font-bold">{stats.search_stats.avg_latency_ms.toFixed(2)}ms</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Ingestion Stats */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Upload className="w-5 h-5 text-primary" />
                <CardTitle className="text-lg">Ingestion Statistics</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div>
                <p className="text-sm text-muted-foreground">Total Jobs</p>
                <p className="text-2xl font-bold">{stats.ingestion_stats.total_jobs.toLocaleString()}</p>
              </div>
            </CardContent>
          </Card>

          {/* Embedding Model */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Cpu className="w-5 h-5 text-primary" />
                <CardTitle className="text-lg">Embedding Model</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm font-mono">{stats.embedding_model}</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
