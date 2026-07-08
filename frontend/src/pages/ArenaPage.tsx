import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { API_BASE, WS_BASE, fetchApi } from '../api'
import AgentStreamView, { buildAgentBubbles, StreamViewMode } from '../components/AgentStreamView'
import TopologyMap from '../components/TopologyMap'
import { submissionReasonLabel } from '../lib/submissionReason'

type LeaderboardEntry = {
  player_id: number
  name?: string
  display_name?: string
  score: number
  flags_captured: number
  flags_lost: number
  sla_ok: boolean
}

type RawLeaderboardEntry = LeaderboardEntry & {
  total_score?: number
  sla_up?: boolean
  model?: string
  display_name?: string
}

type MatchStatus = {
  match_id: string
  name?: string
  scenario_id?: string
  status: string
  elapsed_seconds: number
  remaining_seconds: number
  player_count: number
  leaderboard: Record<string, RawLeaderboardEntry> | RawLeaderboardEntry[]
  recent_events?: Array<{ type: string; data: Record<string, unknown>; timestamp: string }>
  agent_logs?: Record<string, unknown>
  submissions?: SubmissionItem[]
}

type MatchEvent = {
  type: string
  data?: Record<string, unknown>
  timestamp: string
}

type SubmissionItem = {
  attacker_id?: unknown
  victim_id?: unknown
  declared_target_player_id?: unknown
  flag?: unknown
  flag_slot?: unknown
  flag_index?: unknown
  success?: unknown
  reason?: unknown
  timestamp?: unknown
}

type WsMessage = {
  type?: string
  match_id?: string
  [key: string]: unknown
}

const toNumber = (value: unknown): number | undefined => {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return undefined
}

const splitAgentLog = (value: string): string[] => value.split(/\r?\n/)

const normalizePersistedAgentLogs = (raw: unknown): Record<number, string[]> => {
  if (!raw || typeof raw !== 'object') return {}

  const normalized: Record<number, string[]> = {}
  for (const [pidRaw, content] of Object.entries(raw)) {
    const pid = toNumber(pidRaw)
    if (pid == null || typeof content !== 'string') continue
    normalized[pid] = splitAgentLog(content)
  }
  return normalized
}

const eventTime = (timestamp: string): number => {
  const t = new Date(timestamp).getTime()
  return Number.isFinite(t) ? t : 0
}

const isMachineStatusBlob = (body: string) =>
  body.startsWith('{') &&
  (body.includes('"schema_version"') || body.includes('"match_id"')) &&
  (body.includes('"leaderboard_summary"') || body.includes('"score_changes_since_last_query"'))

const isPromptDump = (body: string) =>
  (body.includes('You are Player-') && body.includes('autonomous cybersecurity agent')) ||
  body.includes('[Phase change] The **attack phase** has started')

const shouldShowCleanAgentActivity = (category: string, title: string, body: string) => {
  const normalizedTitle = title.toLowerCase()
  const normalizedBody = body.toLowerCase()
  if (!body.trim()) return false
  if (category === 'log' || category === 'system' || category === 'stderr') return false
  if (normalizedTitle.includes('agent event')) return false
  if (normalizedBody.includes('file lock stale for')) return false
  if (isMachineStatusBlob(body)) return false
  if (isPromptDump(body)) return false
  return true
}

const formatVictimLabel = (value: unknown): string => {
  const victimId = toNumber(value)
  return victimId == null ? 'None' : `P${String(victimId)}`
}

const formatFlagIndexLabel = (value: unknown): string => {
  const flagIndex = toNumber(value)
  return flagIndex == null ? '-' : `#${String(flagIndex)}`
}

const formatFlagEventSuffix = (data: Record<string, unknown>): string => {
  const flagIndex = toNumber(data.flag_index)
  return flagIndex == null ? '' : ` (flag #${String(flagIndex)})`
}

const formatArenaEvent = (event: MatchEvent): string | null => {
  const data = event.data ?? {}
  switch (event.type) {
    case 'STATUS':
      return `Status: ${String(data.status ?? 'unknown')}`
    case 'MATCH_STARTED':
      return `Match started: ${String(data.status ?? 'defense')}`
    case 'PHASE_CHANGE':
      return `Phase: ${String(data.phase ?? 'unknown')}`
    case 'AGENT_READY':
      return `Agent ready: P${String(data.player_id ?? '?')}`
    case 'FLAG_CAPTURED':
      return `Capture: P${String(data.attacker_id ?? data.player_id ?? '?')} -> ${formatVictimLabel(data.victim_id)}${formatFlagEventSuffix(data)}`
    case 'FLAG_SUBMISSION':
      return `Submit: P${String(data.attacker_id ?? '?')} -> ${formatVictimLabel(data.victim_id)}${formatFlagEventSuffix(data)} (${String(data.success ? 'success' : 'fail')})`
    case 'FLAG_SUBMISSION_REJECTED':
      return `Rejected: P${String(data.attacker_id ?? '?')} (${submissionReasonLabel(data.reason)})`
    case 'HEARTBEAT':
      return null
    case 'NETWORK_OPENED':
      return `Network ready: ${String(data.arena_network ?? '')}`
    case 'FLAGS_REFRESHED':
      return `Flags refreshed: ${String(data.player_count ?? '?')} targets`
    case 'AGENT_ACTIVITY':
      if (data.category === 'log' || data.category === 'system') return null
      return `P${String(data.player_id ?? '?')} ${String(data.title ?? data.category ?? 'activity')}: ${String(data.body ?? '').slice(0, 180)}`
    case 'MATCH_FINISHED':
      return 'Match finished'
    case 'MATCH_ERROR':
      return `Match error: ${String(data.error ?? 'unknown')}`
    case 'AGENT_STREAM':
    case 'AGENT_LOGS_COLLECTED':
      return null
    default:
      return `${event.type}: ${JSON.stringify(data)}`
  }
}

const deriveArenaFeed = (events: MatchEvent[], persistedLogs?: unknown) => {
  const readyPlayers = new Set<number>()
  const agentLogs: Record<number, string[]> = {}
  const rawAgentLogs: Record<number, string[]> = {}
  const timeline: string[] = []
  const playersWithStructuredActivity = new Set<number>()
  for (const event of events) {
    if (event.type !== 'AGENT_ACTIVITY') continue
    const pid = toNumber(event.data?.player_id)
    if (pid != null) playersWithStructuredActivity.add(pid)
  }

  for (const event of [...events].sort((a, b) => eventTime(a.timestamp) - eventTime(b.timestamp))) {
    const data = event.data ?? {}
    const formatted = formatArenaEvent(event)
    if (formatted) {
      timeline.push(`[${new Date(event.timestamp).toLocaleTimeString()}] ${formatted}`)
    }

    if (event.type === 'AGENT_READY') {
      const pid = toNumber(data.player_id)
      if (pid != null) readyPlayers.add(pid)
      continue
    }

    if (event.type === 'AGENT_STREAM') {
      const pid = toNumber(data.player_id)
      const content = data.content
      if (pid != null && typeof content === 'string') {
        const rawLines = rawAgentLogs[pid] ?? []
        rawAgentLogs[pid] = [...rawLines, content]
        if (!playersWithStructuredActivity.has(pid)) {
          const lines = agentLogs[pid] ?? []
          agentLogs[pid] = [...lines, content]
        }
      }
      continue
    }

    if (event.type === 'AGENT_ACTIVITY') {
      const pid = toNumber(data.player_id)
      const title = typeof data.title === 'string' ? data.title : 'Activity'
      const category = typeof data.category === 'string' ? data.category : 'activity'
      const phase = typeof data.phase === 'string' ? data.phase : 'match'
      const body = typeof data.body === 'string' ? data.body : ''
      if (pid != null && body) {
        if (shouldShowCleanAgentActivity(category, title, body)) {
          const lines = agentLogs[pid] ?? []
          agentLogs[pid] = [
            ...lines,
            `[${new Date(event.timestamp).toLocaleTimeString()}] ${phase}/${category} · ${title}\n${body}`,
          ]
        }
        const rawPreview =
          typeof data.raw_preview === 'string'
            ? data.raw_preview
            : data.raw && typeof data.raw === 'object' && typeof (data.raw as { preview?: unknown }).preview === 'string'
              ? String((data.raw as { preview?: unknown }).preview)
              : ''
        if (rawPreview) {
          const rawLines = rawAgentLogs[pid] ?? []
          rawAgentLogs[pid] = [
            ...rawLines,
            `[${new Date(event.timestamp).toLocaleTimeString()}] ${phase}/${category} · ${title}\n${rawPreview}`,
          ]
        }
      }
      continue
    }

    if (event.type === 'AGENT_LOGS_COLLECTED') {
      const normalized = normalizePersistedAgentLogs(data.logs)
      for (const [pidRaw, lines] of Object.entries(normalized)) {
        rawAgentLogs[Number(pidRaw)] = lines
      }
    }
  }

  if (Object.keys(agentLogs).length === 0) {
    const normalized = normalizePersistedAgentLogs(persistedLogs)
    for (const [pidRaw, lines] of Object.entries(normalized)) {
      agentLogs[Number(pidRaw)] = lines
    }
  }

  for (const [pidRaw, lines] of Object.entries(normalizePersistedAgentLogs(persistedLogs))) {
    const pid = Number(pidRaw)
    if (!rawAgentLogs[pid]) rawAgentLogs[pid] = lines
  }

  return {
    timeline: timeline.reverse(),
    readyPlayers,
    agentLogs,
    rawAgentLogs,
  }
}

const normalizeLeaderboardRow = (row: RawLeaderboardEntry): LeaderboardEntry => ({
  player_id: row.player_id,
  name: row.name,
  display_name: row.display_name,
  score: row.score ?? row.total_score ?? 0,
  flags_captured: row.flags_captured ?? 0,
  flags_lost: row.flags_lost ?? 0,
  sla_ok: row.sla_ok ?? row.sla_up ?? false,
})

const computePlayerLabel = (row: LeaderboardEntry): string => {
  if (row.display_name) return row.display_name
  if (row.name) return row.name
  return `Player ${row.player_id}`
}

const toLeaderboardArray = (raw: Record<string, RawLeaderboardEntry> | RawLeaderboardEntry[]): LeaderboardEntry[] => {
  const values = Array.isArray(raw) ? raw : Object.values(raw)
  return values.map(normalizeLeaderboardRow).sort((a, b) => b.score - a.score)
}

const ArenaPage: React.FC = () => {
  const { matchId } = useParams<{ matchId: string }>()
  const navigate = useNavigate()
  const [matchInfo, setMatchInfo] = useState<MatchStatus | null>(null)
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([])
  const [events, setEvents] = useState<string[]>([])
  const [agentLogs, setAgentLogs] = useState<Record<number, string[]>>({})
  const [rawAgentLogs, setRawAgentLogs] = useState<Record<number, string[]>>({})
  const [submissions, setSubmissions] = useState<SubmissionItem[]>([])
  const [selectedPlayerLog, setSelectedPlayerLog] = useState<number | null>(null)
  const [streamViewMode, setStreamViewMode] = useState<StreamViewMode>('cleaned')
  const [matchEnded, setMatchEnded] = useState(false)
  const [readyPlayers, setReadyPlayers] = useState<Set<number>>(new Set())
  const [wsConnected, setWsConnected] = useState(false)
  const socketRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<number | null>(null)
  const matchEndedRef = useRef(false)
  const matchNotFoundRef = useRef(false)
  const [statusFetchError, setStatusFetchError] = useState<string | null>(null)

  useEffect(() => {
    matchEndedRef.current = matchEnded || matchInfo?.status === 'finished'
  }, [matchEnded, matchInfo?.status])

  const fetchStatus = useCallback(() => {
    if (!matchId || matchNotFoundRef.current) return

    const loadMatch = async () => {
      try {
        const r = await fetchApi(`${API_BASE}/api/matches/${matchId}`)
        if (r.status === 404) {
          matchNotFoundRef.current = true
          setStatusFetchError(null)
          return
        }
        if (!r.ok) {
          let msg = `Could not load match (${r.status})`
          try {
            const body = (await r.json()) as { detail?: unknown }
            if (typeof body.detail === 'string') {
              msg = body.detail
            } else if (Array.isArray(body.detail)) {
              const first = body.detail[0] as { msg?: unknown } | undefined
              if (first && typeof first.msg === 'string') {
                msg = first.msg
              }
            }
          } catch {
            /* keep default msg */
          }
          setStatusFetchError(msg)
          return
        }
        setStatusFetchError(null)
        const d = (await r.json()) as MatchStatus
        if (typeof d.status !== 'string' || typeof d.match_id !== 'string') {
          setStatusFetchError('Unexpected response from referee API')
          return
        }
        setMatchInfo(d)
        if (d.leaderboard) setLeaderboard(toLeaderboardArray(d.leaderboard))
        if (d.status === 'finished') setMatchEnded(true)
      } catch {
        setStatusFetchError('Network error while loading match status')
      }
    }
    void loadMatch()

    fetchApi(`${API_BASE}/api/matches/${matchId}/submissions`)
      .then((r) => {
        if (r.status === 404) return null
        return r.json()
      })
      .then((d: { submissions?: SubmissionItem[] } | null) => {
        if (!d) return
        setSubmissions(Array.isArray(d.submissions) ? d.submissions : [])
      })
      .catch(() => {})
  }, [matchId])

  const fetchFeed = useCallback(() => {
    if (!matchId || matchNotFoundRef.current) return
    fetchApi(`${API_BASE}/api/matches/${matchId}/events?limit=10000`)
      .then((r) => {
        if (r.status === 404) return null
        return r.json()
      })
      .then((resp: { events?: MatchEvent[] } | MatchEvent[] | null) => {
        if (!resp) return
        const raw = Array.isArray(resp) ? resp : resp.events ?? []
        const {
          timeline,
          readyPlayers: nextReadyPlayers,
          agentLogs: nextAgentLogs,
          rawAgentLogs: nextRawAgentLogs,
        } = deriveArenaFeed(raw, matchInfo?.agent_logs)
        setEvents(timeline)
        setReadyPlayers(nextReadyPlayers)
        setAgentLogs(nextAgentLogs)
        setRawAgentLogs(nextRawAgentLogs)
        setSelectedPlayerLog((prevSelected) => {
          if (prevSelected != null && nextAgentLogs[prevSelected]) return prevSelected
          const firstPlayer = Object.keys(nextAgentLogs)
            .map((pid) => Number(pid))
            .filter((pid) => Number.isFinite(pid))
            .sort((a, b) => a - b)[0]
          return firstPlayer ?? null
        })
      })
      .catch(() => {})
  }, [matchId, matchInfo?.agent_logs])

  useEffect(() => {
    fetchStatus()
    fetchFeed()
    const interval = setInterval(() => {
      if (matchNotFoundRef.current) return
      fetchStatus()
      fetchFeed()
    }, 5000)
    return () => clearInterval(interval)
  }, [fetchFeed, fetchStatus])

  useEffect(() => {
    let cancelled = false
    let reconnectAttempt = 0

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current != null) {
        window.clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
    }

    const scheduleReconnect = () => {
      if (cancelled || matchEndedRef.current || matchNotFoundRef.current) return
      clearReconnectTimer()
      const delay = Math.min(5000, 1000 * 2 ** reconnectAttempt)
      reconnectAttempt += 1
      reconnectTimerRef.current = window.setTimeout(() => {
        reconnectTimerRef.current = null
        connect()
      }, delay)
    }

    const connect = () => {
      if (cancelled) return

      const socket = new WebSocket(`${WS_BASE}/ws/`)
      socketRef.current = socket

      socket.onopen = () => {
        if (cancelled) return
        reconnectAttempt = 0
        setWsConnected(true)
        clearReconnectTimer()
        if (matchId) {
          socket.send(JSON.stringify({ type: 'subscribe', match_id: matchId }))
        }
        fetchStatus()
        fetchFeed()
      }

      socket.onmessage = (ev: MessageEvent) => {
        try {
          const data = JSON.parse(ev.data as string) as WsMessage
          const eventType = data?.type
          if (!eventType) return
          if (typeof data.match_id === 'string' && matchId && data.match_id !== matchId) return
          switch (eventType) {
            case 'subscribed': {
              setWsConnected(true)
              break
            }
            case 'STATUS': {
              fetchStatus()
              fetchFeed()
              break
            }
            case 'AGENT_READY': {
              fetchFeed()
              break
            }
            case 'FLAG_CAPTURED': {
              fetchStatus()
              fetchFeed()
              break
            }
            case 'FLAG_SUBMISSION': {
              fetchStatus()
              fetchFeed()
              break
            }
            case 'FLAG_SUBMISSION_REJECTED': {
              fetchStatus()
              fetchFeed()
              break
            }
            case 'PHASE_CHANGE': {
              fetchStatus()
              fetchFeed()
              break
            }
            case 'AGENT_STREAM': {
              fetchFeed()
              break
            }
            case 'AGENT_ACTIVITY': {
              fetchFeed()
              break
            }
            case 'AGENT_LOGS_COLLECTED': {
              fetchFeed()
              break
            }
            case 'MATCH_FINISHED': {
              setMatchEnded(true)
              matchEndedRef.current = true
              setWsConnected(true)
              clearReconnectTimer()
              setMatchInfo((prev) => {
                if (!prev) return prev
                return {
                  ...prev,
                  status: 'finished',
                  remaining_seconds: 0,
                }
              })
              fetchStatus()
              fetchFeed()
              try {
                socket.close()
              } catch (_closeError) {
                void _closeError
              }
              break
            }
          }
        } catch (_parseError) {
          void _parseError
        }
      }

      socket.onerror = () => {
        setWsConnected(false)
      }

      socket.onclose = () => {
        const shouldReconnect = !cancelled && !matchEndedRef.current
        setWsConnected(!shouldReconnect)
        if (socketRef.current === socket) {
          socketRef.current = null
        }
        if (shouldReconnect) scheduleReconnect()
      }
    }

    connect()

    return () => {
      cancelled = true
      setWsConnected(false)
      clearReconnectTimer()
      const socket = socketRef.current
      socketRef.current = null
      if (socket) {
        try { socket.close() } catch (_e) { void _e }
      }
    }
  }, [fetchFeed, fetchStatus, matchId])

  const endMatch = () => {
    if (!matchId) return
    fetchApi(`${API_BASE}/api/matches/${matchId}/end`, { method: 'POST' }).catch(() => {})
  }

  const closeMatchEndedModal = () => {
    if (!matchId) return
    navigate(`/history?matchId=${encodeURIComponent(matchId)}`)
  }

  const phase = matchInfo?.status ?? 'initializing'
  const remaining = matchInfo?.remaining_seconds ?? 0
  const mins = Math.floor(remaining / 60).toString().padStart(2, '0')
  const secs = Math.floor(remaining % 60).toString().padStart(2, '0')
  const totalPlayers = matchInfo?.player_count ?? 0
  const readyCount = readyPlayers.size
  const isInitPhase =
    phase === 'initializing' ||
    phase === 'creating_containers' ||
    phase === 'initializing_agents'
  const playerLabelById = new Map(leaderboard.map((row) => [row.player_id, computePlayerLabel(row)]))
  const recentSubmissions = submissions
    .slice()
    .sort((a, b) => {
      const aTime = typeof a.timestamp === 'string' ? eventTime(a.timestamp) : 0
      const bTime = typeof b.timestamp === 'string' ? eventTime(b.timestamp) : 0
      return bTime - aTime
    })
  const recentSubmissionsViewportClass = 'h-[15rem] overflow-x-auto overflow-y-auto overscroll-contain'
  const selectedPlayerBubbles = selectedPlayerLog !== null && agentLogs[selectedPlayerLog]
    ? buildAgentBubbles(
        streamViewMode === 'raw'
          ? rawAgentLogs[selectedPlayerLog] ?? agentLogs[selectedPlayerLog]
          : agentLogs[selectedPlayerLog],
        streamViewMode,
      )
    : []
  const matchTitle = matchInfo?.name || matchId

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">{matchTitle}</h1>
            {matchTitle !== matchId && (
              <div className="mt-1 text-xs font-mono text-slate-400">{matchId}</div>
            )}
          </div>
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${wsConnected ? 'bg-cyan-700 text-cyan-100' : 'bg-amber-700 text-amber-100'}`}>
              WS {wsConnected ? 'connected' : 'reconnecting'}
            </span>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${
              phase === 'defense' ? 'bg-emerald-600' :
              phase === 'attack' ? 'bg-red-600' :
              phase === 'finished' ? 'bg-slate-500' :
              phase === 'error' ? 'bg-red-900' :
              phase === 'aborted' ? 'bg-amber-900' :
              'bg-slate-700'
            }`}>
              {phase === 'defense' ? 'Defense' :
                phase === 'attack' ? 'Attack' :
                phase === 'finished' ? 'Finished' :
                phase === 'error' ? 'Error' :
                phase === 'aborted' ? 'Aborted' :
                phase === 'creating_containers' ? 'Containers' :
                phase === 'initializing_agents' ? 'Agents' :
                phase === 'initializing' ? 'Starting' :
                'Initializing'}
            </span>
            <button className="px-4 py-2 rounded-md bg-red-700 hover:bg-red-600 text-white" onClick={endMatch}>
              End match
            </button>
          </div>
        </header>

        {statusFetchError && (
          <div className="bg-red-950 border border-red-800 rounded-md p-4 text-red-100 text-sm">
            <span className="font-semibold">Cannot refresh match from referee: </span>
            {statusFetchError}
            <span className="block mt-2 text-red-200/90">
              If you see this while the match page loads, set the same referee API key in local storage
              (<code className="text-xs bg-red-900/80 px-1 rounded">REFEREE_API_KEY</code>) that you used to start the match.
            </span>
          </div>
        )}

        {isInitPhase && (
          <div className="bg-slate-800 border border-slate-700 rounded-md p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-slate-300">
                {phase === 'creating_containers'
                  ? 'Creating containers…'
                  : phase === 'initializing_agents'
                    ? 'Initializing agents…'
                    : 'Checking Docker and preparing the match…'}
              </span>
              <span className="text-sm font-mono text-slate-400">
                {readyCount} / {totalPlayers || '?'} ready
              </span>
            </div>
            <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
              <div
                className="bg-cyan-500 h-2 rounded-full transition-all duration-500"
                style={{ width: totalPlayers > 0 ? `${(readyCount / totalPlayers) * 100}%` : '0%' }}
              />
            </div>
            {readyPlayers.size > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {[...readyPlayers].map((pid) => (
                  <span key={pid} className="px-2 py-0.5 rounded-full bg-emerald-800 text-emerald-300 text-xs font-mono">
                    P{pid} ✓
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,2fr)_minmax(360px,1fr)] gap-4 items-stretch">
          <div className="flex flex-col gap-4 xl:h-[calc(100vh-8rem)]">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 flex-shrink-0">
              <div className="bg-slate-800 border border-slate-700 rounded-md p-6 flex flex-col items-center justify-center">
                <div className="text-xs text-slate-400 mb-1">Time remaining</div>
                <div className="text-7xl font-mono text-cyan-400">{mins}:{secs}</div>
              </div>

              <div className="lg:col-span-2 bg-slate-800 border border-slate-700 rounded-md p-4">
                <h3 className="text-sm font-semibold text-slate-400 mb-3">Leaderboard</h3>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left border-b border-slate-700 text-slate-400">
                      <th className="pb-2">#</th>
                      <th className="pb-2">Player</th>
                      <th className="pb-2 font-mono">Score</th>
                      <th className="pb-2">Captured</th>
                      <th className="pb-2">Lost</th>
                      <th className="pb-2">SLA</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboard.map((row, i) => (
                      <tr key={row.player_id} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                        <td className="py-2 pr-3 text-slate-400">{i + 1}</td>
                        <td className="py-2 pr-3">{computePlayerLabel(row)}</td>
                        <td className="py-2 pr-3 font-mono text-cyan-400">{row.score ?? 0}</td>
                        <td className="py-2 pr-3 text-emerald-400">{row.flags_captured ?? 0}</td>
                        <td className="py-2 pr-3 text-red-400">{row.flags_lost ?? 0}</td>
                        <td className="py-2">{row.sla_ok ? '✅' : '❌'}</td>
                      </tr>
                    ))}
                    {leaderboard.length === 0 && (
                      <tr>
                        <td colSpan={6} className="py-4 text-center text-slate-500">Waiting for players…</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="bg-slate-800 border border-slate-700 rounded-md p-4 flex-shrink-0">
              <div className="mb-3 flex items-center justify-between gap-4">
                <h3 className="text-sm font-semibold text-slate-400">Recent submissions</h3>
                <span className="text-xs text-slate-500">Only the first successful submit per player per flag scores</span>
              </div>
              <div className={recentSubmissionsViewportClass}>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left border-b border-slate-700 text-slate-400">
                      <th className="pb-2">Time</th>
                      <th className="pb-2">Submitter</th>
                      <th className="pb-2">Target</th>
                      <th className="pb-2">Flag</th>
                      <th className="pb-2">Result</th>
                      <th className="pb-2">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentSubmissions.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-4 text-center text-slate-500">No submissions yet</td>
                      </tr>
                    ) : (
                      recentSubmissions.map((submission, index) => {
                        const attackerId = toNumber(submission.attacker_id)
                        const success = Boolean(submission.success)
                        const flagIndexLabel = formatFlagIndexLabel(submission.flag_index)
                        const timestamp = typeof submission.timestamp === 'string'
                          ? new Date(submission.timestamp).toLocaleTimeString()
                          : '-'

                        return (
                          <tr key={`${String(submission.timestamp ?? index)}-${index}`} className="border-b border-slate-700/50 hover:bg-slate-700/30 transition-colors">
                            <td className="py-2 pr-3 text-slate-300">{timestamp}</td>
                            <td className="py-2 pr-3">P{attackerId ?? '?'}</td>
                            <td className="py-2 pr-3">{formatVictimLabel(submission.victim_id)}</td>
                            <td className="py-2 pr-3">
                              <div className="font-mono text-cyan-300">{flagIndexLabel}</div>
                              {typeof submission.flag_slot === 'string' && submission.flag_slot !== '' && (
                                <div className="text-xs text-slate-500">{submission.flag_slot}</div>
                              )}
                            </td>
                            <td className={`py-2 pr-3 ${success ? 'text-emerald-400' : 'text-red-400'}`}>{success ? 'Success' : 'Fail'}</td>
                            <td className="py-2 pr-3 text-slate-300">{submissionReasonLabel(submission.reason)}</td>
                          </tr>
                        )
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 flex-1 min-h-0">
              <div className="bg-slate-800 border border-slate-700 rounded-md p-4 flex flex-col h-full min-h-0">
                <h3 className="text-sm font-semibold text-slate-400 mb-3 flex-shrink-0">Network topology</h3>
                <div className="flex-grow relative min-h-0">
                  <TopologyMap playerCount={totalPlayers} phase={phase} />
                </div>
              </div>

              <div className="bg-slate-800 border border-slate-700 rounded-md p-4 flex flex-col h-full min-h-0">
                <h3 className="text-sm font-semibold text-slate-400 mb-3 flex-shrink-0">Event log</h3>
                <div className="flex-grow min-h-0 overflow-auto bg-slate-900/60 rounded-md p-3 font-mono text-xs space-y-1">
                  {events.length === 0 && <div className="text-slate-500">No events yet</div>}
                  {events.map((e, idx) => (
                    <div key={idx} className="text-slate-300">{e}</div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="bg-slate-800 border border-slate-700 rounded-md p-4 flex flex-col min-h-[520px] xl:sticky xl:top-4 xl:h-[calc(100vh-8rem)] h-full min-h-0">
            <div className="flex items-center justify-between mb-3 flex-shrink-0">
              <h3 className="text-sm font-semibold text-slate-400">Agent live stream</h3>
              <div className="flex gap-2 flex-wrap items-center justify-end">
                {Object.keys(agentLogs).length === 0 && (
                  <span className="text-xs text-slate-500">No data</span>
                )}
                {Object.keys(agentLogs).map((pidStr) => {
                  const pid = parseInt(pidStr, 10)
                  return (
                    <button
                      key={pid}
                      onClick={() => setSelectedPlayerLog(pid)}
                      className={`px-3 py-1 text-xs rounded-md font-mono transition-colors ${
                        selectedPlayerLog === pid
                          ? 'bg-cyan-600 text-white'
                          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                      }`}
                    >
                      {playerLabelById.get(pid) ?? `Player ${pid}`}
                    </button>
                  )
                })}
              </div>
            </div>
            <AgentStreamView
              mode={streamViewMode}
              onModeChange={setStreamViewMode}
              bubbles={selectedPlayerBubbles}
              emptyText="Waiting for agent output..."
            />
          </div>
        </div>

        {matchEnded && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
            <div className="bg-slate-900 border border-slate-600 rounded-md p-8 max-w-lg w-full text-center">
              <h2 className="text-2xl font-bold mb-4 text-cyan-400">Match finished</h2>
              <h3 className="text-lg mb-4">Final leaderboard</h3>
              <table className="w-full text-sm mb-6">
                <thead>
                  <tr className="border-b border-slate-700 text-slate-400">
                    <th>#</th><th>Player</th><th>Score</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((row, i) => (
                    <tr key={row.player_id} className="border-b border-slate-700/50">
                      <td className="py-1">{i + 1}</td>
                      <td className="py-1">{computePlayerLabel(row)}</td>
                      <td className="py-1 font-mono text-cyan-400">{row.score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <button className="px-6 py-2 bg-cyan-600 rounded-md" onClick={closeMatchEndedModal}>
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ArenaPage
