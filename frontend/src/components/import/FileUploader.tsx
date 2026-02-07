import { useState, useCallback } from 'react'
import { Upload, File, X } from 'lucide-react'
import { initImport, uploadChunk, startImport, uploadSimple } from '../../api/client'
import type { ImportJob } from '../../api/client'

interface FileUploaderProps {
  onComplete: (job: ImportJob) => void
  onError: (error: string) => void
}

const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB
const SIMPLE_UPLOAD_THRESHOLD = 50 * 1024 * 1024 // 50MB

export default function FileUploader({ onComplete, onError }: FileUploaderProps) {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [dragOver, setDragOver] = useState(false)

  const handleFileSelect = useCallback((selectedFile: File) => {
    const validExtensions = ['.txt', '.zip']
    const ext = selectedFile.name.toLowerCase().slice(selectedFile.name.lastIndexOf('.'))

    if (!validExtensions.includes(ext)) {
      onError('Please select a .txt or .zip file')
      return
    }

    setFile(selectedFile)
  }, [onError])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)

    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      handleFileSelect(droppedFile)
    }
  }, [handleFileSelect])

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    setProgress(0)

    try {
      let job: ImportJob

      if (file.size < SIMPLE_UPLOAD_THRESHOLD) {
        // Simple upload for smaller files
        job = await uploadSimple(file)
      } else {
        // Chunked upload for larger files
        const totalChunks = Math.ceil(file.size / CHUNK_SIZE)
        job = await initImport(file.name, file.size, totalChunks)

        for (let i = 0; i < totalChunks; i++) {
          const start = i * CHUNK_SIZE
          const end = Math.min(start + CHUNK_SIZE, file.size)
          const chunk = file.slice(start, end)

          await uploadChunk(job.id, i, chunk)
          setProgress(Math.round(((i + 1) / totalChunks) * 100))
        }
      }

      // Start processing
      const startedJob = await startImport(job.id)
      onComplete(startedJob)
    } catch (error: any) {
      console.error('Upload error:', error)
      onError(error.response?.data?.detail || error.message || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }

  return (
    <div>
      {/* Drop zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragOver ? 'border-whatsapp-teal bg-whatsapp-teal/5' : 'border-gray-300'
        }`}
      >
        {file ? (
          <div className="flex items-center justify-center gap-3">
            <File className="w-8 h-8 text-whatsapp-teal" />
            <div className="text-left">
              <p className="font-medium text-gray-900">{file.name}</p>
              <p className="text-sm text-gray-500">{formatFileSize(file.size)}</p>
            </div>
            <button
              onClick={() => setFile(null)}
              className="p-1 hover:bg-gray-100 rounded-full"
              disabled={uploading}
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        ) : (
          <>
            <Upload className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <p className="text-gray-600 mb-2">
              Drag and drop your file here, or{' '}
              <label className="text-whatsapp-teal cursor-pointer hover:underline">
                browse
                <input
                  type="file"
                  accept=".txt,.zip"
                  onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                  className="hidden"
                />
              </label>
            </p>
            <p className="text-xs text-gray-400">Supports .txt and .zip files up to 10GB</p>
          </>
        )}
      </div>

      {/* Progress bar */}
      {uploading && (
        <div className="mt-4">
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-gray-600">Uploading...</span>
            <span className="text-gray-900 font-medium">{progress}%</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-whatsapp-teal transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Upload button */}
      {file && !uploading && (
        <button
          onClick={handleUpload}
          className="mt-4 w-full py-2 bg-whatsapp-teal text-white rounded-lg hover:bg-whatsapp-dark transition-colors font-medium"
        >
          Upload and Import
        </button>
      )}
    </div>
  )
}
