'use client'

import { useState } from 'client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Send, Square } from 'lucide-react'

interface ChatInputProps {
  onSend: (query: string, provider?: string) => void
  onStop: () => void
  isStreaming: boolean
}

export function ChatInput({ onSend, onStop, isStreaming }: ChatInputProps) {
  const [query, setQuery] = useState('')
  const [provider, setProvider] = useState<string>('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      onSend(query, provider || undefined)
      setQuery('')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Ask about your codebase..."
        disabled={isStreaming}
        className="flex-1"
      />
      
      <select
        value={provider}
        onChange={(e) => setProvider(e.target.value)}
        className="px-3 rounded-md border border-input bg-background text-sm"
        disabled={isStreaming}
      >
        <option value="">Auto</option>
        <option value="local">Phi-3</option>
        <option value="sonnet">Sonnet</option>
        <option value="opus">Opus</option>
      </select>

      {isStreaming ? (
        <Button type="button" onClick={onStop} variant="destructive">
          <Square className="w-4 h-4 mr-2" />
          Stop
        </Button>
      ) : (
        <Button type="submit" disabled={!query.trim()}>
          <Send className="w-4 h-4 mr-2" />
          Send
        </Button>
      )}
    </form>
  )
}
