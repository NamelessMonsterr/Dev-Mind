'use client'

import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { CodeBlock } from '@/components/CodeBlock'
import { FileCode, ExternalLink, MessageSquare } from 'lucide-react'
import type { SearchResult } from '@/lib/api'

interface SearchResultCardProps {
  result: SearchResult
}

export function SearchResultCard({ result }: SearchResultCardProps) {
  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-start gap-2 flex-1 min-w-0">
            <FileCode className="w-5 h-5 mt-0.5 flex-shrink-0 text-primary" />
            <div className="flex-1 min-w-0">
              <p className="font-mono text-sm truncate">{result.file_path}</p>
              <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                <span>Lines {result.start_line}-{result.end_line}</span>
                <span>•</span>
                <span className="capitalize">{result.section_type}</span>
                <span>•</span>
                <span>Score: {result.score.toFixed(2)}</span>
              </div>
            </div>
          </div>
          <div className="text-lg font-bold text-primary">
            {(result.score * 100).toFixed(0)}%
          </div>
        </div>

        {/* Code Preview */}
        <CodeBlock
          code={result.content}
          language={result.language}
          startLine={result.start_line}
        />

        {/* Actions */}
        <div className="flex gap-2">
          <Button size="sm" variant="outline">
            <ExternalLink className="w-3 h-3 mr-1" />
            View File
          </Button>
          <Button size="sm" variant="outline">
            <MessageSquare className="w-3 h-3 mr-1" />
            Explain
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
