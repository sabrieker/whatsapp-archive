import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface Participant {
  id: number
  conversation_id: number
  name: string
  phone_number: string | null
  message_count: number
  color: string
  created_at: string
}

export interface Conversation {
  id: number
  name: string
  is_group: boolean
  share_token: string | null
  message_count: number
  first_message_at: string | null
  last_message_at: string | null
  created_at: string
  participants: Participant[]
}

export interface ConversationList {
  items: Conversation[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface MediaFile {
  id: number
  message_id: number
  storage_key: string
  media_type: string
  mime_type: string | null
  file_size: number | null
  original_filename: string | null
  url: string | null
  thumbnail_url: string | null
}

export interface Message {
  id: number
  conversation_id: number
  participant_id: number | null
  sender_name: string
  content: string | null
  message_type: string
  timestamp: string
  has_media: boolean
  media_files: MediaFile[]
  participant_color: string | null
}

export interface MessageList {
  items: Message[]
  total: number
  page: number
  per_page: number
  pages: number
  has_more: boolean
}

export interface ImportJob {
  id: number
  conversation_id: number | null
  status: string
  filename: string | null
  file_size: number | null
  total_chunks: number
  uploaded_chunks: number
  total_messages: number
  processed_messages: number
  total_media: number
  processed_media: number
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export interface ImportProgress {
  job_id: number
  status: string
  progress_percent: number
  total_messages: number
  processed_messages: number
  total_media: number
  processed_media: number
  error_message: string | null
}

// Conversations
export const getConversations = async (page = 1, perPage = 20, search?: string): Promise<ConversationList> => {
  const params = new URLSearchParams({ page: String(page), per_page: String(perPage) })
  if (search) params.append('search', search)
  const { data } = await api.get(`/conversations?${params}`)
  return data
}

export const getConversation = async (id: number): Promise<Conversation> => {
  const { data } = await api.get(`/conversations/${id}`)
  return data
}

export const deleteConversation = async (id: number): Promise<void> => {
  await api.delete(`/conversations/${id}`)
}

export const updateConversation = async (id: number, name: string): Promise<Conversation> => {
  const { data } = await api.patch(`/conversations/${id}`, { name })
  return data
}

export const generateShareLink = async (id: number): Promise<{ share_token: string; share_url: string }> => {
  const { data } = await api.post(`/conversations/${id}/share`)
  return data
}

export const revokeShareLink = async (id: number): Promise<void> => {
  await api.delete(`/conversations/${id}/share`)
}

// Messages
export const getMessages = async (
  conversationId: number,
  page = 1,
  perPage = 50
): Promise<MessageList> => {
  const { data } = await api.get(
    `/messages/conversation/${conversationId}?page=${page}&per_page=${perPage}`
  )
  return data
}

// Search
export const searchMessages = async (
  query: string,
  conversationId?: number,
  page = 1,
  perPage = 50
): Promise<MessageList> => {
  const params = new URLSearchParams({ q: query, page: String(page), per_page: String(perPage) })
  if (conversationId) params.append('conversation_id', String(conversationId))
  const { data } = await api.get(`/search?${params}`)
  return data
}

// Import
export const initImport = async (filename: string, fileSize: number, totalChunks: number): Promise<ImportJob> => {
  const { data } = await api.post('/import/init', { filename, file_size: fileSize, total_chunks: totalChunks })
  return data
}

export const uploadChunk = async (jobId: number, chunkNumber: number, chunk: Blob): Promise<{ complete: boolean }> => {
  const formData = new FormData()
  formData.append('job_id', String(jobId))
  formData.append('chunk_number', String(chunkNumber))
  formData.append('file', chunk)
  const { data } = await api.post('/import/upload/chunk', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const uploadSimple = async (file: File): Promise<ImportJob> => {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/import/upload/simple', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const startImport = async (jobId: number): Promise<ImportJob> => {
  const { data } = await api.post('/import/start', { job_id: jobId })
  return data
}

export const getImportProgress = async (jobId: number): Promise<ImportProgress> => {
  const { data } = await api.get(`/import/progress/${jobId}`)
  return data
}

// Shared
export const getSharedConversation = async (token: string): Promise<Conversation> => {
  const { data } = await api.get(`/shared/${token}`)
  return data
}

export const getSharedMessages = async (token: string, page = 1, perPage = 50): Promise<MessageList> => {
  const { data } = await api.get(`/shared/${token}/messages?page=${page}&per_page=${perPage}`)
  return data
}

export const searchSharedMessages = async (
  token: string,
  query: string,
  page = 1,
  perPage = 50
): Promise<MessageList> => {
  const { data } = await api.get(`/shared/${token}/search?q=${query}&page=${page}&per_page=${perPage}`)
  return data
}

// Analytics
export interface AnalyticsParticipant {
  id: number
  name: string
  color: string
  message_count: number
}

export interface AnalyticsSummary {
  total_messages: number
  date_range: {
    start: string
    end: string
    days: number
    years: number
  }
  avg_messages_per_day: number
  most_active_hour: number
  most_active_day: string
  longest_streak_days?: number
  participants: {
    name: string
    messages: number
    percentage: number
    most_active_hour: number
    color: string
  }[]
  top_participants?: {
    name: string
    messages: number
    percentage: number
    color: string
  }[]
}

export interface CalendarHeatmap {
  year: string | number
  url: string
}

export interface AnalyticsResult {
  charts: {
    time_heatmap: string
    calendar_heatmaps: CalendarHeatmap[]
    comparison_heatmap?: string
    trend: string
    response_time?: string
    daily_activity: string
    top_participants?: string
    participation_over_time?: string
  }
  summary: AnalyticsSummary
  participants: AnalyticsParticipant[]
  generated_at: string
  is_group_chat?: boolean
}

export const getAnalyticsParticipants = async (conversationId: number): Promise<{ participants: AnalyticsParticipant[] }> => {
  const { data } = await api.get(`/analytics/${conversationId}/participants`)
  return data
}

export const getCachedAnalytics = async (conversationId: number): Promise<AnalyticsResult | null> => {
  try {
    const { data } = await api.get(`/analytics/${conversationId}`)
    return data
  } catch {
    return null
  }
}

export const generateAnalytics = async (
  conversationId: number,
  person1?: string,
  person2?: string
): Promise<AnalyticsResult> => {
  const params = new URLSearchParams()
  // Only add params if both are provided (comparison mode)
  if (person1 && person2) {
    params.append('person1', person1)
    params.append('person2', person2)
  }
  const queryString = params.toString()
  const url = queryString ? `/analytics/${conversationId}?${queryString}` : `/analytics/${conversationId}`
  const { data } = await api.post(url)
  return data
}

export default api
