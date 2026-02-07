'use client'

import { cn } from '@/lib/utils'
import { User, Bot, Loader2 } from 'lucide-react'

interface MessageBubbleProps {
  message: {
    role: 'user' | 'assistant'
    content: string
  }
  isStreaming?: boolean
}

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={cn('flex gap-3', isUser && 'flex-row-reverse')}>
      <div className={cn(
        'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
        isUser ? 'bg-primary' : 'bg-secondary'
      )}>
        {isUser ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
      </div>

      <div className={cn(
        'flex-1 max-w-3xl p-4 rounded-lg',
        isUser
          ? 'bg-primary text-primary-foreground'
          : 'bg-muted'
      )}>
        <p className="whitespace-pre-wrap">{message.content}</p>
        {isStreaming && (
          <Loader2 className="w-4 h-4 animate-spin mt-2 text-muted-foreground" />
        )}
      </div>
    </div>
  )
}
