import { ChatWindow } from './components/chat/ChatWindow'
import { DocumentSidebar } from './components/documents/DocumentSidebar'
import { AppLayout } from './components/layout/AppLayout'

export default function App() {
  return <AppLayout sidebar={<DocumentSidebar />} main={<ChatWindow />} />
}
