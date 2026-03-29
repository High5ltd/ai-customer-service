import type { Document } from '../types/document'
import client from './client'

export async function fetchDocuments(): Promise<Document[]> {
  const { data } = await client.get<Document[]>('/documents')
  return data
}

export async function uploadDocument(file: File): Promise<Document> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await client.post<Document>('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function deleteDocument(id: string): Promise<void> {
  await client.delete(`/documents/${id}`)
}
