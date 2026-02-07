'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { api, type JobStatus } from '@/lib/api'
import { Upload, Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react'

export default function IngestPage() {
  const [sourcePath, setSourcePath] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [jobs, setJobs] = useState<JobStatus[]>([])

  useEffect(() => {
    loadJobs()
  }, [])

  const loadJobs = async () => {
    try {
      const response = await api.listJobs(undefined, 20)
      setJobs(response.jobs)
    } catch (error) {
      console.error('Failed to load jobs:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!sourcePath.trim()) return

    setIsSubmitting(true)
    try {
      await api.startIngestion({
        source_path: sourcePath,
        languages: ['python', 'javascript', 'typescript'],
        file_types: ['CODE']
      })
      setSourcePath('')
      await loadJobs()
    } catch (error) {
      console.error('Ingestion error:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />
      case 'FAILED':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'RUNNING':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
      default:
        return <Clock className="w-5 h-5 text-yellow-500" />
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border p-4">
        <h1 className="text-2xl font-bold">Ingestion</h1>
        <p className="text-sm text-muted-foreground">
          Index new codebases and manage jobs
        </p>
      </div>

      {/* Start Ingestion */}
      <div className="p-4 border-b border-border">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Start New Ingestion</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="flex gap-2">
              <Input
                value={sourcePath}
                onChange={(e) => setSourcePath(e.target.value)}
                placeholder="/path/to/codebase"
                className="flex-1"
                disabled={isSubmitting}
              />
              <Button type="submit" disabled={isSubmitting || !sourcePath.trim()}>
                {isSubmitting ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : (
                  <Upload className="w-4 h-4 mr-2" />
                )}
                Start
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      {/* Jobs List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <h2 className="text-lg font-semibold">Recent Jobs</h2>
        
        {jobs.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <p className="text-muted-foreground">No ingestion jobs yet</p>
          </div>
        ) : (
          jobs.map((job) => (
            <Card key={job.job_id}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    {getStatusIcon(job.status)}
                    <div className="flex-1">
                      <p className="font-mono text-sm">{job.job_id}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {new Date(job.created_at).toLocaleString()}
                      </p>
                      {job.progress && (
                        <div className="mt-2 space-y-1 text-xs">
                          <p>Files: {job.progress.files_processed}/{job.progress.files_scanned}</p>
                          <p>Sections: {job.progress.sections_extracted}</p>
                          <p>Chunks: {job.progress.chunks_generated}</p>
                        </div>
                      )}
                      {job.errors && job.errors.length > 0 && (
                        <p className="text-xs text-red-500 mt-2">
                          {job.errors[0]}
                        </p>
                      )}
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    job.status === 'COMPLETED' ? 'bg-green-500/20 text-green-500' :
                    job.status === 'FAILED' ? 'bg-red-500/20 text-red-500' :
                    job.status === 'RUNNING' ? 'bg-blue-500/20 text-blue-500' :
                    'bg-yellow-500/20 text-yellow-500'
                  }`}>
                    {job.status}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}
