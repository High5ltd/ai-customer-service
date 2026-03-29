import type { Citation } from '../types/chat'

export function createChatStream(
  question: string,
  sessionId: string,
  onToken: (token: string) => void,
  onCitations: (citations: Citation[]) => void,
  onDone: () => void,
  onError: (err: Event) => void,
  documentIds?: string[],
): EventSource {
  const params = new URLSearchParams({
    question,
    session_id: sessionId,
  })
  if (documentIds?.length) {
    params.set('document_ids', documentIds.join(','))
  }

  const es = new EventSource(`/api/v1/chat/stream?${params}`)

  es.onmessage = (e) => {
    if (e.data === '[DONE]') {
      onDone()
      es.close()
      return
    }
    try {
      const token = JSON.parse(e.data) as string
      onToken(token)
    } catch {
      onToken(e.data)
    }
  }

  es.addEventListener('citations', (e: MessageEvent) => {
    try {
      const citations = JSON.parse(e.data) as Citation[]
      onCitations(citations)
    } catch {
      // ignore parse errors
    }
  })

  es.onerror = (e) => {
    onError(e)
    es.close()
  }

  return es
}

export async function clearSession(sessionId: string): Promise<void> {
  await fetch(`/api/v1/chat/session/${sessionId}`, { method: 'DELETE' })
}
