import { useEffect } from 'react'
import { useDocumentStore } from '../store/documentStore'

export function useDocuments() {
  const store = useDocumentStore()

  useEffect(() => {
    useDocumentStore.getState().fetch()
  }, [])

  return store
}
