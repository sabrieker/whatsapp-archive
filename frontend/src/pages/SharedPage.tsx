import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useInfiniteQuery } from '@tanstack/react-query'
import { MessageSquare, Search, Lock } from 'lucide-react'
import { getSharedConversation, getSharedMessages, searchSharedMessages } from '../api/client'
import MessageList from '../components/chat/MessageList'
import SearchBar from '../components/ui/SearchBar'

export default function SharedPage() {
  const { token } = useParams<{ token: string }>()
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)

  // Fetch conversation details
  const { data: conversation, isError, error } = useQuery({
    queryKey: ['shared-conversation', token],
    queryFn: () => getSharedConversation(token!),
    enabled: !!token,
  })

  // Fetch messages with infinite scroll
  const {
    data: messagesData,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading: isLoadingMessages,
  } = useInfiniteQuery({
    queryKey: ['shared-messages', token],
    queryFn: ({ pageParam = 1 }) => getSharedMessages(token!, pageParam, 100),
    getNextPageParam: (lastPage) => (lastPage.has_more ? lastPage.page + 1 : undefined),
    initialPageParam: 1,
    enabled: !!token && !!conversation,
  })

  // Search messages
  const { data: searchResults, isLoading: isSearchLoading } = useQuery({
    queryKey: ['shared-search', token, searchQuery],
    queryFn: () => searchSharedMessages(token!, searchQuery),
    enabled: !!token && searchQuery.length > 0,
  })

  const allMessages = messagesData?.pages.flatMap((page) => page.items) || []
  const displayMessages = searchQuery ? searchResults?.items || [] : allMessages

  const handleLoadMore = () => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage()
    }
  }

  if (isError) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-gray-100">
        <Lock className="w-16 h-16 text-gray-400 mb-4" />
        <h1 className="text-xl font-semibold text-gray-700 mb-2">Conversation Not Found</h1>
        <p className="text-gray-500">This shared link may have expired or been revoked.</p>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <header className="bg-whatsapp-teal text-white px-4 py-3 flex items-center gap-4">
        <MessageSquare className="w-6 h-6" />
        <div className="flex-1 min-w-0">
          <h1 className="font-semibold truncate">{conversation?.name || 'Loading...'}</h1>
          {conversation && (
            <p className="text-xs text-white/80">
              {conversation.message_count.toLocaleString()} messages · Shared view (read-only)
            </p>
          )}
        </div>
        <button
          onClick={() => setIsSearching(!isSearching)}
          className="p-2 hover:bg-white/20 rounded-full transition-colors"
        >
          <Search className="w-5 h-5" />
        </button>
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
    </div>
  )
}
