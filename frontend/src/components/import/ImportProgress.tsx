import { useEffect, useState } from 'react'
import { getImportProgress } from '../../api/client'
import type { ImportProgress as ImportProgressType } from '../../api/client'

interface ImportProgressProps {
  jobId: number
  onComplete: () => void
  onError: (error: string) => void
}

export default function ImportProgress({ jobId, onComplete, onError }: ImportProgressProps) {
  const [progress, setProgress] = useState<ImportProgressType | null>(null)

  useEffect(() => {
    let intervalId: NodeJS.Timeout

    const checkProgress = async () => {
      try {
        const data = await getImportProgress(jobId)
        setProgress(data)

        if (data.status === 'completed') {
          clearInterval(intervalId)
          onComplete()
        } else if (data.status === 'failed') {
          clearInterval(intervalId)
          onError(data.error_message || 'Import failed')
        }
      } catch (error: any) {
        clearInterval(intervalId)
        onError(error.message || 'Failed to get import progress')
      }
    }

    checkProgress()
    intervalId = setInterval(checkProgress, 1000)

    return () => clearInterval(intervalId)
  }, [jobId, onComplete, onError])

  if (!progress) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-whatsapp-teal" />
      </div>
    )
  }

  const getStatusText = () => {
    switch (progress.status) {
      case 'uploading':
        return 'Uploading file...'
      case 'pending':
        return 'Preparing to process...'
      case 'processing':
        return 'Processing messages...'
      case 'completed':
        return 'Import complete!'
      case 'failed':
        return 'Import failed'
      default:
        return progress.status
    }
  }

  return (
    <div className="py-4">
      {/* Status */}
      <div className="text-center mb-4">
        <p className="text-lg font-medium text-gray-900">{getStatusText()}</p>
      </div>

      {/* Progress bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="text-gray-600">Overall progress</span>
          <span className="text-gray-900 font-medium">
            {Math.round(progress.progress_percent)}%
          </span>
        </div>
        <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-whatsapp-teal transition-all duration-300"
            style={{ width: `${progress.progress_percent}%` }}
          />
        </div>
      </div>

      {/* Details */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-gray-500">Messages</p>
          <p className="text-lg font-semibold text-gray-900">
            {progress.processed_messages.toLocaleString()}
            {progress.total_messages > 0 && (
              <span className="text-gray-500 font-normal text-sm">
                {' '}/ {progress.total_messages.toLocaleString()}
              </span>
            )}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-gray-500">Media files</p>
          <p className="text-lg font-semibold text-gray-900">
            {progress.processed_media.toLocaleString()}
            {progress.total_media > 0 && (
              <span className="text-gray-500 font-normal text-sm">
                {' '}/ {progress.total_media.toLocaleString()}
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Spinner */}
      {progress.status === 'processing' && (
        <div className="flex justify-center mt-6">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-whatsapp-teal" />
        </div>
      )}
    </div>
  )
}
