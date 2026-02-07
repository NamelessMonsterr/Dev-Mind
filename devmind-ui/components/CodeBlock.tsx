'use client'

import { useEffect, useState } from 'react'
import { highlightCode, getLanguageLabel } from '@/lib/highlight'

interface CodeBlockProps {
  code: string
  language: string
  startLine?: number
  highlighted?: boolean
}

export function CodeBlock({ code, language, startLine = 1, highlighted }: CodeBlockProps) {
  const [html, setHtml] = useState('')

  useEffect(() => {
    const highlighted = highlightCode(code, language)
    setHtml(highlighted)
  }, [code, language])

  const lines = code.split('\n')

  return (
    <div className="rounded-md bg-muted/50 border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-muted border-b border-border">
        <span className="text-xs text-muted-foreground font-mono">
          {getLanguageLabel(language)}
        </span>
      </div>

      {/* Code */}
      <div className="overflow-x-auto">
        <pre className="p-4 text-sm">
          <code
            className={`language-${language}`}
            dangerouslySetInnerHTML={{ __html: html }}
          />
        </pre>
      </div>

      {/* Line Numbers (optional) */}
      {startLine && (
        <div className="px-3 py-1 bg-muted/30 border-t border-border">
          <span className="text-xs text-muted-foreground">
            Lines {startLine}-{startLine + lines.length - 1}
          </span>
        </div>
      )}
    </div>
  )
}
