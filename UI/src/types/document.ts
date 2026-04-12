export interface Document {
  id: string
  filename: string
  original_filename: string
  mime_type: string
  file_size: number
  status: 'processing' | 'ready' | 'failed'
  chunk_count: number
  error_message: string | null
  created_at: string
  updated_at: string
}
