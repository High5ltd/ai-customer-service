import { useChat } from '../../hooks/useChat'
import { ChatInput } from './ChatInput'
import { MessageList } from './MessageList'

export function ChatWindow() {
  const { messages, isStreaming, sendMessage, clearMessages, sessionId } = useChat()

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 bg-white border-b border-gray-200">
        <div>
          <h1 className="text-base font-semibold text-gray-800">RAG Assistant</h1>
          <p className="text-xs text-gray-400 mt-0.5">Session: {sessionId.slice(0, 8)}…</p>
        </div>
        <button
          onClick={clearMessages}
          className="text-xs text-gray-400 hover:text-gray-600 px-2 py-1 rounded hover:bg-gray-100 transition-colors"
        >
          Clear chat
        </button>
      </div>

      {/* Messages */}
      <MessageList messages={messages} />

      {/* Input */}
      <ChatInput onSend={sendMessage} isStreaming={isStreaming} />
    </div>
  )
}
