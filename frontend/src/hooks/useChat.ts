import { useRef } from 'react'
import { createChatStream } from '../api/chat'
import { useChatStore } from '../store/chatStore'

export function useChat() {
  const store = useChatStore()
  const esRef = useRef<EventSource | null>(null)

  const sendMessage = (question: string, documentIds?: string[]) => {
    if (store.isStreaming) return

    // Add user message
    store.addMessage('user', question)

    // Add empty assistant message to fill via streaming
    const assistantId = store.addMessage('assistant', '')
    store.setStreaming(true)

    esRef.current = createChatStream(
      question,
      store.sessionId,
      (token) => store.appendToken(assistantId, token),
      (citations) => store.setMessageCitations(assistantId, citations),
      () => store.setStreamingDone(assistantId),
      () => store.setStreamingDone(assistantId),
      documentIds,
    )
  }

  const stopStreaming = () => {
    esRef.current?.close()
    store.setStreaming(false)
  }

  return {
    messages: store.messages,
    isStreaming: store.isStreaming,
    sessionId: store.sessionId,
    sendMessage,
    stopStreaming,
    clearMessages: store.clearMessages,
  }
}
