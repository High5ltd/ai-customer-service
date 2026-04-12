interface Props {
  index: number
  onClick?: () => void
}

export function CitationBadge({ index, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-brand-500 text-white text-xs font-bold hover:bg-brand-600 transition-colors align-super"
      style={{ fontSize: '10px', lineHeight: 1 }}
      title={`Source ${index}`}
    >
      {index}
    </button>
  )
}
