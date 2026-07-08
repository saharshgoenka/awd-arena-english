import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, CheckCircle2, ChevronDown, Clock3, Key, ListChecks, Play, Shield, Swords, Users } from 'lucide-react'
import { API_BASE, fetchApi } from '../api'

type MatchMode = 'hvh' | 'defense_only' | 'attack_only'

type ModelOption = {
  id: string
  label: string
  slug: string
  inputPrice: number
  outputPrice: number
  matchCost: number
  sweepCost: number
}

type ScenarioOption = {
  id: string
  label: string
  targetImage: string
  oracleImage?: string
}

type PlayerRow = {
  id: number
  modelId: string
}

type DefaultsResponse = {
  openrouter?: {
    configured?: boolean
    apiKey?: string
    baseUrl?: string
    provider?: string
  }
}

const OPENROUTER_KEY_STORAGE = 'OPENROUTER_API_KEY'

const MODEL_OPTIONS: ModelOption[] = [
  {
    id: 'deepseek_v4_flash',
    label: 'DeepSeek V4 Flash',
    slug: 'deepseek/deepseek-v4-flash',
    inputPrice: 0.435,
    outputPrice: 0.87,
    matchCost: 0.96,
    sweepCost: 8.61,
  },
  {
    id: 'deepseek_v4_pro',
    label: 'DeepSeek V4 Pro',
    slug: 'deepseek/deepseek-v4-pro',
    inputPrice: 0.435,
    outputPrice: 0.87,
    matchCost: 0.96,
    sweepCost: 8.61,
  },
  {
    id: 'qwen_3_7_plus',
    label: 'Qwen 3.7 Plus',
    slug: 'qwen/qwen3.7-plus',
    inputPrice: 0.32,
    outputPrice: 1.28,
    matchCost: 0.77,
    sweepCost: 6.91,
  },
  {
    id: 'phi_4',
    label: 'Phi 4',
    slug: 'microsoft/phi-4',
    inputPrice: 0.065,
    outputPrice: 0.14,
    matchCost: 0.14,
    sweepCost: 1.3,
  },
  {
    id: 'minimax_m3',
    label: 'Minimax M3',
    slug: 'minimax/minimax-m3',
    inputPrice: 0.3,
    outputPrice: 1.2,
    matchCost: 0.72,
    sweepCost: 6.48,
  },
  {
    id: 'nemotron_3_super',
    label: 'Nvidia Nemotron 3 Super',
    slug: 'nvidia/nemotron-3-super-120b-a12b',
    inputPrice: 0.09,
    outputPrice: 0.45,
    matchCost: 0.23,
    sweepCost: 2.03,
  },
  {
    id: 'gemma_4_31b',
    label: 'Gemma 4 31B',
    slug: 'google/gemma-4-31b-it',
    inputPrice: 0.12,
    outputPrice: 0.35,
    matchCost: 0.28,
    sweepCost: 2.48,
  },
  {
    id: 'llama_3_3_70b',
    label: 'Llama 3.3 70B',
    slug: 'meta-llama/llama-3.3-70b-instruct',
    inputPrice: 0.1,
    outputPrice: 0.32,
    matchCost: 0.23,
    sweepCost: 2.09,
  },
  {
    id: 'qwen3_coder_plus',
    label: 'Qwen3 Coder Plus',
    slug: 'qwen/qwen3-coder-plus',
    inputPrice: 0.65,
    outputPrice: 3.25,
    matchCost: 1.63,
    sweepCost: 14.63,
  },
]

const SCENARIO_OPTIONS: ScenarioOption[] = [
  { id: 'S1', label: 'S1 - NexusBI Flask', targetImage: 'nexusbi-s1:latest', oracleImage: 'openclaw/oracle-s1:v1' },
  { id: 'S2', label: 'S2 - PeopleOps', targetImage: 'peopleops-s2:latest', oracleImage: 'openclaw/oracle-s2:v1' },
  { id: 'S3', label: 'S3 - TaskFlow', targetImage: 'taskflow-s3:latest', oracleImage: 'openclaw/oracle-s3:v1' },
  { id: 'S4', label: 'S4 - ShopAdmin', targetImage: 'shopadmin-s4:latest', oracleImage: 'openclaw/oracle-s4:v1' },
  { id: 'S5', label: 'S5 - FinLedger', targetImage: 'finledger-s5:latest', oracleImage: 'openclaw/oracle-s5:v1' },
  { id: 'S6', label: 'S6 - ContentHub', targetImage: 'contenthub-s6:latest', oracleImage: 'openclaw/oracle-s6:v1' },
  { id: 'S7', label: 'S7 - FleetView', targetImage: 'fleetview-s7:latest', oracleImage: 'openclaw/oracle-s7:v1' },
  { id: 'S8', label: 'S8 - GridPulse', targetImage: 'gridpulse-s8:latest', oracleImage: 'openclaw/oracle-s8:v1' },
  { id: 'S9', label: 'S9 - VaultGate', targetImage: 'vaultgate-s9:latest', oracleImage: 'openclaw/oracle-s9:v1' },
]

const modeCopy: Record<MatchMode, { label: string; detail: string; icon: React.ReactNode }> = {
  hvh: {
    label: 'Attack + defense',
    detail: 'Each selected model gets a target, patches first, then attacks the others.',
    icon: <Swords className="h-4 w-4" />,
  },
  defense_only: {
    label: 'Defense only',
    detail: 'One model patches its target; an oracle probes it after the defense window.',
    icon: <Shield className="h-4 w-4" />,
  },
  attack_only: {
    label: 'Attack only',
    detail: 'One model attacks an unpatched victim target. The victim is added automatically.',
    icon: <Swords className="h-4 w-4" />,
  },
}

const makePlayers = (count: number, existing: PlayerRow[] = []): PlayerRow[] =>
  Array.from({ length: count }, (_, index) => ({
    id: index + 1,
    modelId: existing[index]?.modelId ?? MODEL_OPTIONS[index % MODEL_OPTIONS.length].id,
  }))

const formatCurrency = (value: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(value)

const getModel = (id: string) => MODEL_OPTIONS.find((model) => model.id === id) ?? MODEL_OPTIONS[0]

const isKeyError = (message: string) => {
  const lower = message.toLowerCase()
  return lower.includes('401') || lower.includes('402') || lower.includes('403') || lower.includes('429') || lower.includes('limit') || lower.includes('billing') || lower.includes('key')
}

const ConfigPage: React.FC = () => {
  const navigate = useNavigate()
  const [matchMode, setMatchMode] = useState<MatchMode>('hvh')
  const [scenarioId, setScenarioId] = useState('S1')
  const [playerCount, setPlayerCount] = useState(2)
  const [players, setPlayers] = useState<PlayerRow[]>(() => makePlayers(2))
  const [defenseMinutes, setDefenseMinutes] = useState(10)
  const [attackMinutes, setAttackMinutes] = useState(10)
  const [matchName, setMatchName] = useState('DeepSeek V4 Flash - S1')
  const [matchNameEdited, setMatchNameEdited] = useState(false)
  const [openRouterKey, setOpenRouterKey] = useState(() => localStorage.getItem(OPENROUTER_KEY_STORAGE) || '')
  const [provider, setProvider] = useState('openai-completions')
  const [baseUrl, setBaseUrl] = useState('https://openrouter.ai/api/v1')
  const [isStarting, setIsStarting] = useState(false)
  const [isStartingSweep, setIsStartingSweep] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)
  const [sweepMessage, setSweepMessage] = useState<string | null>(null)

  const selectedScenario = SCENARIO_OPTIONS.find((scenario) => scenario.id === scenarioId) ?? SCENARIO_OPTIONS[0]
  const visiblePlayerCount = matchMode === 'hvh' ? playerCount : 1
  const selectedModels = players.slice(0, visiblePlayerCount).map((player) => getModel(player.modelId))
  const firstModelLabel = selectedModels[0]?.label ?? 'Model'
  const expectedMatchCost = selectedModels.reduce((total, model) => total + model.matchCost, 0)
  const expectedSweepCost = selectedModels.reduce((total, model) => total + model.sweepCost, 0)
  const staggeredSweepCost = (selectedModels[0]?.sweepCost ?? 0) * 2
  const effectiveAttackMinutes = matchMode === 'defense_only' ? Math.max(1, attackMinutes) : attackMinutes
  const totalMinutes = defenseMinutes + effectiveAttackMinutes

  const hasKey = openRouterKey.trim().length > 0
  const canStart = hasKey && !isStarting && !isStartingSweep && selectedModels.every(Boolean) && totalMinutes > 0

  useEffect(() => {
    const updateKey = () => setOpenRouterKey(localStorage.getItem(OPENROUTER_KEY_STORAGE) || '')
    window.addEventListener('openclaw:openrouter-key-updated', updateKey)
    return () => window.removeEventListener('openclaw:openrouter-key-updated', updateKey)
  }, [])

  useEffect(() => {
    fetchApi(`${API_BASE}/api/defaults`)
      .then((response) => response.json())
      .then((data: DefaultsResponse) => {
        const openrouter = data.openrouter
        if (openrouter?.baseUrl) setBaseUrl(openrouter.baseUrl)
        if (openrouter?.provider) setProvider(openrouter.provider)
        if (!localStorage.getItem(OPENROUTER_KEY_STORAGE) && openrouter?.apiKey) {
          localStorage.setItem(OPENROUTER_KEY_STORAGE, openrouter.apiKey)
          setOpenRouterKey(openrouter.apiKey)
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    setPlayers((current) => makePlayers(visiblePlayerCount, current))
  }, [visiblePlayerCount])

  useEffect(() => {
    if (!matchNameEdited) {
      setMatchName(`${firstModelLabel} - ${scenarioId}`)
    }
  }, [firstModelLabel, matchNameEdited, scenarioId])

  const rows = useMemo(() => players.slice(0, visiblePlayerCount), [players, visiblePlayerCount])

  const openKeyDrawer = () => {
    window.dispatchEvent(new Event('openclaw:open-api-key-drawer'))
  }

  const updatePlayerModel = (playerId: number, modelId: string) => {
    setPlayers((current) => current.map((player) => (player.id === playerId ? { ...player, modelId } : player)))
  }

  const setMode = (mode: MatchMode) => {
    setMatchMode(mode)
    if (mode !== 'hvh') {
      setPlayerCount(1)
    } else {
      setPlayerCount((count) => Math.max(2, count))
    }
  }

  const buildMatchPayload = (mode: MatchMode, scenario: ScenarioOption, name: string, playerModel = selectedModels[0]) => {
    const modeAttackMinutes = mode === 'defense_only' ? Math.max(1, attackMinutes) : attackMinutes
    const modeDefenseMinutes = mode === 'attack_only' ? 0 : defenseMinutes
    const activePlayers = (mode === 'hvh' ? rows : rows.slice(0, 1)).map((player, index) => {
      const model = mode === 'hvh' ? getModel(player.modelId) : playerModel
      return {
        id: index + 1,
        name: model.label,
        model: model.slug,
        apiKey: null,
        gatewayPort: 18789 + index,
        backend_type: 'openclaw',
        backend_config: {
          image: null,
          profile_name: null,
          extra_env: {},
        },
        is_agent: true,
      }
    })

    const payloadPlayers =
      mode === 'attack_only'
        ? [
            activePlayers[0],
            {
              id: 2,
              name: 'Unpatched victim',
              model: null,
              apiKey: null,
              gatewayPort: 18790,
              backend_type: 'openclaw',
              backend_config: {
                image: null,
                profile_name: null,
                extra_env: {},
              },
              is_agent: false,
            },
          ]
        : activePlayers

    return {
      match: {
        name,
        duration: (modeDefenseMinutes + modeAttackMinutes) * 60,
        phases: {
          defense: modeDefenseMinutes * 60,
          attack: modeAttackMinutes * 60,
        },
      },
      loop: {
        enabled: false,
        repeatCount: 1,
      },
      llm: {
        provider,
        baseUrl,
        apiKey: openRouterKey.trim(),
        proxy: '',
        model: playerModel.slug,
      },
      players: payloadPlayers,
      scoring: {
        attackSuccess: 100,
        defenseFailure: -50,
        slaViolation: -10,
      },
      flags: {
        refreshInterval: 60,
        format: 'FLAG{{{hash}}}',
      },
      target_image: scenario.targetImage,
      agent_image: 'openclaw/awd-openclaw-agent:latest',
      mode: mode === 'hvh' ? 'head_to_head' : mode,
      scenario_id: scenario.id,
      oracle_image: scenario.oracleImage ?? null,
      token_budget_input: 10000000,
      token_budget_output: 250000,
      decoding_temp: 0.2,
    }
  }

  const startMatch = async () => {
    if (!canStart) {
      if (!hasKey) openKeyDrawer()
      return
    }

    setIsStarting(true)
    setStartError(null)
    const payload = buildMatchPayload(matchMode, selectedScenario, matchName.trim() || `${scenarioId} - ${modeCopy[matchMode].label}`)

    try {
      const response = await fetchApi(`${API_BASE}/api/matches/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const body = await response.text()
        throw new Error(`HTTP ${response.status}${body ? `: ${body}` : ''}`)
      }

      const data: { match_id?: string; id?: string } = await response.json()
      const id = data.match_id ?? data.id
      if (!id) throw new Error('No match ID returned')

      navigate(`/arena/${id}`)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to create match'
      setStartError(message)
      setIsStarting(false)
      if (isKeyError(message)) openKeyDrawer()
    }
  }

  const startStaggeredSweep = async () => {
    if (!hasKey) {
      openKeyDrawer()
      return
    }

    const model = selectedModels[0]
    setIsStartingSweep(true)
    setStartError(null)
    setSweepMessage(null)

    const matches = SCENARIO_OPTIONS.flatMap((scenario) => [
      buildMatchPayload('defense_only', scenario, `${model.label} - ${scenario.id} Defense`, model),
      buildMatchPayload('attack_only', scenario, `${model.label} - ${scenario.id} Attack`, model),
    ])

    try {
      const response = await fetchApi(`${API_BASE}/api/staggered-runs/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: `${model.label} all samples`,
          matches,
          continueOnError: true,
        }),
      })

      if (!response.ok) {
        const body = await response.text()
        throw new Error(`HTTP ${response.status}${body ? `: ${body}` : ''}`)
      }

      const data: { run_id?: string; current_match_id?: string; total_matches?: number } = await response.json()
      setSweepMessage(`Queued ${data.total_matches ?? matches.length} staggered matches. First match: ${data.current_match_id ?? 'starting'}.`)
      if (data.current_match_id) navigate(`/arena/${data.current_match_id}`)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to start staggered sweep'
      setStartError(message)
      if (isKeyError(message)) openKeyDrawer()
    } finally {
      setIsStartingSweep(false)
    }
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-md border border-zinc-800 bg-zinc-900">
        <div className="grid gap-0 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="space-y-5 p-5 sm:p-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300">Match setup</p>
                <h1 className="mt-2 text-2xl font-semibold text-white sm:text-3xl">Build the run without touching raw config.</h1>
              </div>
              <button
                type="button"
                onClick={openKeyDrawer}
                className={`inline-flex h-10 items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-cyan-400 ${hasKey ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-100' : 'border-amber-400/50 bg-amber-400/10 text-amber-100'}`}
              >
                <Key className="h-4 w-4" />
                {hasKey ? 'OpenRouter key saved' : 'Add OpenRouter key'}
              </button>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <label className="block space-y-2">
                <span className="text-sm font-medium text-zinc-300">Scenario</span>
                <div className="relative">
                  <select
                    value={scenarioId}
                    onChange={(event) => setScenarioId(event.target.value)}
                    className="h-11 w-full appearance-none rounded-md border border-zinc-700 bg-zinc-950 px-3 pr-9 text-sm text-white outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
                  >
                    {SCENARIO_OPTIONS.map((scenario) => (
                      <option key={scenario.id} value={scenario.id}>
                        {scenario.label}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-zinc-500" />
                </div>
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-zinc-300">Match name</span>
                <input
                  value={matchName}
                  onChange={(event) => {
                    setMatchNameEdited(true)
                    setMatchName(event.target.value)
                  }}
                  className="h-11 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-white outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-medium text-zinc-300">Players</span>
                <div className="relative">
                  <select
                    value={visiblePlayerCount}
                    disabled={matchMode !== 'hvh'}
                    onChange={(event) => setPlayerCount(Number(event.target.value))}
                    className="h-11 w-full appearance-none rounded-md border border-zinc-700 bg-zinc-950 px-3 pr-9 text-sm text-white outline-none transition disabled:cursor-not-allowed disabled:opacity-50 focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
                  >
                    {[1, 2, 3, 4, 5, 6, 8, 10].map((count) => (
                      <option key={count} value={count}>
                        {count} {count === 1 ? 'player' : 'players'}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-zinc-500" />
                </div>
              </label>
            </div>
          </div>

          <div className="border-t border-zinc-800 bg-zinc-950 p-5 lg:border-l lg:border-t-0">
            <div className="grid h-full content-center gap-3">
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <span className="text-sm text-zinc-400">Expected one match</span>
                <span className="font-mono text-lg text-white">{formatCurrency(expectedMatchCost)}</span>
              </div>
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
                <span className="text-sm text-zinc-400">All 9 samples</span>
                <span className="font-mono text-lg text-white">{formatCurrency(expectedSweepCost)}</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-zinc-500">
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                Uses the 2M input / 100k output planning estimate per model row.
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[0.75fr_1.25fr]">
        <div className="rounded-md border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="flex items-center gap-2 text-base font-semibold text-white">
            <Clock3 className="h-4 w-4 text-cyan-300" />
            Phase timing
          </h2>
          <div className="mt-4 grid gap-3">
            <label className="block space-y-2">
              <span className="text-sm text-zinc-300">Defense minutes</span>
              <input
                type="number"
                min={0}
                value={defenseMinutes}
                onChange={(event) => setDefenseMinutes(Math.max(0, Number(event.target.value) || 0))}
                className="h-11 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-white outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
              />
            </label>
            <label className="block space-y-2">
              <span className="text-sm text-zinc-300">Attack minutes</span>
              <input
                type="number"
                min={0}
                value={attackMinutes}
                onChange={(event) => setAttackMinutes(Math.max(0, Number(event.target.value) || 0))}
                className="h-11 w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 text-sm text-white outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
              />
            </label>
          </div>
        </div>

        <div className="rounded-md border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-base font-semibold text-white">Run type</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {(Object.keys(modeCopy) as MatchMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                onClick={() => setMode(mode)}
                className={`min-h-[116px] rounded-md border p-4 text-left transition focus:outline-none focus:ring-2 focus:ring-cyan-400 ${matchMode === mode ? 'border-cyan-400 bg-cyan-400/10' : 'border-zinc-700 bg-zinc-950 hover:border-zinc-500'}`}
              >
                <span className="flex items-center gap-2 text-sm font-semibold text-white">
                  {modeCopy[mode].icon}
                  {modeCopy[mode].label}
                </span>
                <span className="mt-2 block text-sm leading-5 text-zinc-400">{modeCopy[mode].detail}</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-md border border-zinc-800 bg-zinc-900">
        <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-3">
          <h2 className="flex items-center gap-2 text-base font-semibold text-white">
            <Users className="h-4 w-4 text-cyan-300" />
            Model roster
          </h2>
          <span className="text-sm text-zinc-500">{rows.length} {rows.length === 1 ? 'row' : 'rows'}</span>
        </div>

        <div className="divide-y divide-zinc-800">
          {rows.map((player) => {
            const model = getModel(player.modelId)
            return (
              <div key={player.id} className="grid gap-3 px-4 py-4 md:grid-cols-[96px_1fr_140px_140px] md:items-center">
                <div className="font-mono text-sm text-zinc-500">P{player.id}</div>
                <label className="block">
                  <span className="sr-only">Player {player.id} model</span>
                  <div className="relative">
                    <select
                      value={player.modelId}
                      onChange={(event) => updatePlayerModel(player.id, event.target.value)}
                      className="h-11 w-full appearance-none rounded-md border border-zinc-700 bg-zinc-950 px-3 pr-9 text-sm font-medium text-white outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/30"
                    >
                      {MODEL_OPTIONS.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="pointer-events-none absolute right-3 top-3 h-4 w-4 text-zinc-500" />
                  </div>
                </label>
                <div className="text-sm text-zinc-400">
                  <span className="block text-xs uppercase tracking-wide text-zinc-600">Per match</span>
                  <span className="font-mono text-zinc-200">{formatCurrency(model.matchCost)}</span>
                </div>
                <div className="text-sm text-zinc-400">
                  <span className="block text-xs uppercase tracking-wide text-zinc-600">9 samples</span>
                  <span className="font-mono text-zinc-200">{formatCurrency(model.sweepCost)}</span>
                </div>
              </div>
            )
          })}
        </div>
      </section>

      <section className="rounded-md border border-cyan-500/30 bg-zinc-900 p-4">
        <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-center">
          <div>
            <h2 className="flex items-center gap-2 text-base font-semibold text-white">
              <ListChecks className="h-4 w-4 text-cyan-300" />
              Staggered all-sample sweep
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-400">
              Runs {firstModelLabel} as defense-only and attack-only on S1-S9, one match at a time after Docker cleanup.
            </p>
            <div className="mt-3 flex flex-wrap gap-3 text-xs text-zinc-500">
              <span className="rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1">18 matches</span>
              <span className="rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1">{defenseMinutes}m defense rounds</span>
              <span className="rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1">{attackMinutes}m attack rounds</span>
              <span className="rounded-md border border-zinc-800 bg-zinc-950 px-2 py-1">{formatCurrency(staggeredSweepCost)} estimated</span>
            </div>
            {sweepMessage && <p className="mt-3 text-sm text-emerald-300">{sweepMessage}</p>}
          </div>
          <button
            type="button"
            onClick={startStaggeredSweep}
            disabled={!hasKey || isStarting || isStartingSweep}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-cyan-400 bg-cyan-400/10 px-4 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:border-zinc-700 disabled:bg-zinc-800 disabled:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-cyan-400"
          >
            <ListChecks className="h-4 w-4" />
            {isStartingSweep ? 'Starting sweep...' : hasKey ? 'Start staggered sweep' : 'Add key to sweep'}
          </button>
        </div>
      </section>

      <section className="rounded-md border border-zinc-800 bg-zinc-900 p-4">
        <details>
          <summary className="cursor-pointer text-sm font-semibold text-zinc-200">Advanced payload details</summary>
          <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">
            <div className="rounded-md border border-zinc-800 bg-zinc-950 p-3">
              <span className="block text-xs uppercase tracking-wide text-zinc-600">Provider</span>
              <span className="mt-1 block font-mono text-zinc-200">{provider}</span>
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-950 p-3">
              <span className="block text-xs uppercase tracking-wide text-zinc-600">Base URL</span>
              <span className="mt-1 block break-all font-mono text-zinc-200">{baseUrl}</span>
            </div>
            <div className="rounded-md border border-zinc-800 bg-zinc-950 p-3">
              <span className="block text-xs uppercase tracking-wide text-zinc-600">Target image</span>
              <span className="mt-1 block break-all font-mono text-zinc-200">{selectedScenario.targetImage}</span>
            </div>
          </div>
        </details>
      </section>

      {startError && (
        <div className="rounded-md border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-100">
          <div className="flex items-start gap-2">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <strong className="font-semibold">Could not start match.</strong>
              <span className="ml-1">{startError}</span>
            </div>
          </div>
        </div>
      )}

      <div className="sticky bottom-0 z-20 -mx-5 border-t border-zinc-800 bg-zinc-950/90 px-5 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="text-sm text-zinc-400">
            {selectedScenario.label} - {modeCopy[matchMode].label} - {defenseMinutes}m defense / {effectiveAttackMinutes}m attack
          </div>
          <button
            type="button"
            onClick={startMatch}
            disabled={!canStart}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-cyan-400 px-5 text-sm font-semibold text-zinc-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-zinc-700 disabled:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-cyan-400"
          >
            <Play className="h-4 w-4" />
            {isStarting ? 'Starting match...' : hasKey ? 'Start match' : 'Add key to start'}
          </button>
        </div>
      </div>

      {isStarting && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 px-4">
          <div className="w-full max-w-sm rounded-md border border-zinc-800 bg-zinc-950 p-5 shadow-2xl">
            <div className="flex items-center gap-4">
              <div className="h-9 w-9 animate-spin rounded-full border-4 border-cyan-400/20 border-t-cyan-300" />
              <div>
                <h3 className="font-semibold text-white">Starting match</h3>
                <p className="text-sm text-zinc-400">Creating containers and opening the arena.</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ConfigPage
