import { useState } from 'react'
import { X, BarChart3, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getAnalyticsParticipants, generateAnalytics, getCachedAnalytics } from '../../api/client'
import type { AnalyticsResult, AnalyticsParticipant } from '../../api/client'
import { format } from 'date-fns'

interface AnalyticsDialogProps {
  conversationId: number
  conversationName: string
  onClose: () => void
}

export default function AnalyticsDialog({
  conversationId,
  conversationName,
  onClose,
}: AnalyticsDialogProps) {
  const [expandedCalendars, setExpandedCalendars] = useState(false)
  const queryClient = useQueryClient()

  // Fetch participants
  const { data: participantsData } = useQuery({
    queryKey: ['analytics-participants', conversationId],
    queryFn: () => getAnalyticsParticipants(conversationId),
  })

  // Fetch cached analytics
  const { data: cachedAnalytics, isLoading: isLoadingCached } = useQuery({
    queryKey: ['analytics-cached', conversationId],
    queryFn: () => getCachedAnalytics(conversationId),
  })

  const participants = participantsData?.participants || []

  // Determine chat type from cached result or participants
  const isGroupChat = cachedAnalytics?.is_group_chat ?? participants.length > 2
  const is1to1Chat = cachedAnalytics ? !cachedAnalytics.is_group_chat : participants.length === 2

  // For 1:1 chats, auto-select both participants
  const person1 = is1to1Chat && participants[0] ? participants[0].name : undefined
  const person2 = is1to1Chat && participants[1] ? participants[1].name : undefined

  // Generate analytics mutation
  const {
    mutate: generate,
    data: generatedAnalytics,
    isPending,
    error,
  } = useMutation({
    mutationFn: () => generateAnalytics(
      conversationId,
      person1,
      person2
    ),
    onSuccess: (data) => {
      // Update the cached query with new data
      queryClient.setQueryData(['analytics-cached', conversationId], data)
    },
  })

  // Use generated analytics if available, otherwise use cached
  const analytics = generatedAnalytics || cachedAnalytics

  return (
    <div className="fixed inset-0 bg-black/50 z-50 overflow-y-auto">
      <div className="min-h-screen py-8 px-4">
        <div className="bg-white rounded-lg max-w-5xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b sticky top-0 bg-white rounded-t-lg z-10">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-whatsapp-teal" />
              <h2 className="text-lg font-semibold">Analytics: {conversationName}</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 hover:bg-gray-100 rounded-full"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Generate Button */}
          <div className="p-4 border-b bg-gray-50">
            <div className="flex flex-wrap items-center gap-4">
              <div className="text-sm text-gray-600">
                {isGroupChat ? (
                  <span>Group chat with {participants.length} participants</span>
                ) : is1to1Chat ? (
                  <span>Comparing {person1} vs {person2}</span>
                ) : (
                  <span>Loading participants...</span>
                )}
              </div>

              <button
                onClick={() => generate()}
                disabled={isPending || participants.length < 2}
                className="flex items-center gap-2 px-4 py-1.5 bg-whatsapp-teal text-white rounded-lg hover:bg-whatsapp-dark transition-colors disabled:opacity-50 ml-auto"
              >
                {isPending ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4" />
                )}
                {isPending ? 'Generating...' : analytics ? 'Regenerate' : 'Generate Analytics'}
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-4">
            {error && (
              <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg">
                Failed to generate analytics. Please try again.
              </div>
            )}

            {(isPending || isLoadingCached) && (
              <div className="flex flex-col items-center justify-center py-16">
                <RefreshCw className="w-12 h-12 text-whatsapp-teal animate-spin mb-4" />
                <p className="text-gray-600">
                  {isPending ? 'Generating analytics...' : 'Loading cached analytics...'}
                </p>
                {isPending && (
                  <p className="text-sm text-gray-400">This may take a moment for large chats</p>
                )}
              </div>
            )}

            {!analytics && !isPending && !isLoadingCached && (
              <div className="flex flex-col items-center justify-center py-16 text-gray-500">
                <BarChart3 className="w-16 h-16 mb-4 opacity-50" />
                <p>Click Generate Analytics to see insights</p>
              </div>
            )}

            {analytics && !isPending && !isLoadingCached && (
              <div className="space-y-6">
                {/* Summary Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard
                    label="Total Messages"
                    value={analytics.summary.total_messages.toLocaleString()}
                  />
                  <StatCard
                    label="Time Span"
                    value={`${analytics.summary.date_range.years} years`}
                  />
                  <StatCard
                    label="Daily Average"
                    value={`${analytics.summary.avg_messages_per_day} msgs`}
                  />
                  <StatCard
                    label="Longest Streak"
                    value={`${analytics.summary.longest_streak_days || 0} days`}
                  />
                </div>

                {/* Top Participants Summary (for group chats only) */}
                {isGroupChat && analytics.summary.top_participants && analytics.summary.top_participants.length > 0 && (
                  <div className="border rounded-lg overflow-hidden">
                    <h3 className="px-4 py-3 bg-gray-50 font-semibold text-gray-800">
                      Top Participants
                    </h3>
                    <div className="p-4">
                      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                        {analytics.summary.top_participants.slice(0, 10).map((p, idx) => (
                          <div
                            key={p.name}
                            className="p-3 rounded-lg border text-center"
                            style={{ borderLeftWidth: '4px', borderLeftColor: p.color }}
                          >
                            <div className="text-xs text-gray-400 mb-1">#{idx + 1}</div>
                            <div className="font-medium text-sm truncate" title={p.name}>
                              {p.name}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {p.messages.toLocaleString()} ({p.percentage}%)
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* 1:1 Chat Participant Stats */}
                {is1to1Chat && analytics.summary.participants.length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {analytics.summary.participants.map((p) => (
                      <div
                        key={p.name}
                        className="p-4 rounded-lg border"
                        style={{ borderLeftWidth: '4px', borderLeftColor: p.color }}
                      >
                        <h4 className="font-semibold" style={{ color: p.color }}>
                          {p.name}
                        </h4>
                        <div className="mt-2 text-sm text-gray-600 space-y-1">
                          <p>{p.messages.toLocaleString()} messages ({p.percentage}%)</p>
                          <p>Most active: {p.most_active_hour}:00</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Charts - Group chats only */}
                {isGroupChat && analytics.charts.top_participants && (
                  <ChartSection title="Participant Overview" src={analytics.charts.top_participants} />
                )}

                {isGroupChat && analytics.charts.participation_over_time && (
                  <ChartSection title="Participation Over Time" src={analytics.charts.participation_over_time} />
                )}

                {/* Charts - Always shown */}
                <ChartSection title="Activity by Time" src={analytics.charts.time_heatmap} />

                <ChartSection title="Message Trend" src={analytics.charts.trend} />

                <ChartSection title="Daily Activity" src={analytics.charts.daily_activity} />

                {/* Charts - 1:1 chats only */}
                {is1to1Chat && analytics.charts.comparison_heatmap && (
                  <ChartSection
                    title="Who Messages More"
                    src={analytics.charts.comparison_heatmap}
                  />
                )}

                {is1to1Chat && analytics.charts.response_time && (
                  <ChartSection title="Response Time" src={analytics.charts.response_time} />
                )}

                {/* Calendar Heatmaps - Collapsible for many years */}
                {analytics.charts.calendar_heatmaps.length > 0 && (
                  <div className="border rounded-lg overflow-hidden">
                    <button
                      onClick={() => setExpandedCalendars(!expandedCalendars)}
                      className="w-full px-4 py-3 bg-gray-50 flex items-center justify-between hover:bg-gray-100 transition-colors"
                    >
                      <h3 className="font-semibold text-gray-800">
                        Calendar Heatmaps ({analytics.charts.calendar_heatmaps.length} years)
                      </h3>
                      {expandedCalendars ? (
                        <ChevronUp className="w-5 h-5 text-gray-500" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-gray-500" />
                      )}
                    </button>
                    {expandedCalendars && (
                      <div className="p-4 space-y-4">
                        {analytics.charts.calendar_heatmaps.map((cal) => (
                          <div key={cal.year}>
                            <h4 className="text-sm font-medium text-gray-600 mb-2">
                              {cal.year === 'all' ? 'All Years' : cal.year}
                            </h4>
                            <img
                              src={cal.url}
                              alt={`Calendar ${cal.year}`}
                              className="w-full rounded border"
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Generated timestamp */}
                <p className="text-xs text-gray-400 text-center">
                  Generated {format(new Date(analytics.generated_at), 'PPpp')}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4 text-center">
      <p className="text-2xl font-bold text-gray-800">{value}</p>
      <p className="text-sm text-gray-500">{label}</p>
    </div>
  )
}

function ChartSection({ title, src }: { title: string; src: string }) {
  return (
    <div className="border rounded-lg overflow-hidden">
      <h3 className="px-4 py-3 bg-gray-50 font-semibold text-gray-800">{title}</h3>
      <div className="p-4">
        <img src={src} alt={title} className="w-full rounded" />
      </div>
    </div>
  )
}
