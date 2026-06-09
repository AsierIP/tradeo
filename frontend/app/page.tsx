'use client'

import { useEffect, useMemo, useState } from 'react'
import useSWR from 'swr'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts'
import { fetcher, postJson } from '../lib/api'

type Summary = {
  mode: string
  live_armed: boolean
  kill_switch_enabled: boolean
  initial_capital_usd: number
  risk_per_trade_usd: number
  min_reward_risk: number
  equity: Array<{ timestamp: string; equity: number; cash: number; open_risk: number }>
  pattern_metrics: Array<{
    pattern: string
    strategy_version: string
    total_trades: number
    win_rate: number
    profit_factor: number
    expectancy_r: number
    max_drawdown_pct: number
    avg_r_multiple: number
  }>
  recent_signals: Array<{
    id: number
    symbol: string
    pattern: string
    side: string
    timeframe: string
    entry: number
    stop: number
    target: number
    reward_risk: number
    confidence: number
    composite_score: number
    entry_quality_score?: number
    entry_quality_label?: string
    entry_quality_actionable?: boolean
    entry_quality_flags?: string[]
    risk_usd: number
    suggested_qty: number
    status: string
    created_at: string
  }>
  open_trades: Array<{ id: number; symbol: string; side: string; qty: number; entry: number; stop: number; target: number; status: string }>
  supervisor_state: Record<string, unknown>
}

type DiscoveredPattern = {
  id: number
  pattern_key: string
  name: string
  status: string
  side: string
  timeframe: string
  window_size: number
  cluster_id: number
  sample_count: number
  symbol_count: number
  year_count: number
  score: number
  reward_risk_estimate: number
  expectancy_r: number
  profit_factor: number
  win_rate: number
  avg_mfe_r: number
  avg_mae_r: number
  stability_score: number
  out_of_sample_expectancy_r: number
  out_of_sample_profit_factor: number
  best_rr: number
  best_tested_rr: number
  best_expectancy_r: number
  best_profit_factor: number
  best_win_rate: number
  best_max_drawdown_r: number
  preferred_rr_passed: boolean
  premium_rr_passed: boolean
  promotion_status: string
  promotion_reason: string
  rr_metrics_json: Record<string, Record<string, number>>
  rejection_reasons_json: string[]
  in_sample_expectancy_r: number
  in_sample_profit_factor: number
  out_of_sample_win_rate: number
  out_of_sample_max_drawdown_r: number
  validation_passed: boolean
  validation_reasons_json: string[]
  metrics_json: Record<string, unknown>
  feature_summary_json: Record<string, unknown>
  created_at: string
}

type DiscoveryRunResponse = {
  run_id: number
  status: string
  symbols_scanned: number
  windows_sampled: number
  clusters_evaluated: number
  accepted_patterns: number
  rejected_patterns: number
  stored_patterns: number
  duration_seconds: number
  report_path?: string
  top_patterns: Array<Record<string, unknown>>
  warnings: string[]
}

type DiscoveryRun = {
  id: number
  started_at: string
  finished_at: string | null
  status: string
  symbols_scanned: number
  windows_sampled: number
  clusters_evaluated: number
  accepted_patterns: number
  rejected_patterns: number
  duration_seconds: number
  report_path?: string | null
}

type ScanResult = {
  scanned: number
  candidates: number
  stored_signals: number
  rejected: number
}

type ModuleSignal = Summary['recent_signals'][number]
  & {
    execution_reason_code?: string | null
    execution_reason?: string | null
    retryable?: boolean
    next_action?: string | null
  }
type ModuleTrade = Summary['open_trades'][number] & {
  signal_id?: number | null
  opened_at: string
  closed_at: string | null
  exit_price: number | null
  pnl_usd: number
  r_multiple: number
  broker_order_id?: string | null
}
type ModuleOverview = {
  module: 'laboratory' | 'fox_hunter'
  signals: ModuleSignal[]
  trades: ModuleTrade[]
  pnl_points: Array<{ timestamp: string; total_pnl_usd: number; trade_pnl_usd: number; symbol?: string; status?: string }>
  stats: {
    signals: number
    trades: number
    open_trades: number
    closed_trades: number
    total_pnl_usd: number
    total_r: number
    win_rate: number
    funnel?: {
      detected: number
      actionable: number
      submitted: number
      executed: number
      blocked_or_expired: number
    }
  }
}
type ModuleStatus = {
  enabled: boolean
  operational_ok?: boolean
  state?: string
  market_session?: { regular_session_open?: boolean; state?: string; checked_at?: string }
  auto_submit_paper_orders?: boolean
  auto_submit_live_orders?: boolean
  eligible_patterns: number
  symbols_checked?: number
  last_symbols_checked?: number
  live_armed?: boolean
}
type WebNotice = {
  visible: boolean
  level?: 'ok' | 'error'
  title?: string
  message?: string
  updated_at?: string
}

function StatCard({ label, value, suffix }: { label: string; value: string | number; suffix?: string }) {
  return (
    <section className="card stat">
      <div className="value">{value}{suffix || ''}</div>
      <div className="label">{label}</div>
    </section>
  )
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase()
  const tone = normalized.includes('reject') || normalized.includes('cancel') || normalized.includes('closed')
    ? 'bad'
    : normalized.includes('executed') || normalized.includes('open') || normalized.includes('candidate')
      ? 'good'
      : normalized.includes('watch') || normalized.includes('lab')
        ? 'warn'
        : 'good'
  return <span className={`status ${tone}`}>{status}</span>
}

function EdgeBadges({ pattern }: { pattern: DiscoveredPattern }) {
  const oosPassed = pattern.out_of_sample_expectancy_r > 0 && pattern.out_of_sample_profit_factor >= 1.2
  return (
    <div className="badge-row">
      {pattern.best_rr >= 2.5 && pattern.best_expectancy_r > 0 && <span className="edge-badge">2.5R EDGE</span>}
      {pattern.preferred_rr_passed && <span className="edge-badge good">3R CANDIDATE</span>}
      {pattern.premium_rr_passed && <span className="edge-badge premium">4R PREMIUM</span>}
      <span className={`edge-badge ${oosPassed ? 'good' : 'bad'}`}>{oosPassed ? 'OOS PASSED' : 'OOS FAILED'}</span>
    </div>
  )
}

function formatRunTime(value?: string | null) {
  if (!value) return 'en curso'
  return new Date(value).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatMoney(value: number) {
  const sign = value > 0 ? '+' : ''
  return `${sign}$${value.toFixed(2)}`
}

function shortDateTime(value?: string | null) {
  if (!value) return '-'
  return new Date(value).toLocaleString('es-ES', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function formatQuality(signal: ModuleSignal) {
  const score = typeof signal.entry_quality_score === 'number' ? signal.entry_quality_score : signal.composite_score
  const label = signal.entry_quality_label || 'quality'
  return `${(score * 100).toFixed(0)}% ${label}`
}

function explainAcceptedPattern(pattern: DiscoveredPattern) {
  const lines = [
    `Lo acepto porque, en las pruebas, su mejor punto esta en ${pattern.best_rr.toFixed(1)}R: por cada 1R que arriesga, intenta sacar ${pattern.best_rr.toFixed(1)}R.`,
    `De media deja ${pattern.best_expectancy_r.toFixed(2)}R por operacion y el profit factor es ${pattern.best_profit_factor.toFixed(2)}, asi que las ganancias historicas pesan mas que las perdidas.`,
    `Ha salido en ${pattern.sample_count} muestras, ${pattern.symbol_count} simbolos y ${pattern.year_count} anos; no parece una casualidad de una sola accion.`
  ]
  if (pattern.out_of_sample_expectancy_r > 0) {
    lines.push(`Tambien aguanta fuera de muestra con ${pattern.out_of_sample_expectancy_r.toFixed(2)}R, que es buena senal para vigilarlo.`)
  } else {
    lines.push(`Fuera de muestra aun va justo (${pattern.out_of_sample_expectancy_r.toFixed(2)}R), asi que lo trato como watchlist, no como patron listo para dinero real.`)
  }
  if (pattern.preferred_rr_passed) {
    lines.push('Ademas pasa el nivel serio de 3R.')
  } else if (pattern.best_rr >= 2.5) {
    lines.push('Pasa el minimo de edge de 2.5R, aunque todavia no llega al nivel serio de 3R.')
  }
  if (pattern.premium_rr_passed) {
    lines.push('Y encima tambien pasa 4R, asi que es candidato premium.')
  }
  return lines.join(' ')
}

function OperationsModule({
  title,
  subtitle,
  overview,
  status
}: {
  title: string
  subtitle: string
  overview?: ModuleOverview
  status?: ModuleStatus
}) {
  const signals = overview?.signals || []
  const trades = overview?.trades || []
  const pnl = overview?.pnl_points?.length ? overview.pnl_points : [{ timestamp: '', total_pnl_usd: 0, trade_pnl_usd: 0 }]
  const stats = overview?.stats || { signals: 0, trades: 0, open_trades: 0, closed_trades: 0, total_pnl_usd: 0, total_r: 0, win_rate: 0 }
  const funnel = stats.funnel || { detected: stats.signals, actionable: 0, submitted: 0, executed: 0, blocked_or_expired: 0 }
  const operationalOk = Boolean(status?.operational_ok)
  const operationalTone = status?.state === 'market_closed' ? 'warn' : operationalOk ? '' : 'bad'
  return (
    <section className="card full module-card">
      <div className="section-head module-head">
        <div>
          <div className="module-kicker">{title}</div>
          <h2>{title}</h2>
          <p className="muted">{subtitle}</p>
        </div>
        <div className="module-actions">
          <div className="pill"><span className={`dot ${operationalTone}`} />{status?.state || 'status'}</div>
        </div>
      </div>

      <div className="module-stats">
        <div><strong>{status?.eligible_patterns ?? 0}</strong><span>patrones elegibles</span></div>
        <div><strong>{status?.symbols_checked ?? 0}</strong><span>acciones contrastadas</span></div>
        <div><strong>{stats.signals}</strong><span>señales</span></div>
        <div><strong>{funnel.actionable}</strong><span>accionables</span></div>
        <div><strong>{stats.open_trades}</strong><span>operaciones abiertas</span></div>
        <div><strong>{formatMoney(stats.total_pnl_usd)}</strong><span>beneficio total</span></div>
        <div><strong>{(stats.win_rate * 100).toFixed(1)}%</strong><span>win rate cerrado</span></div>
      </div>

      <div className="module-split">
        <section className="module-panel">
          <h3>Beneficio total</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={pnl}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis dataKey="timestamp" hide />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="total_pnl_usd" strokeWidth={2} fillOpacity={0.22} />
            </AreaChart>
          </ResponsiveContainer>
        </section>
        <section className="module-panel">
          <h3>Operaciones</h3>
          <div className="table-scroll compact-scroll">
            <table>
              <thead>
                <tr><th>Símbolo</th><th>Lado</th><th>Qty</th><th>Entrada</th><th>Salida</th><th>PnL</th><th>R</th><th>Estado</th><th>Apertura</th></tr>
              </thead>
              <tbody>
                {trades.map((t) => (
                  <tr key={t.id}>
                    <td>{t.symbol}</td>
                    <td>{t.side}</td>
                    <td>{t.qty}</td>
                    <td>{t.entry}</td>
                    <td>{t.exit_price ?? '-'}</td>
                    <td className={t.pnl_usd > 0 ? 'positive' : t.pnl_usd < 0 ? 'negative' : ''}>{formatMoney(t.pnl_usd)}</td>
                    <td>{t.r_multiple.toFixed(2)}R</td>
                    <td><StatusBadge status={t.status} /></td>
                    <td>{shortDateTime(t.opened_at)}</td>
                  </tr>
                ))}
                {!trades.length && <tr><td colSpan={9}>Sin operaciones todavía.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <div className="subsection">
        <h3>Señales y patrones detectados</h3>
        <div className="table-scroll signal-scroll">
          <table>
            <thead>
              <tr>
                <th>Símbolo</th><th>Lado</th><th>Entrada</th><th>Stop</th><th>Target</th><th>R:R</th><th>Conf.</th><th>Calidad</th><th>Qty</th><th>Estado</th><th>Motivo</th><th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((s) => (
                <tr key={s.id}>
                  <td>{s.symbol}</td><td>{s.side}</td><td>{s.entry}</td><td>{s.stop}</td><td>{s.target}</td>
                  <td>{s.reward_risk}</td><td>{(s.confidence * 100).toFixed(1)}%</td><td title={(s.entry_quality_flags || []).join(', ') || undefined}>{formatQuality(s)}</td><td>{s.suggested_qty}</td><td><StatusBadge status={s.status} /></td>
                  <td title={s.execution_reason || undefined}>{s.execution_reason_code || '-'}</td>
                  <td>{s.retryable ? 'retry' : (s.next_action || '-')}</td>
                </tr>
              ))}
              {!signals.length && <tr><td colSpan={12}>Sin señales todavía.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  )
}

export default function Page() {
  const [lastDiscovery, setLastDiscovery] = useState<DiscoveryRunResponse | null>(null)
  const [busyDiscovery, setBusyDiscovery] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [selectedPatternId, setSelectedPatternId] = useState<number | null>(null)
  const [scanResult, setScanResult] = useState<ScanResult | null>(null)
  const [scanError, setScanError] = useState<string | null>(null)
  const [showWebNotice, setShowWebNotice] = useState(false)
  const { data, error, mutate, isLoading } = useSWR<Summary>('/dashboard/summary', fetcher, { refreshInterval: 15000 })
  const { data: discoveredPatterns, mutate: mutateResearch } = useSWR<DiscoveredPattern[]>('/research/discovered-patterns?limit=100', fetcher, { refreshInterval: 30000 })
  const { data: discoveryRuns, mutate: mutateRuns } = useSWR<DiscoveryRun[]>('/research/runs?limit=25', fetcher, { refreshInterval: 15000 })
  const { data: labStatus } = useSWR<ModuleStatus>('/laboratory/status', fetcher, { refreshInterval: 5000 })
  const { data: foxStatus } = useSWR<ModuleStatus>('/fox-hunter/status', fetcher, { refreshInterval: 5000 })
  const { data: labOverview } = useSWR<ModuleOverview>('/laboratory/overview', fetcher, { refreshInterval: 15000 })
  const { data: foxOverview } = useSWR<ModuleOverview>('/fox-hunter/overview', fetcher, { refreshInterval: 15000 })
  const { data: webNotice } = useSWR<WebNotice>('/health/notice', fetcher, { refreshInterval: 10000 })

  useEffect(() => {
    if (!webNotice?.visible) {
      setShowWebNotice(false)
      return
    }
    setShowWebNotice(true)
    const timer = window.setTimeout(() => setShowWebNotice(false), 5000)
    return () => window.clearTimeout(timer)
  }, [webNotice?.visible, webNotice?.level, webNotice?.title, webNotice?.message, webNotice?.updated_at])

  async function runScan() {
    setIsScanning(true)
    setScanError(null)
    try {
      const result = await postJson('/scan', { limit: 50 }) as ScanResult
      setScanResult(result)
      await mutate()
    } catch (err) {
      setScanError(err instanceof Error ? err.message : 'Error lanzando escaneo')
    } finally {
      setIsScanning(false)
    }
  }

  async function generateReport() {
    await postJson('/reports/generate', {})
    await mutate()
  }

  async function runBacktest() {
    await postJson('/backtests/run', { max_symbols: 25, period: '3y', interval: '1d' })
    await mutate()
  }

  async function runDiscovery() {
    setBusyDiscovery(true)
    try {
      const result = await postJson('/research/run-discovery', {
        limit: 40,
        period: '5y',
        interval: '1d',
        max_total_windows: 6000,
        max_windows_per_symbol: 250,
        store_rejected: true
      }) as DiscoveryRunResponse
      setLastDiscovery(result)
      await mutateResearch()
      await mutateRuns()
    } finally {
      setBusyDiscovery(false)
    }
  }

  const researchRows = useMemo(() => {
    const rows = (discoveredPatterns || []).filter((p) => p.validation_passed)
    return rows.slice(0, 18).map((p) => ({
      name: p.name.replace('DISCOVERED_', '').slice(0, 18),
      expectancy_r: Number(p.expectancy_r.toFixed(3)),
      score: Number(p.score.toFixed(3)),
      profit_factor: Number(p.profit_factor.toFixed(2)),
      rr: Number(p.reward_risk_estimate.toFixed(2))
    }))
  }, [discoveredPatterns])
  const discoveredPatternRows = useMemo(() => {
    return [...(discoveredPatterns || [])].filter((p) => p.validation_passed).sort((a, b) => {
      const createdDiff = new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      return createdDiff || b.id - a.id
    })
  }, [discoveredPatterns])
  const selectedPattern = useMemo(() => {
    const rows = discoveredPatternRows
    if (!rows.length) return null
    return rows.find((p) => p.id === selectedPatternId) || rows[0]
  }, [discoveredPatternRows, selectedPatternId])
  const selectedRrRows = useMemo(() => {
    const metrics = selectedPattern?.rr_metrics_json || {}
    return Object.entries(metrics)
      .map(([rr, values]) => ({
        rr,
        win_rate: Number(values.win_rate || 0),
        expectancy_r: Number(values.expectancy_r || 0),
        profit_factor: Number(values.profit_factor || 0),
        max_drawdown_r: Number(values.max_drawdown_r || 0),
        target_hit_rate: Number(values.target_hit_rate || 0),
        stop_hit_rate: Number(values.stop_hit_rate || 0),
        avg_bars_to_target: Number(values.avg_bars_to_target || 0),
        avg_bars_to_stop: Number(values.avg_bars_to_stop || 0)
      }))
      .sort((a, b) => Number(a.rr) - Number(b.rr))
  }, [selectedPattern])

  if (error) return <main className="main"><p className="error">No puedo conectar con el backend: {error.message}</p></main>
  if (isLoading || !data) return <main className="main"><p>Cargando Tradeo…</p></main>

  const latestEquity = data.equity.length ? data.equity[data.equity.length - 1].equity : data.initial_capital_usd
  const acceptedResearch = (discoveredPatterns || []).filter((p) => p.validation_passed)
  const latestRun = discoveryRuns?.[0]
  const latestCompletedRun = discoveryRuns?.find((run) => run.status === 'completed')

  return (
    <main className="main">
      {webNotice?.visible && showWebNotice && (
        <aside className={`web-notice ${webNotice.level === 'error' ? 'bad' : 'good'}`}>
          <div className="web-notice-title">{webNotice.title || 'Tradeo'}</div>
          <div className="web-notice-message">{webNotice.message}</div>
        </aside>
      )}
      <section className="hero">
        <div>
          <div className="kicker">Tradeo · dashboard privado</div>
          <h1>Director de patrones mid/small cap</h1>
          <p className="subtitle">
            Tres módulos independientes: Research descubre patrones, Laboratorio los valida con IB Paper y Fox Hunter opera solo patrones en Producción.
          </p>
          <div className="actions">
            <button onClick={runScan} disabled={isScanning}>{isScanning ? 'Escaneando...' : 'Escanear universo'}</button>
            <button onClick={runBacktest}>Backtest rápido</button>
            <button onClick={generateReport}>Generar revisión</button>
            <button onClick={runDiscovery} disabled={busyDiscovery}>{busyDiscovery ? 'Descubriendo…' : 'Research Lab'}</button>
          </div>
          {scanResult && (
            <p className="scan-notice">
              Ultimo escaneo: {scanResult.scanned} simbolos revisados, {scanResult.candidates} candidatos,
              {' '}{scanResult.stored_signals} senales guardadas, {scanResult.rejected} rechazadas.
            </p>
          )}
          {scanError && <p className="error">Escaneo fallido: {scanError}</p>}
        </div>
        <div className="pill"><span className={`dot ${data.live_armed ? '' : 'warn'}`} />Modo {data.mode} · live {data.live_armed ? 'armado' : 'bloqueado'}</div>
      </section>

      <section className="grid">
        <StatCard label="Equity actual" value={`$${latestEquity.toFixed(2)}`} />
        <StatCard label="Research aceptados" value={acceptedResearch.length} />
        <StatCard label="Lab señales" value={labOverview?.stats.signals ?? 0} />
        <StatCard label="Fox operaciones" value={foxOverview?.stats.trades ?? 0} />

        <section className="card full research-card">
          <div className="section-head">
            <div>
              <div className="module-kicker">Research</div>
              <h2>Research · patrones descubiertos desde cero</h2>
              <p className="muted">
                Descubre patrones nuevos con clustering OHLCV. No opera; solo propone patrones para Laboratorio.
              </p>
            </div>
            <div className="mini-stats">
              <span>{acceptedResearch.length} LAB</span>
              <span>scroll filtrado: solo aceptados</span>
              <span>{discoveryRuns?.length || 0} runs recientes</span>
              {latestRun && <span>run #{latestRun.id}: {latestRun.status}</span>}
              {latestCompletedRun && (
                <span>
                  última completa #{latestCompletedRun.id}: {latestCompletedRun.accepted_patterns} aceptados · {latestCompletedRun.windows_sampled} ventanas
                </span>
              )}
              {lastDiscovery && <span>última run #{lastDiscovery.run_id}: {lastDiscovery.windows_sampled} ventanas</span>}
            </div>
          </div>
          <div className="lab-status-grid">
            <div>
              <strong>Run actual</strong>
              <span>{latestRun ? `#${latestRun.id} · ${latestRun.status} · ${formatRunTime(latestRun.started_at)}` : 'sin datos'}</span>
            </div>
            <div>
              <strong>Última completa</strong>
              <span>
                {latestCompletedRun
                  ? `#${latestCompletedRun.id} · ${latestCompletedRun.accepted_patterns} aceptados · ${latestCompletedRun.windows_sampled} ventanas`
                  : 'sin runs completas'}
              </span>
            </div>
            <div>
              <strong>Actividad reciente</strong>
              <span>{discoveryRuns?.length || 0} runs revisadas · tabla sin rechazados</span>
            </div>
            <div>
              <strong>Patrones únicos</strong>
              <span>{acceptedResearch.length} aceptados visibles</span>
            </div>
          </div>
          {researchRows.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={researchRows}>
                <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                <XAxis dataKey="name" hide />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="expectancy_r" strokeWidth={2} />
                <Line type="monotone" dataKey="score" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="muted">Aún no hay patrones descubiertos. Pulsa “Research Lab” o deja que trabaje el worker.</p>
          )}
          <div className="table-caption">
            Solo patrones aceptados. El historial restante queda dentro del scroll.
          </div>
          <div className="table-scroll pattern-scroll">
            <table>
              <thead>
                <tr>
                  <th>Patrón</th><th>Status</th><th>Best R:R</th><th>Expectancy R</th><th>Profit Factor</th><th>Win Rate</th><th>Max DD R</th><th>OOS Exp.</th><th>Preferred 3R</th><th>Premium 4R</th><th>Muestras</th><th>Símbolos</th><th>Años</th>
                </tr>
              </thead>
              <tbody>
                {discoveredPatternRows.map((p) => (
                  <tr key={p.id} onClick={() => setSelectedPatternId(p.id)} className={selectedPattern?.id === p.id ? 'selected-row' : ''}>
                    <td className="mono">{p.name}</td>
                    <td><StatusBadge status={p.status} /></td>
                    <td>{p.best_rr.toFixed(1)}</td>
                    <td>{p.best_expectancy_r.toFixed(2)}R</td>
                    <td>{p.best_profit_factor.toFixed(2)}</td>
                    <td>{(p.best_win_rate * 100).toFixed(1)}%</td>
                    <td>{p.best_max_drawdown_r.toFixed(2)}R</td>
                    <td>{p.out_of_sample_expectancy_r.toFixed(2)}R</td>
                    <td>{p.preferred_rr_passed ? 'sí' : 'no'}</td>
                    <td>{p.premium_rr_passed ? 'sí' : 'no'}</td>
                    <td>{p.sample_count}</td>
                    <td>{p.symbol_count}</td>
                    <td>{p.year_count}</td>
                  </tr>
                ))}
                {!discoveredPatternRows.length && <tr><td colSpan={13}>Sin patrones aceptados todavía.</td></tr>}
              </tbody>
            </table>
          </div>
          {selectedPattern && (
            <div className="subsection pattern-detail">
              <div className="section-head">
                <div>
                  <h3>{selectedPattern.name}</h3>
                  <p className="muted">
                    Best R:R {selectedPattern.best_rr.toFixed(1)} · Exp {selectedPattern.best_expectancy_r.toFixed(2)}R · PF {selectedPattern.best_profit_factor.toFixed(2)} · Win {(selectedPattern.best_win_rate * 100).toFixed(1)}%
                  </p>
                </div>
                <div>
                  <StatusBadge status={selectedPattern.status} />
                  <EdgeBadges pattern={selectedPattern} />
                </div>
              </div>
              <p className="accepted-explanation">{explainAcceptedPattern(selectedPattern)}</p>
              {selectedRrRows.length > 0 && (
                <>
                  <ResponsiveContainer width="100%" height={230}>
                    <LineChart data={selectedRrRows}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                      <XAxis dataKey="rr" />
                      <YAxis />
                      <Tooltip />
                      <Line type="monotone" dataKey="expectancy_r" strokeWidth={2} />
                      <Line type="monotone" dataKey="profit_factor" strokeWidth={2} />
                      <Line type="monotone" dataKey="max_drawdown_r" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr><th>R:R</th><th>Win rate</th><th>Expectancy</th><th>Profit factor</th><th>Drawdown</th><th>Target hit</th><th>Stop hit</th><th>Bars target</th><th>Bars stop</th></tr>
                      </thead>
                      <tbody>
                        {selectedRrRows.map((row) => (
                          <tr key={row.rr}>
                            <td>{row.rr}</td>
                            <td>{(row.win_rate * 100).toFixed(1)}%</td>
                            <td>{row.expectancy_r.toFixed(2)}R</td>
                            <td>{row.profit_factor.toFixed(2)}</td>
                            <td>{row.max_drawdown_r.toFixed(2)}R</td>
                            <td>{(row.target_hit_rate * 100).toFixed(1)}%</td>
                            <td>{(row.stop_hit_rate * 100).toFixed(1)}%</td>
                            <td>{row.avg_bars_to_target.toFixed(1)}</td>
                            <td>{row.avg_bars_to_stop.toFixed(1)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}
        </section>

        <OperationsModule
          title="Laboratorio"
          subtitle="Valida patrones aprobados por Research con señales y operaciones IB Paper. Misma estructura que Fox, datos de paper."
          overview={labOverview}
          status={labStatus}
        />

        <OperationsModule
          title="Fox Hunter"
          subtitle="Escanea solo patrones en Producción. Misma estructura que Laboratorio, datos live cuando el sistema esté armado."
          overview={foxOverview}
          status={foxStatus}
        />
      </section>
    </main>
  )
}
