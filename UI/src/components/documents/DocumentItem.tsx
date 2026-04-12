import type { Document } from '../../types/document'

interface Props {
  doc: Document
  onDelete: (id: string) => void
}

const statusColors: Record<string, string> = {
  ready: 'bg-green-100 text-green-700',
  processing: 'bg-yellow-100 text-yellow-700',
  failed: 'bg-red-100 text-red-700',
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function DocumentItem({ doc, onDelete }: Props) {
  return (
    <div className="group flex items-start gap-2 rounded-md px-2 py-2 hover:bg-gray-100 transition-colors">
      <div className="mt-0.5 text-gray-400 text-lg">📄</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800 truncate" title={doc.original_filename}>
          {doc.original_filename}
        </p>
        <div className="flex items-center gap-2 mt-0.5">
          <span
            className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${statusColors[doc.status] ?? 'bg-gray-100 text-gray-600'}`}
          >
            {doc.status}
          </span>
          <span className="text-xs text-gray-400">{formatBytes(doc.file_size)}</span>
          {doc.chunk_count > 0 && (
            <span className="text-xs text-gray-400">{doc.chunk_count} chunks</span>
          )}
        </div>
        {doc.error_message && (
          <p className="text-xs text-red-500 mt-0.5 truncate" title={doc.error_message}>
            {doc.error_message}
          </p>
        )}
      </div>
      <button
        onClick={() => onDelete(doc.id)}
        className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all text-sm p-0.5"
        title="Delete document"
      >
        ✕
      </button>
    </div>
  )
}
