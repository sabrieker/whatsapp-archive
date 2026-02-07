import { format } from 'date-fns'
import { Users, User } from 'lucide-react'
import type { Conversation } from '../../api/client'

interface ChatListProps {
  conversations: Conversation[]
  onSelect: (id: number) => void
}

export default function ChatList({ conversations, onSelect }: ChatListProps) {
  return (
    <div className="h-full overflow-y-auto bg-white">
      {conversations.map((conversation) => (
        <div
          key={conversation.id}
          onClick={() => onSelect(conversation.id)}
          className="flex items-center gap-3 px-4 py-3 hover:bg-whatsapp-hover cursor-pointer border-b border-gray-100"
        >
          {/* Avatar */}
          <div className="w-12 h-12 rounded-full bg-whatsapp-teal flex items-center justify-center text-white flex-shrink-0">
            {conversation.is_group ? (
              <Users className="w-6 h-6" />
            ) : (
              <User className="w-6 h-6" />
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-900 truncate">
                {conversation.name}
              </h3>
              {conversation.last_message_at && (
                <span className="text-xs text-gray-500 flex-shrink-0 ml-2">
                  {format(new Date(conversation.last_message_at), 'MMM d, yyyy')}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500 truncate">
              {conversation.message_count.toLocaleString()} messages
              {conversation.participants.length > 0 && (
                <> · {conversation.participants.length} participants</>
              )}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
