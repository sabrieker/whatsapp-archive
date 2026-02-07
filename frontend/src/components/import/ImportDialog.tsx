import { useState } from 'react'
import { X, AlertCircle } from 'lucide-react'
import FileUploader from './FileUploader'
import ImportProgress from './ImportProgress'
import type { ImportJob } from '../../api/client'

interface ImportDialogProps {
  onClose: () => void
  onComplete: () => void
}

type ImportStep = 'upload' | 'progress' | 'complete' | 'error'

export default function ImportDialog({ onClose, onComplete }: ImportDialogProps) {
  const [step, setStep] = useState<ImportStep>('upload')
  const [job, setJob] = useState<ImportJob | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleUploadComplete = (uploadedJob: ImportJob) => {
    setJob(uploadedJob)
    setStep('progress')
  }

  const handleUploadError = (errorMessage: string) => {
    setError(errorMessage)
    setStep('error')
  }

  const handleImportComplete = () => {
    setStep('complete')
    setTimeout(() => {
      onComplete()
    }, 1500)
  }

  const handleImportError = (errorMessage: string) => {
    setError(errorMessage)
    setStep('error')
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Import WhatsApp Chat</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded-full"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        {step === 'upload' && (
          <>
            <p className="text-sm text-gray-600 mb-4">
              Upload a WhatsApp chat export file (.txt or .zip with media).
            </p>
            <FileUploader
              onComplete={handleUploadComplete}
              onError={handleUploadError}
            />
            <div className="mt-4 text-xs text-gray-500">
              <p className="font-medium mb-1">How to export from WhatsApp:</p>
              <ol className="list-decimal list-inside space-y-1">
                <li>Open the chat in WhatsApp</li>
                <li>Tap the menu (⋮) → More → Export chat</li>
                <li>Choose "Include Media" or "Without Media"</li>
                <li>Save the file and upload it here</li>
              </ol>
            </div>
          </>
        )}

        {step === 'progress' && job && (
          <ImportProgress
            jobId={job.id}
            onComplete={handleImportComplete}
            onError={handleImportError}
          />
        )}

        {step === 'complete' && (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Import Complete!</h3>
            <p className="text-gray-600">Your chat has been imported successfully.</p>
          </div>
        )}

        {step === 'error' && (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-8 h-8 text-red-500" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Import Failed</h3>
            <p className="text-red-600 mb-4">{error}</p>
            <button
              onClick={() => {
                setStep('upload')
                setError(null)
                setJob(null)
              }}
              className="px-4 py-2 bg-whatsapp-teal text-white rounded-lg hover:bg-whatsapp-dark transition-colors"
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
