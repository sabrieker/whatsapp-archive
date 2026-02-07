import { useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useInfiniteQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Search, Share2, Trash2, X, Copy, Check, Pencil, BarChart3 } from 'lucide-react'
import { getConversation, getMessages, searchMessages, generateShareLink, deleteConversation, updateConversation } from '../api/client'
import MessageList from '../components/chat/MessageList'
import SearchBar from '../components/ui/SearchBar'
import AnalyticsDialog from '../components/analytics/AnalyticsDialog'

export default function ChatPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const conversationId = Number(id)

  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [showShareDialog, setShowShareDialog] = useState(false)
  const [showRenameDialog, setShowRenameDialog] = useState(false)
  const [showAnalytics, setShowAnalytics] = useState(false)
  const [newName, setNewName] = useState('')
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  // Fetch conversation details
  const { data: conversation } = useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => getConversation(conversationId),
  })

  // Fetch messages with infinite scroll
  const {
    data: messagesData,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading: isLoadingMessages,
  } = useInfiniteQuery({
    queryKey: ['messages', conversationId],
    queryFn: ({ pageParam = 1 }) => getMessages(conversationId, pageParam, 100),
    getNextPageParam: (lastPage) => (lastPage.has_more ? lastPage.page + 1 : undefined),
    initialPageParam: 1,
  })

  // Search messages
  const { data: searchResults, isLoading: isSearchLoading } = useQuery({
    queryKey: ['search', conversationId, searchQuery],
    queryFn: () => searchMessages(searchQuery, conversationId),
    enabled: searchQuery.length > 0,
  })

  const allMessages = messagesData?.pages.flatMap((page) => page.items) || []
  const displayMessages = searchQuery ? searchResults?.items || [] : allMessages

  const handleShare = async () => {
    try {
      const result = await generateShareLink(conversationId)
      setShareUrl(`${window.location.origin}${result.share_url}`)
      setShowShareDialog(true)
    } catch (error) {
      console.error('Failed to generate share link:', error)
    }
  }

  const handleCopyLink = () => {
    if (shareUrl) {
      navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleDelete = async () => {
    if (window.confirm('Are you sure you want to delete this conversation? This action cannot be undone.')) {
      try {
        await deleteConversation(conversationId)
        navigate('/')
      } catch (error) {
        console.error('Failed to delete conversation:', error)
      }
    }
  }

  const handleRename = () => {
    setNewName(conversation?.name || '')
    setShowRenameDialog(true)
  }

  const handleSaveRename = async () => {
    if (!newName.trim()) return
    try {
      await updateConversation(conversationId, newName.trim())
      queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] })
      queryClient.invalidateQueries({ queryKey: ['conversations'] })
      setShowRenameDialog(false)
    } catch (error) {
      console.error('Failed to rename conversation:', error)
    }
  }

  const handleLoadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage()
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <header className="bg-whatsapp-teal text-white px-4 py-3 flex items-center gap-4">
        <button
          onClick={() => navigate('/')}
          className="p-1 hover:bg-white/20 rounded-full transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex-1 min-w-0 cursor-pointer group" onClick={handleRename}>
          <div className="flex items-center gap-2">
            <h1 className="font-semibold truncate">{conversation?.name || 'Loading...'}</h1>
            <Pencil className="w-4 h-4 opacity-0 group-hover:opacity-70 transition-opacity" />
          </div>
          {conversation && (
            <p className="text-xs text-white/80">
              {conversation.message_count.toLocaleString()} messages
              {conversation.participants.length > 0 && ` · ${conversation.participants.length} participants`}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsSearching(!isSearching)}
            className="p-2 hover:bg-white/20 rounded-full transition-colors"
            title="Search"
          >
            <Search className="w-5 h-5" />
          </button>
          <button
            onClick={() => setShowAnalytics(true)}
            className="p-2 hover:bg-white/20 rounded-full transition-colors"
            title="Analytics"
          >
            <BarChart3 className="w-5 h-5" />
          </button>
          <button
            onClick={handleShare}
            className="p-2 hover:bg-white/20 rounded-full transition-colors"
            title="Share"
          >
            <Share2 className="w-5 h-5" />
          </button>
          <button
            onClick={handleDelete}
            className="p-2 hover:bg-white/20 rounded-full transition-colors text-red-200 hover:text-red-100"
            title="Delete"
          >
            <Trash2 className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Search bar */}
      {isSearching && (
        <div className="bg-white border-b p-3">
          <SearchBar
            value={searchQuery}
            onChange={setSearchQuery}
            placeholder="Search in conversation..."
            autoFocus
          />
          {searchQuery && searchResults && (
            <p className="text-xs text-gray-500 mt-2">
              Found {searchResults.total} messages
            </p>
          )}
        </div>
      )}

      {/* Messages */}
      <main className="flex-1 overflow-hidden chat-bg">
        {isLoadingMessages ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-whatsapp-teal" />
          </div>
        ) : (
          <MessageList
            messages={displayMessages}
            onLoadMore={handleLoadMore}
            hasMore={hasNextPage && !searchQuery}
            isLoading={isFetchingNextPage || isSearchLoading}
          />
        )}
      </main>

      {/* Share Dialog */}
      {showShareDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Share Conversation</h2>
              <button
                onClick={() => setShowShareDialog(false)}
                className="p-1 hover:bg-gray-100 rounded-full"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-gray-600 mb-4">
              Anyone with this link can view this conversation (read-only).
            </p>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={shareUrl || ''}
                readOnly
                className="flex-1 px-3 py-2 border rounded-lg text-sm bg-gray-50"
              />
              <button
                onClick={handleCopyLink}
                className="flex items-center gap-1 px-4 py-2 bg-whatsapp-teal text-white rounded-lg hover:bg-whatsapp-dark transition-colors"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rename Dialog */}
      {showRenameDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Rename Conversation</h2>
              <button
                onClick={() => setShowRenameDialog(false)}
                className="p-1 hover:bg-gray-100 rounded-full"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Conversation name"
              className="w-full px-3 py-2 border rounded-lg text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-whatsapp-teal"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSaveRename()
                if (e.key === 'Escape') setShowRenameDialog(false)
              }}
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowRenameDialog(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveRename}
                disabled={!newName.trim()}
                className="px-4 py-2 bg-whatsapp-teal text-white rounded-lg hover:bg-whatsapp-dark transition-colors disabled:opacity-50"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Analytics Dialog */}
      {showAnalytics && conversation && (
        <AnalyticsDialog
          conversationId={conversationId}
          conversationName={conversation.name}
          onClose={() => setShowAnalytics(false)}
        />
      )}
    </div>
  )
}
