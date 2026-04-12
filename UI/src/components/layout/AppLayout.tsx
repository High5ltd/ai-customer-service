import type { ReactNode } from 'react'

interface Props {
  sidebar: ReactNode
  main: ReactNode
}

export function AppLayout({ sidebar, main }: Props) {
  return (
    <div className="flex h-screen overflow-hidden">
      <div className="w-72 shrink-0 flex flex-col overflow-hidden">{sidebar}</div>
      <div className="flex-1 flex flex-col overflow-hidden">{main}</div>
    </div>
  )
}
