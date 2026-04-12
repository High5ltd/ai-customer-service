import { useDocuments } from '../../hooks/useDocuments'
import { ErrorBanner } from '../shared/ErrorBanner'
import { LoadingSpinner } from '../shared/LoadingSpinner'
import { DocumentList } from './DocumentList'
import { DocumentUpload } from './DocumentUpload'

export function DocumentSidebar() {
  const { documents, isLoading, isUploading, error, upload, remove } = useDocuments()

  return (
    <aside className="flex flex-col h-full bg-white border-r border-gray-200">
      {/* Header */}
      <div className="px-4 py-4 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Documents</h2>
      </div>

      {/* Upload */}
      <div className="px-3 py-3 border-b border-gray-100">
        <DocumentUpload isUploading={isUploading} onUpload={upload} />
      </div>

      {/* Error */}
      {error && (
        <div className="px-3 py-2">
          <ErrorBanner message={error} />
        </div>
      )}

      {/* List */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-1 py-2">
        {isLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner />
          </div>
        ) : (
          <DocumentList documents={documents} onDelete={remove} />
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-gray-100">
        <p className="text-xs text-gray-400">
          {documents.length} document{documents.length !== 1 ? 's' : ''}
        </p>
      </div>
    </aside>
  )
}
