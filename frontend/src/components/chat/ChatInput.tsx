import { useState } from 'react'
import { LoadingSpinner } from '../shared/LoadingSpinner'

interface Props {
  onSend: (message: string) => void
  isStreaming: boolean
}

export function ChatInput({ onSend, isStreaming }: Props) {
  const [input, setInput] = useState('')

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return
    onSend(trimmed)
    setInput('')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-gray-200 bg-white px-4 py-3">
      <div className="flex items-end gap-2 rounded-xl border border-gray-300 bg-white px-3 py-2 focus-within:border-brand-500 focus-within:ring-1 focus-within:ring-brand-500 transition-shadow">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your documents… (Enter to send)"
          rows={1}
          disabled={isStreaming}
          className="flex-1 resize-none outline-none text-sm text-gray-800 placeholder-gray-400 bg-transparent max-h-32 leading-relaxed"
          style={{ minHeight: '24px' }}
          onInput={(e) => {
            const el = e.currentTarget
            el.style.height = 'auto'
            el.style.height = `${el.scrollHeight}px`
          }}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isStreaming}
          className="shrink-0 w-8 h-8 rounded-lg bg-brand-500 text-white flex items-center justify-center hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {isStreaming ? <LoadingSpinner size="sm" /> : '↑'}
        </button>
      </div>
      <p className="mt-1 text-xs text-gray-400 text-center">
        Shift+Enter for new line · Enter to send
      </p>
    </div>
  )
}
