import { useRef, useEffect, useMemo } from 'react'
import { format, isSameDay } from 'date-fns'
import type { Message } from '../../api/client'
import MessageBubble from './MessageBubble'

interface MessageListProps {
  messages: Message[]
  onLoadMore?: () => void
  hasMore?: boolean
  isLoading?: boolean
}

export default function MessageList({
  messages,
  onLoadMore,
  hasMore = false,
  isLoading = false,
}: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const loadMoreRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const isInitialLoad = useRef(true)

  // Reverse messages so oldest is first (API returns newest first)
  const sortedMessages = useMemo(() => {
    return [...messages].sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    )
  }, [messages])

  // Scroll to bottom on initial load
  useEffect(() => {
    if (isInitialLoad.current && sortedMessages.length > 0 && bottomRef.current) {
      bottomRef.current.scrollIntoView()
      isInitialLoad.current = false
    }
  }, [sortedMessages.length])

  // Infinite scroll observer for loading older messages
  useEffect(() => {
    if (!loadMoreRef.current || !onLoadMore) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !isLoading) {
          onLoadMore()
        }
      },
      { threshold: 0.1 }
    )

    observer.observe(loadMoreRef.current)
    return () => observer.disconnect()
  }, [hasMore, isLoading, onLoadMore])

  // Group messages by date
  const groupedMessages: { date: Date; messages: Message[] }[] = []
  let currentDate: Date | null = null
  let currentGroup: Message[] = []

  sortedMessages.forEach((message) => {
    const messageDate = new Date(message.timestamp)
    if (!currentDate || !isSameDay(currentDate, messageDate)) {
      if (currentGroup.length > 0) {
        groupedMessages.push({ date: currentDate!, messages: currentGroup })
      }
      currentDate = messageDate
      currentGroup = [message]
    } else {
      currentGroup.push(message)
    }
  })

  if (currentGroup.length > 0 && currentDate) {
    groupedMessages.push({ date: currentDate, messages: currentGroup })
  }

  // Check if message is first in a sender group
  const isFirstInSenderGroup = (message: Message, index: number, group: Message[]) => {
    if (index === 0) return true
    return group[index - 1].sender_name !== message.sender_name
  }

  return (
    <div ref={containerRef} className="h-full overflow-y-auto px-4 py-2">
      {/* Load more trigger at top (for older messages) */}
      {hasMore && (
        <div ref={loadMoreRef} className="flex justify-center py-4">
          {isLoading ? (
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-whatsapp-teal" />
          ) : (
            <button
              onClick={onLoadMore}
              className="text-sm text-whatsapp-teal hover:underline"
            >
              Load older messages
            </button>
          )}
        </div>
      )}

      {/* Messages grouped by date */}
      {groupedMessages.map((group, groupIndex) => (
        <div key={groupIndex}>
          {/* Date separator */}
          <div className="flex justify-center my-4">
            <div className="bg-white/90 text-gray-600 text-xs px-3 py-1 rounded-lg shadow-sm">
              {format(group.date, 'MMMM d, yyyy')}
            </div>
          </div>

          {/* Messages for this date */}
          {group.messages.map((message, messageIndex) => (
            <MessageBubble
              key={message.id}
              message={message}
              showSender={true}
              showAvatar={true}
              isFirstInGroup={isFirstInSenderGroup(message, messageIndex, group.messages)}
            />
          ))}
        </div>
      ))}

      {/* Empty state */}
      {messages.length === 0 && !isLoading && (
        <div className="flex items-center justify-center h-full text-gray-500">
          <p>No messages to display</p>
        </div>
      )}

      {/* Loading indicator for initial load */}
      {isLoading && messages.length === 0 && (
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-whatsapp-teal" />
        </div>
      )}

      {/* Bottom anchor for scrolling */}
      <div ref={bottomRef} />
    </div>
  )
}
