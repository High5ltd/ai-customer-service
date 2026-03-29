export interface Citation {
  index: number
  document_id: string
  filename: string
  page_number: number
  chunk_index: number
  score: number
  text: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  isStreaming?: boolean
}
