import { useState } from 'react'
import { format } from 'date-fns'
import { Image, Video, FileText, Music, MapPin, X, Play } from 'lucide-react'
import type { Message } from '../../api/client'

interface MessageBubbleProps {
  message: Message
  showSender?: boolean
  showAvatar?: boolean
  isFirstInGroup?: boolean
}

// URL regex pattern
const URL_REGEX = /(https?:\/\/[^\s<]+[^<.,:;"')\]\s])/g

// Get initials from name
function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
}

// Function to render text with clickable links
function renderContentWithLinks(content: string) {
  const parts = content.split(URL_REGEX)

  return parts.map((part, index) => {
    if (URL_REGEX.test(part)) {
      URL_REGEX.lastIndex = 0
      return (
        <a
          key={index}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:underline break-all"
        >
          {part}
        </a>
      )
    }
    return part
  })
}

export default function MessageBubble({
  message,
  showSender = true,
  showAvatar = true,
  isFirstInGroup = true
}: MessageBubbleProps) {
  const [lightboxMedia, setLightboxMedia] = useState<string | null>(null)
  const isSystem = message.message_type === 'system'

  if (isSystem) {
    return (
      <div className="flex justify-center my-2">
        <div className="bg-white/80 text-gray-600 text-xs px-3 py-1 rounded-lg shadow-sm">
          {message.content}
        </div>
      </div>
    )
  }

  const getMediaIcon = () => {
    switch (message.message_type) {
      case 'image':
        return <Image className="w-4 h-4" />
      case 'video':
        return <Video className="w-4 h-4" />
      case 'audio':
        return <Music className="w-4 h-4" />
      case 'document':
        return <FileText className="w-4 h-4" />
      case 'location':
        return <MapPin className="w-4 h-4" />
      default:
        return null
    }
  }

  const senderColor = message.participant_color || '#128C7E'

  return (
    <>
      <div className={`flex gap-2 mb-0.5 ${isFirstInGroup ? 'mt-2' : ''}`}>
        {/* Avatar - only show for first message in group */}
        <div className="w-8 flex-shrink-0">
          {showAvatar && isFirstInGroup && (
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-semibold"
              style={{ backgroundColor: senderColor }}
            >
              {getInitials(message.sender_name)}
            </div>
          )}
        </div>

        {/* Message content */}
        <div className="flex-1 max-w-[75%]">
          <div className="bg-white rounded-lg shadow-sm px-3 py-1.5 inline-block">
            {/* Sender name - only on first message */}
            {showSender && isFirstInGroup && (
              <p
                className="text-xs font-semibold mb-0.5"
                style={{ color: senderColor }}
              >
                {message.sender_name}
              </p>
            )}

            {/* Media - thumbnails */}
            {message.has_media && message.media_files.length > 0 && (
              <div className="mb-1">
                {message.media_files.map((media) => (
                  <div key={media.id} className="relative">
                    {media.media_type === 'image' && media.url && (
                      <img
                        src={media.url}
                        alt={media.original_filename || 'Image'}
                        className="max-w-[200px] max-h-[150px] rounded cursor-pointer hover:opacity-90 object-cover"
                        onClick={() => setLightboxMedia(media.url!)}
                      />
                    )}
                    {media.media_type === 'video' && media.url && (
                      <div
                        className="relative max-w-[200px] cursor-pointer"
                        onClick={() => setLightboxMedia(media.url!)}
                      >
                        <video
                          src={media.url}
                          className="max-w-[200px] max-h-[150px] rounded object-cover"
                        />
                        <div className="absolute inset-0 flex items-center justify-center bg-black/30 rounded">
                          <Play className="w-10 h-10 text-white" fill="white" />
                        </div>
                      </div>
                    )}
                    {media.media_type === 'audio' && media.url && (
                      <audio src={media.url} controls className="w-48 h-8" />
                    )}
                    {!['image', 'video', 'audio'].includes(media.media_type) && (
                      <a
                        href={media.url || '#'}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 text-whatsapp-teal hover:underline text-sm"
                      >
                        <FileText className="w-4 h-4" />
                        <span>{media.original_filename || 'Download'}</span>
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Media indicator without actual file */}
            {message.has_media && message.media_files.length === 0 && (
              <div className="flex items-center gap-1 text-gray-400 italic text-xs mb-1">
                {getMediaIcon()}
                <span>{message.message_type} omitted</span>
              </div>
            )}

            {/* Content with clickable links */}
            {message.content && (
              <p className="text-gray-800 whitespace-pre-wrap break-words text-sm">
                {renderContentWithLinks(message.content)}
              </p>
            )}

            {/* Timestamp */}
            <p className="text-[10px] text-gray-500 text-right -mb-0.5">
              {format(new Date(message.timestamp), 'HH:mm')}
            </p>
          </div>
        </div>
      </div>

      {/* Lightbox for full-size media */}
      {lightboxMedia && (
        <div
          className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center"
          onClick={() => setLightboxMedia(null)}
        >
          <button
            className="absolute top-4 right-4 text-white hover:text-gray-300"
            onClick={() => setLightboxMedia(null)}
          >
            <X className="w-8 h-8" />
          </button>
          {lightboxMedia.includes('.mp4') || lightboxMedia.includes('video') ? (
            <video
              src={lightboxMedia}
              controls
              autoPlay
              className="max-w-[90vw] max-h-[90vh]"
              onClick={(e) => e.stopPropagation()}
            />
          ) : (
            <img
              src={lightboxMedia}
              alt="Full size"
              className="max-w-[90vw] max-h-[90vh] object-contain"
              onClick={(e) => e.stopPropagation()}
            />
          )}
        </div>
      )}
    </>
  )
}
