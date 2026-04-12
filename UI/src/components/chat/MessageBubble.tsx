import type { Message } from '../../types/chat'
import { SourcesPanel } from './SourcesPanel'

interface Props {
  message: Message
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] ${isUser ? 'order-2' : 'order-1'}`}>
        {/* Avatar */}
        <div className={`flex items-end gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          <div
            className={`w-7 h-7 rounded-full flex items-center justify-center text-sm shrink-0 ${
              isUser ? 'bg-brand-500 text-white' : 'bg-gray-200 text-gray-600'
            }`}
          >
            {isUser ? 'U' : 'AI'}
          </div>

          <div
            className={`rounded-2xl px-4 py-2.5 ${
              isUser
                ? 'bg-brand-500 text-white rounded-br-sm'
                : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm'
            }`}
          >
            <p className="text-sm whitespace-pre-wrap leading-relaxed">
              {message.content}
              {message.isStreaming && (
                <span className="inline-block w-1.5 h-4 ml-0.5 bg-current opacity-70 animate-pulse" />
              )}
            </p>
          </div>
        </div>

        {/* Sources */}
        {!isUser && message.citations && message.citations.length > 0 && !message.isStreaming && (
          <div className="ml-9 mt-1">
            <SourcesPanel citations={message.citations} />
          </div>
        )}
      </div>
    </div>
  )
}
