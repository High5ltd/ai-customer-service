import type { Document } from '../../types/document'
import { EmptyState } from '../shared/EmptyState'
import { DocumentItem } from './DocumentItem'

interface Props {
  documents: Document[]
  onDelete: (id: string) => void
}

export function DocumentList({ documents, onDelete }: Props) {
  if (documents.length === 0) {
    return (
      <EmptyState
        title="No documents yet"
        description="Upload a PDF, DOCX, or TXT file to get started"
      />
    )
  }

  return (
    <div className="flex flex-col gap-0.5">
      {documents.map((doc) => (
        <DocumentItem key={doc.id} doc={doc} onDelete={onDelete} />
      ))}
    </div>
  )
}
