import { useRef, useState } from 'react'
import { LoadingSpinner } from '../shared/LoadingSpinner'

interface Props {
  isUploading: boolean
  onUpload: (file: File) => void
}

export function DocumentUpload({ isUploading, onUpload }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleFile = (file: File | undefined) => {
    if (file) onUpload(file)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      onClick={() => !isUploading && inputRef.current?.click()}
      className={`
        cursor-pointer rounded-lg border-2 border-dashed p-4 text-center transition-colors
        ${isDragging ? 'border-brand-500 bg-brand-50' : 'border-gray-300 hover:border-brand-400 hover:bg-gray-50'}
        ${isUploading ? 'opacity-60 cursor-not-allowed' : ''}
      `}
    >
      {isUploading ? (
        <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
          <LoadingSpinner size="sm" />
          <span>Uploading...</span>
        </div>
      ) : (
        <>
          <p className="text-sm font-medium text-gray-600">+ Upload document</p>
          <p className="text-xs text-gray-400 mt-1">PDF, DOCX, TXT — drag & drop</p>
        </>
      )}
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept=".pdf,.docx,.doc,.txt,.md"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
    </div>
  )
}
