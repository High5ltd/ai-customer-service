import { useState } from 'react'
import type { Citation } from '../../types/chat'

interface Props {
  citations: Citation[]
}

export function SourcesPanel({ citations }: Props) {
  const [expanded, setExpanded] = useState(false)

  if (citations.length === 0) return null

  return (
    <div className="mt-2 rounded-md border border-gray-200 bg-gray-50 text-xs overflow-hidden">
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center justify-between px-3 py-2 text-gray-600 hover:bg-gray-100 transition-colors"
      >
        <span className="font-medium">Sources ({citations.length})</span>
        <span>{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="divide-y divide-gray-200">
          {citations.map((c) => (
            <div key={c.index} className="px-3 py-2">
              <div className="flex items-center gap-2 mb-1">
                <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-brand-500 text-white text-xs font-bold">
                  {c.index}
                </span>
                <span className="font-medium text-gray-700">{c.filename}</span>
                <span className="text-gray-400">· p.{c.page_number}</span>
                <span className="ml-auto text-gray-400">{(c.score * 100).toFixed(0)}%</span>
              </div>
              <p className="text-gray-600 leading-relaxed line-clamp-3">{c.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
