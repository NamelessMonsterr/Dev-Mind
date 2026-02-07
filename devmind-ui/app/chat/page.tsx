'use client'

import { useState, useRef, useEffect } from 'react'
import { ChatInput } from '@/components/ChatInput'
import { MessageBubble } from '@/components/MessageBubble'
import { CitationCard } from '@/components/CitationCard'
import { createChatSocket, type StreamMessage } from '@/lib/ws'

interface Message {
  role: 'user' | 'assistant'
  content: string
  citations?: StreamMessage['citations']
  metadata?: StreamMessage['metadata']
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentResponse, setCurrentResponse] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const socketRef = useRef<ReturnType<typeof createChatSocket> | null>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, currentResponse])

  const handleSend = async (query: string, provider?: string) => {
    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: query }])
    setIsStreaming(true)
    setCurrentResponse('')

    // Create WebSocket connection
    const socket = createChatSocket(
      // onDelta
      (delta: string) => {
        setCurrentResponse(prev => prev + delta)
      },
      // onComplete
      (message: StreamMessage) => {
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: currentResponse,
            citations: message.citations,
            metadata: message.metadata
          }
        ])
        setCurrentResponse('')
        setIsStreaming(false)
      },
      // onError
      (error: string) => {
        console.error('Chat error:', error)
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: `Error: ${error}`
          }
        ])
        setCurrentResponse('')
        setIsStreaming(false)
      }
    )

    socketRef.current = socket

    try {
      await socket.connect({
        query,
        top_k: 10,
        use_query_expansion: true,
        provider,
        temperature: 0.7
      })
    } catch (error) {
      console.error('Failed to connect:', error)
      setIsStreaming(false)
    }
  }

  const handleStop = () => {
    if (socketRef.current) {
      socketRef.current.close()
      setIsStreaming(false)
      if (currentResponse) {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: currentResponse }
        ])
        setCurrentResponse('')
      }
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border p-4">
        <h1 className="text-2xl font-bold">Chat</h1>
        <p className="text-sm text-muted-foreground">
          Ask questions about your codebase
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-center">
            <div className="space-y-4">
              <h2 className="text-xl text-muted-foreground">
                Start a conversation
              </h2>
              <p className="text-sm text-muted-foreground">
                Ask me anything about your codebase
              </p>
              <div className="text-xs text-muted-foreground space-y-1">
                <p>Example: "How does authentication work?"</p>
                <p>Example: "Find the login function"</p>
                <p>Example: "Explain the database schema"</p>
              </div>
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <div key={index}>
            <MessageBubble message={message} />
            {message.citations && message.citations.length > 0 && (
              <div className="mt-2 space-y-2">
                <p className="text-xs text-muted-foreground">Citations:</p>
                {message.citations.map((citation, citIndex) => (
                  <CitationCard key={citIndex} citation={citation} />
                ))}
              </div>
            )}
          </div>
        ))}

        {isStreaming && currentResponse && (
          <MessageBubble
            message={{ role: 'assistant', content: currentResponse }}
            isStreaming
          />
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-border p-4">
        <ChatInput
          onSend={handleSend}
          onStop={handleStop}
          isStreaming={isStreaming}
        />
      </div>
    </div>
  )
}
