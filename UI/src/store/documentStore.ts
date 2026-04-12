import { create } from 'zustand'
import { deleteDocument, fetchDocuments, uploadDocument } from '../api/documents'
import type { Document } from '../types/document'

interface DocumentState {
  documents: Document[]
  isLoading: boolean
  isUploading: boolean
  error: string | null
  fetch: () => Promise<void>
  upload: (file: File) => Promise<void>
  remove: (id: string) => Promise<void>
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  documents: [],
  isLoading: false,
  isUploading: false,
  error: null,

  fetch: async () => {
    set({ isLoading: true, error: null })
    try {
      const docs = await fetchDocuments()
      set({ documents: docs })
    } catch (e: unknown) {
      set({ error: e instanceof Error ? e.message : 'Failed to fetch documents' })
    } finally {
      set({ isLoading: false })
    }
  },

  upload: async (file: File) => {
    set({ isUploading: true, error: null })
    try {
      const doc = await uploadDocument(file)
      set((state) => ({ documents: [doc, ...state.documents] }))
    } catch (e: unknown) {
      set({ error: e instanceof Error ? e.message : 'Upload failed' })
      throw e
    } finally {
      set({ isUploading: false })
    }
  },

  remove: async (id: string) => {
    try {
      await deleteDocument(id)
      set((state) => ({ documents: state.documents.filter((d) => d.id !== id) }))
    } catch (e: unknown) {
      set({ error: e instanceof Error ? e.message : 'Delete failed' })
      throw e
    }
  },
}))
