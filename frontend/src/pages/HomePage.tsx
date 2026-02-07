import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { MessageSquare, Upload, Search } from 'lucide-react'
import { getConversations } from '../api/client'
import ChatList from '../components/chat/ChatList'
import ImportDialog from '../components/import/ImportDialog'
import SearchBar from '../components/ui/SearchBar'

export default function HomePage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [showImport, setShowImport] = useState(false)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['conversations', search],
    queryFn: () => getConversations(1, 50, search || undefined),
  })

  const handleConversationClick = (id: number) => {
    navigate(`/chat/${id}`)
  }

  const handleImportComplete = () => {
    setShowImport(false)
    refetch()
  }

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <header className="bg-whatsapp-teal text-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-6 h-6" />
          <h1 className="text-xl font-semibold">WhatsApp Archive</h1>
        </div>
        <button
          onClick={() => setShowImport(true)}
          className="flex items-center gap-2 bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg transition-colors"
        >
          <Upload className="w-4 h-4" />
          <span>Import Chat</span>
        </button>
      </header>

      {/* Search */}
      <div className="p-4 bg-white border-b">
        <SearchBar
          value={search}
          onChange={setSearch}
          placeholder="Search conversations..."
        />
      </div>

      {/* Content */}
      <main className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-whatsapp-teal" />
          </div>
        ) : data?.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <MessageSquare className="w-16 h-16 mb-4 opacity-50" />
            <p className="text-lg mb-2">No conversations yet</p>
            <p className="text-sm">Import a WhatsApp chat export to get started</p>
            <button
              onClick={() => setShowImport(true)}
              className="mt-4 flex items-center gap-2 bg-whatsapp-teal text-white px-6 py-2 rounded-lg hover:bg-whatsapp-dark transition-colors"
            >
              <Upload className="w-4 h-4" />
              <span>Import Chat</span>
            </button>
          </div>
        ) : (
          <ChatList
            conversations={data?.items || []}
            onSelect={handleConversationClick}
          />
        )}
      </main>

      {/* Import Dialog */}
      {showImport && (
        <ImportDialog
          onClose={() => setShowImport(false)}
          onComplete={handleImportComplete}
        />
      )}
    </div>
  )
}
