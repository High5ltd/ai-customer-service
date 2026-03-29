import { create } from 'zustand'
import type { Citation, Message } from '../types/chat'

let msgCounter = 0
const newId = () => `msg-${++msgCounter}`

interface ChatState {
  messages: Message[]
  isStreaming: boolean
  sessionId: string
  addMessage: (role: 'user' | 'assistant', content: string) => string
  appendToken: (id: string, token: string) => void
  setMessageCitations: (id: string, citations: Citation[]) => void
  setStreaming: (streaming: boolean) => void
  setStreamingDone: (id: string) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  sessionId: crypto.randomUUID(),

  addMessage: (role, content) => {
    const id = newId()
    set((state) => ({
      messages: [
        ...state.messages,
        { id, role, content, isStreaming: role === 'assistant' },
      ],
    }))
    return id
  },

  appendToken: (id, token) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + token } : m,
      ),
    }))
  },

  setMessageCitations: (id, citations) => {
    set((state) => ({
      messages: state.messages.map((m) => (m.id === id ? { ...m, citations } : m)),
    }))
  },

  setStreaming: (streaming) => set({ isStreaming: streaming }),

  setStreamingDone: (id) => {
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, isStreaming: false } : m,
      ),
      isStreaming: false,
    }))
  },

  clearMessages: () => set({ messages: [], sessionId: crypto.randomUUID() }),
}))
