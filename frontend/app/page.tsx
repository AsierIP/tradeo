'use client'

import type { ReactNode } from 'react'
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

type WorkspaceTab = 'research' | 'laboratory' | 'fox_hunter'

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
    opportunity_rank?: number | null
    opportunity_rank_score?: number | null
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
  run_id?: number | null
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
  centroid_json?: number[]
  metrics_json: Record<string, unknown>
  feature_summary_json: Record<string, unknown>
  created_at: string
}

type DiscoveredPatternExample = {
  id: number
  pattern_id: number
  symbol: string
  timeframe: string
  window_start: string
  window_end: string
  outcome_r: number
  mfe_r: number
  mae_r: number
  similarity: number
  kind: string
  chart_json: {
    close_norm?: number[]
    range_pct?: number[]
    volume_rel?: number[]
  }
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
  params_json?: Record<string, unknown>
  report_path?: string | null
}

type ScanResult = {
  module: string
  symbols_checked: number
  matches_found: number
  signals_created: number
  orders_submitted: number
  rejected_by_entry_gate: number
  skipped_duplicates: number
  paper_observations_opened: number
  near_miss_shadow_observations_opened: number
  shadow_no_order_observations_opened: number
  order_skip_reason_counts: Record<string, number>
  execution_mode?: string | null
  execution_degraded_to_shadow?: boolean
  execution_degrade_reason?: string | null
}

type ModuleSignal = Summary['recent_signals'][number]
  & {
    expected_value_r?: number | null
    expected_value_source?: string | null
    expected_value_history_count?: number | null
    execution_reason_code?: string | null
    execution_reason?: string | null
    retryable?: boolean
    next_action?: string | null
    cadence?: 'daily' | 'intraday' | string
    metadata_json?: Record<string, unknown>
  }
type ModuleTrade = Summary['open_trades'][number] & {
  signal_id?: number | null
  opened_at: string
  closed_at: string | null
  exit_price: number | null
  pnl_usd: number
  r_multiple: number
  broker_order_id?: string | null
  evidence_type?: string
  execution_class?: string | null
  evidence_quality?: string
  counts_as_execution_fill?: boolean
  expected_value_r?: number | null
  expected_value_source?: string | null
  expected_value_history_count?: number | null
  exit_reason?: string | null
  entry_fill_price?: number | null
  entry_slippage_bps?: number | null
  entry_slippage_r?: number | null
  total_slippage_r?: number | null
  commission_usd?: number | null
  commission_r?: number | null
  estimated_cost_per_share_usd?: number | null
  gross_r?: number | null
  net_r?: number | null
  cost_coverage?: string | null
  cadence?: 'daily' | 'intraday' | string
  metadata_json?: Record<string, unknown>
}
type ExecutionDiagnostics = {
  method?: string
  count: number
  coverage: number
  missing_shortfall_rows: number
  missing_commission_rows: number
  expected_expectancy_r?: number | null
  net_expectancy_r?: number | null
  net_profit_factor?: number | null
  net_max_drawdown_r?: number | null
  gross_expectancy_r?: number | null
  gross_delta_vs_expected_r?: number | null
  net_delta_vs_expected_r?: number | null
  mean_slippage_r?: number | null
  mean_commission_r?: number | null
}
type ModuleOverview = {
  module: 'laboratory' | 'fox_hunter'
  cadence?: 'all' | 'daily' | 'intraday'
  data_scope?: string
  query_limit?: number
  summary_limit?: number
  pnl_basis?: string
  director_source?: boolean
  scope_note?: string
  signals: ModuleSignal[]
  trades: ModuleTrade[]
  pattern_outcomes: Array<{
    pattern: string
    signals: number
    actionable: number
    submitted: number
    executed: number
    blocked_or_expired: number
    closed_trades: number
    all_closed_trades?: number
    shadow_closed?: number
    near_miss_closed?: number
    ibkr_paper_filled?: number
    live?: number
    live_filled?: number
    degraded_closed?: number
    total_pnl_usd: number
    total_r: number
    avg_quality_score: number
    top_reason_code: string
  }>
  pnl_points: Array<{ timestamp: string; total_pnl_usd: number; trade_pnl_usd: number; symbol?: string; status?: string }>
  shadow_pnl_points?: Array<{ timestamp: string; total_pnl_usd: number; trade_pnl_usd: number; symbol?: string; status?: string }>
  evidence_summary?: {
    shadow_closed: number
    near_miss_closed: number
    ibkr_paper_filled: number
    live_filled: number
    degraded_closed: number
  }
  execution_diagnostics?: ExecutionDiagnostics
  stats: {
    signals: number
    trades: number
    open_trades: number
    closed_trades: number
    all_closed_trades?: number
    execution_closed_trades?: number
    shadow_closed_trades?: number
    near_miss_closed_trades?: number
    ibkr_paper_filled_trades?: number
    live_trades?: number
    live_filled_trades?: number
    degraded_closed_trades?: number
    pnl_basis?: string
    shadow_only?: boolean
    total_pnl_usd: number
    total_r: number
    shadow_total_r?: number
    win_rate: number
    execution_diagnostics?: ExecutionDiagnostics
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
  paper_orders_allowed?: boolean
  live_orders_allowed?: boolean
  blocked_but_healthy?: boolean
  execution_block_reason?: string | null
  production_manifest_required?: boolean
  production_status_patterns?: number
  production_manifest_blocked_patterns?: number
  legacy_runtime_blocked_patterns?: number
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
type IntradayConfig = {
  enabled: boolean
  shadow_enabled: boolean
  paper_enabled: boolean
  live_enabled: boolean
  live_armed: boolean
  timeframes: string[]
}
type IntradaySessionJob = {
  job_id: string
  status: string
  reason?: string | null
  generated_at?: string | null
  details?: Record<string, unknown>
}
type IntradaySessionStatus = {
  intraday_enabled: boolean
  paper_enabled: boolean
  live_enabled: boolean
  live_armed: boolean
  updated_at?: string | null
  jobs: Record<string, IntradaySessionJob>
  reason?: string | null
}
type IntradayStatus = {
  config: IntradayConfig
  session: IntradaySessionStatus
}
type IntradayFlatStatus = {
  enabled: boolean
  session: IntradaySessionStatus
}
type IntradayPacingWindow = {
  window_seconds: number
  capacity: number
  daily_reserved: number
  used: number
  remaining: number
  next_available_at?: string | null
}
type IntradayPacing = {
  generated_at: string
  request_types: Record<string, { windows: IntradayPacingWindow[] }>
  omitted_symbols_by_pacing: string[]
  last_update_by_timeframe: Record<string, string>
  degraded_to_shadow_safe: boolean
  last_degraded_at?: string | null
  new_entries_allowed: boolean
}
type FlatPreviewOrder = {
  symbol: string
  side: string
  qty: number
  reason: string
  preview: boolean
}
type IntradayFlatPreview = {
  ok: boolean
  preview: boolean
  state: string
  orders: FlatPreviewOrder[]
  reason_code: string
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

function ScopeDivider({
  label,
  title,
  children
}: {
  label: string
  title: string
  children?: ReactNode
}) {
  return (
    <section className="scope-divider full">
      <div>
        <div className="module-kicker">{label}</div>
        <h2>{title}</h2>
      </div>
      {children && <div className="mode-strip">{children}</div>}
    </section>
  )
}

function ModeChip({
  label,
  value,
  tone = 'warn'
}: {
  label: string
  value: string
  tone?: 'good' | 'warn' | 'bad'
}) {
  return (
    <span className={`mode-chip ${tone}`}>
      <strong>{label}</strong>
      <span>{value}</span>
    </span>
  )
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

function formatRValue(value?: number | null, digits = 2) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '-'
  return `${value.toFixed(digits)}R`
}

function shortDateTime(value?: string | null) {
  if (!value) return '-'
  return new Date(value).toLocaleString('es-ES', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function formatScore(value?: number | null, digits = 3) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '-'
}

function formatCompactValue(value?: string | number | boolean | null) {
  if (typeof value === 'number') {
    if (Math.abs(value) >= 10) return value.toFixed(1)
    return value.toFixed(2)
  }
  if (typeof value === 'boolean') return value ? 'sí' : 'no'
  return value || '-'
}

function formatDetailValue(value: unknown) {
  if (typeof value === 'number') return formatCompactValue(value)
  if (typeof value === 'boolean') return value ? 'sí' : 'no'
  if (typeof value === 'string') return value || '-'
  if (value === null || typeof value === 'undefined') return '-'
  if (Array.isArray(value)) return `${value.length} items`
  if (typeof value === 'object') return 'objeto'
  return String(value)
}

function intradayJobDetails(job: IntradaySessionJob) {
  const detailText = Object.entries(job.details || {})
    .slice(0, 4)
    .map(([key, value]) => `${key}: ${formatDetailValue(value)}`)
    .join(' · ')
  return detailText || job.reason || '-'
}

function formatWindowSeconds(value: number) {
  if (value % 3600 === 0) return `${value / 3600}h`
  if (value % 60 === 0) return `${value / 60}m`
  return `${value}s`
}

function intradayModeTone(enabled?: boolean, armed?: boolean): 'good' | 'warn' | 'bad' {
  if (!enabled) return 'bad'
  if (armed === false) return 'warn'
  return 'good'
}

function intradayModeLabel(enabled?: boolean, armed?: boolean) {
  if (!enabled) return 'apagado'
  if (armed === false) return 'gate cerrado'
  return 'activo'
}

function evidenceLabel(trade: ModuleTrade) {
  const type = trade.evidence_type || 'unknown'
  const quality = trade.evidence_quality === 'degraded' ? ' degradada' : ''
  if (type === 'near_miss_shadow') return `near-miss shadow${quality}`
  if (type === 'shadow_no_order') return `shadow sin orden${quality}`
  if (type === 'ibkr_paper_fill') return `IBKR paper fill${quality}`
  if (type === 'ibkr_paper_order') return `IBKR paper order${quality}`
  if (type === 'live_fill') return `live fill${quality}`
  if (type === 'live_order') return `live order${quality}`
  return `${type}${quality}`
}

function expectedValueLabel(item: { expected_value_r?: number | null; expected_value_source?: string | null; expected_value_history_count?: number | null }) {
  const value = formatRValue(item.expected_value_r)
  const source = item.expected_value_source === 'paper_history'
    ? `paper n=${formatCompactValue(item.expected_value_history_count)}`
    : item.expected_value_source === 'research_pattern'
      ? 'research'
      : 'sin EV'
  return `${value} · ${source}`
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

function isDailyPattern(pattern: DiscoveredPattern) {
  const timeframe = pattern.timeframe.toLowerCase()
  return timeframe === '1d' || timeframe === 'd' || timeframe === 'day' || timeframe === 'daily'
}

function isDailyRun(run: DiscoveryRun) {
  const interval = String(run.params_json?.interval || '').toLowerCase()
  return !interval || interval === '1d' || interval === 'd' || interval === 'day' || interval === 'daily'
}

function isIntradayRun(run: DiscoveryRun) {
  return !isDailyRun(run)
}

function patternRrRows(pattern?: DiscoveredPattern | null) {
  const metrics = pattern?.rr_metrics_json || {}
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
}

function representativeExample(examples?: DiscoveredPatternExample[]) {
  const rows = [...(examples || [])].sort((a, b) => {
    const aWinner = a.kind.toLowerCase().includes('winner') ? 1 : 0
    const bWinner = b.kind.toLowerCase().includes('winner') ? 1 : 0
    const aProfitable = a.outcome_r > 0 ? 1 : 0
    const bProfitable = b.outcome_r > 0 ? 1 : 0
    const aTypical = a.kind.toLowerCase().includes('typical') ? 1 : 0
    const bTypical = b.kind.toLowerCase().includes('typical') ? 1 : 0
    return bWinner - aWinner || bProfitable - aProfitable || bTypical - aTypical || b.similarity - a.similarity
  })
  return rows[0] || null
}

function exampleShapeRows(example?: DiscoveredPatternExample | null) {
  const close = example?.chart_json.close_norm || []
  const range = example?.chart_json.range_pct || []
  const volume = example?.chart_json.volume_rel || []
  return close
    .filter((value) => typeof value === 'number' && Number.isFinite(value))
    .map((close_norm, index) => ({
      bar: index + 1,
      close_norm,
      range_pct: typeof range[index] === 'number' ? range[index] : null,
      volume_rel: typeof volume[index] === 'number' ? volume[index] : null
    }))
}

function ResearchPatternPanel({
  title,
  subtitle,
  patterns,
  selectedPatternId,
  onSelectPattern,
  latestRun,
  latestCompletedRun,
  discoveryRunsCount
}: {
  title: string
  subtitle: string
  patterns: DiscoveredPattern[]
  selectedPatternId: number | null
  onSelectPattern: (patternId: number) => void
  latestRun?: DiscoveryRun
  latestCompletedRun?: DiscoveryRun
  discoveryRunsCount: number
}) {
  const selectedPattern = patterns.find((p) => p.id === selectedPatternId) || null
  const { data: selectedExamples } = useSWR<DiscoveredPatternExample[]>(
    selectedPattern ? `/research/discovered-patterns/${selectedPattern.id}/examples` : null,
    fetcher,
    { refreshInterval: 30000 }
  )
  const selectedExample = representativeExample(selectedExamples)
  const currentRunPatterns = latestRun ? patterns.filter((p) => p.run_id === latestRun.id).length : 0
  const currentRunDetected = latestRun ? latestRun.accepted_patterns + latestRun.rejected_patterns : 0
  const shapeRows = exampleShapeRows(selectedExample)
  const rrRows = patternRrRows(selectedPattern)

  return (
    <section className="card full research-card">
      <div className="section-head">
        <div>
          <div className="module-kicker">Research</div>
          <h2>{title}</h2>
          <p className="muted">{subtitle}</p>
        </div>
        <div className="mini-stats">
          <span>{patterns.length} aceptados</span>
          <span>{discoveryRunsCount} runs recientes</span>
          {latestRun && <span>run #{latestRun.id}: {latestRun.status}</span>}
        </div>
      </div>

      <div className="lab-status-grid research-run-grid">
        <div>
          <strong>Run actual</strong>
          <span>{latestRun ? `#${latestRun.id} · ${latestRun.status} · ${formatRunTime(latestRun.started_at)}` : 'sin datos'}</span>
        </div>
        <div>
          <strong>Detectados en run</strong>
          <span>{currentRunDetected} total · {currentRunPatterns} visibles en esta tabla</span>
        </div>
        <div>
          <strong>Detectados totales</strong>
          <span>{patterns.length} patrones aceptados</span>
        </div>
        <div>
          <strong>Última completa</strong>
          <span>
            {latestCompletedRun
              ? `#${latestCompletedRun.id} · ${latestCompletedRun.accepted_patterns} aceptados · ${latestCompletedRun.windows_sampled} ventanas`
              : 'sin runs completas'}
          </span>
        </div>
      </div>

      <div className="table-caption">
        Patrones aceptados. Click en una fila para abrir detalle debajo.
      </div>
      <div className="table-scroll pattern-scroll">
        <table>
          <thead>
            <tr>
              <th>Patrón</th><th>TF</th><th>Status</th><th>Best R:R</th><th>Expectancy</th><th>PF</th><th>Win</th><th>OOS</th><th>Score</th><th>Muestras</th><th>Símb.</th><th>Run</th>
            </tr>
          </thead>
          <tbody>
            {patterns.map((p) => (
              <tr key={p.id} onClick={() => onSelectPattern(p.id)} className={selectedPattern?.id === p.id ? 'selected-row' : ''}>
                <td className="mono">{p.name}</td>
                <td>{p.timeframe}</td>
                <td><StatusBadge status={p.status} /></td>
                <td>{p.best_rr.toFixed(1)}</td>
                <td>{p.best_expectancy_r.toFixed(2)}R</td>
                <td>{p.best_profit_factor.toFixed(2)}</td>
                <td>{(p.best_win_rate * 100).toFixed(1)}%</td>
                <td>{p.out_of_sample_expectancy_r.toFixed(2)}R</td>
                <td>{p.score.toFixed(3)}</td>
                <td>{p.sample_count}</td>
                <td>{p.symbol_count}</td>
                <td>{p.run_id ? `#${p.run_id}` : '-'}</td>
              </tr>
            ))}
            {!patterns.length && <tr><td colSpan={12}>Sin patrones aceptados en este bloque todavía.</td></tr>}
          </tbody>
        </table>
      </div>

      {selectedPattern && (
        <div className="subsection pattern-detail">
          <div className="section-head">
            <div>
              <h3>{selectedPattern.name}</h3>
              <p className="muted">
                {selectedPattern.timeframe} · Best R:R {selectedPattern.best_rr.toFixed(1)} · Exp {selectedPattern.best_expectancy_r.toFixed(2)}R · PF {selectedPattern.best_profit_factor.toFixed(2)} · Win {(selectedPattern.best_win_rate * 100).toFixed(1)}%
              </p>
            </div>
            <div>
              <StatusBadge status={selectedPattern.status} />
              <EdgeBadges pattern={selectedPattern} />
            </div>
          </div>
          <p className="accepted-explanation">{explainAcceptedPattern(selectedPattern)}</p>

          <div className="pattern-detail-grid">
            <section className="module-panel">
              <h3>Forma real del patrón</h3>
              {shapeRows.length > 0 ? (
                <>
                  <p className="muted pattern-example-meta">
                    {selectedExample?.symbol} · {selectedPattern.side.toUpperCase()} · {selectedExample?.kind} · {formatRValue(selectedExample?.outcome_r)} resultado · {shapeRows.length} velas · {shortDateTime(selectedExample?.window_start)}-{shortDateTime(selectedExample?.window_end)}
                  </p>
                  <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={shapeRows}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
                    <XAxis dataKey="bar" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="close_norm" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="range_pct" strokeWidth={1} dot={false} />
                  </LineChart>
                  </ResponsiveContainer>
                </>
              ) : (
                <p className="muted">Selecciona un patrón con ejemplos guardados para ver una ventana real, no el vector interno.</p>
              )}
            </section>

            <section className="module-panel">
              <h3>Datos clave</h3>
              <div className="detail-kv-grid">
                <div><strong>{selectedPattern.sample_count}</strong><span>muestras</span></div>
                <div><strong>{selectedPattern.symbol_count}</strong><span>símbolos</span></div>
                <div><strong>{selectedPattern.year_count}</strong><span>años</span></div>
                <div><strong>{selectedPattern.stability_score.toFixed(2)}</strong><span>estabilidad</span></div>
                <div><strong>{selectedPattern.avg_mfe_r.toFixed(2)}R</strong><span>avg MFE</span></div>
                <div><strong>{selectedPattern.avg_mae_r.toFixed(2)}R</strong><span>avg MAE</span></div>
                <div><strong>{selectedPattern.side.toUpperCase()}</strong><span>dirección</span></div>
                <div><strong>{formatRValue(selectedExample?.outcome_r)}</strong><span>resultado ejemplo</span></div>
              </div>
            </section>
          </div>

          {rrRows.length > 0 && (
            <div className="subsection compact-subsection">
              <h3>Sensibilidad por R:R</h3>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr><th>R:R</th><th>Win rate</th><th>Expectancy</th><th>Profit factor</th><th>Drawdown</th><th>Target hit</th><th>Stop hit</th><th>Bars target</th><th>Bars stop</th></tr>
                  </thead>
                  <tbody>
                    {rrRows.map((row) => (
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
            </div>
          )}
        </div>
      )}
    </section>
  )
}

function IntradayPanel({
  status,
  pacing,
  flatStatus,
  flatPreview,
  previewBusy,
  previewError,
  onPreviewFlat
}: {
  status?: IntradayStatus
  pacing?: IntradayPacing
  flatStatus?: IntradayFlatStatus
  flatPreview?: IntradayFlatPreview | null
  previewBusy: boolean
  previewError?: string | null
  onPreviewFlat: () => void
}) {
  const config = status?.config
  const session = status?.session || flatStatus?.session
  const timeframes = config?.timeframes?.length ? config.timeframes : []
  const jobs = Object.values(session?.jobs || {}).sort((a, b) => {
    const left = a.generated_at ? new Date(a.generated_at).getTime() : 0
    const right = b.generated_at ? new Date(b.generated_at).getTime() : 0
    return right - left
  })
  const requestTypes = Object.entries(pacing?.request_types || {})
  const flatEnabled = Boolean(flatStatus?.enabled)
  const liveLabel = config?.live_enabled
    ? config.live_armed ? 'armado' : 'sin armar'
    : status ? 'apagado' : 'cargando'
  const liveTone = status ? intradayModeTone(config?.live_enabled, config?.live_armed) : 'warn'

  return (
    <section className="card full intraday-card">
      <div className="section-head module-head">
        <div>
          <div className="module-kicker">Intraday</div>
          <h2>Panel intradía operativo</h2>
          <p className="muted">
            Estado de sesión, lanes shadow/paper/live, pacing IBKR y flat EOD con preview obligatorio.
          </p>
        </div>
        <div className="module-actions">
          <div className="pill">
            <span className={`dot ${config?.enabled ? '' : 'warn'}`} />
            intraday {config?.enabled ? 'activo' : 'apagado'}
          </div>
          <div className="pill">
            <span className={`dot ${config?.live_armed ? '' : 'warn'}`} />
            live {config?.live_armed ? 'armado' : 'bloqueado'}
          </div>
          <div className="pill">actualizado: {shortDateTime(session?.updated_at)}</div>
        </div>
      </div>

      <div className="mode-lane-grid">
        <ModeChip
          label="Shadow"
          value={status ? intradayModeLabel(config?.shadow_enabled) : 'cargando'}
          tone={status ? intradayModeTone(config?.shadow_enabled) : 'warn'}
        />
        <ModeChip
          label="Paper"
          value={status ? intradayModeLabel(config?.paper_enabled) : 'cargando'}
          tone={status ? intradayModeTone(config?.paper_enabled) : 'warn'}
        />
        <ModeChip label="Live" value={liveLabel} tone={liveTone} />
      </div>

      <div className="intraday-stat-grid">
        <div>
          <strong>{timeframes.join(', ') || '-'}</strong>
          <span>timeframes</span>
        </div>
        <div>
          <strong>{pacing?.new_entries_allowed ? 'sí' : 'no'}</strong>
          <span>nuevas entradas por pacing</span>
        </div>
        <div>
          <strong>{pacing?.degraded_to_shadow_safe ? 'shadow' : 'normal'}</strong>
          <span>degradación pacing</span>
        </div>
        <div>
          <strong>{flatEnabled ? 'activo' : 'apagado'}</strong>
          <span>flat EOD</span>
        </div>
      </div>

      <div className="intraday-grid">
        <section className="module-panel">
          <h3>Sesión</h3>
          <div className="table-scroll intraday-scroll">
            <table>
              <thead>
                <tr><th>Job</th><th>Estado</th><th>Detalle</th><th>Hora</th></tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.job_id}>
                    <td className="mono">{job.job_id}</td>
                    <td><StatusBadge status={job.status} /></td>
                    <td className="wrap-cell" title={job.reason || undefined}>{intradayJobDetails(job)}</td>
                    <td>{shortDateTime(job.generated_at)}</td>
                  </tr>
                ))}
                {!jobs.length && <tr><td colSpan={4}>Sin jobs intradía reportados todavía.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>

        <section className="module-panel">
          <h3>Pacing IBKR</h3>
          <div className="table-scroll intraday-scroll">
            <table>
              <thead>
                <tr><th>Tipo</th><th>Ventana</th><th>Uso</th><th>Reservado daily</th><th>Next</th></tr>
              </thead>
              <tbody>
                {requestTypes.flatMap(([requestType, payload]) => (
                  payload.windows.map((window) => (
                    <tr key={`${requestType}-${window.window_seconds}`}>
                      <td className="mono">{requestType}</td>
                      <td>{formatWindowSeconds(window.window_seconds)}</td>
                      <td>{window.used}/{window.capacity} · quedan {window.remaining}</td>
                      <td>{window.daily_reserved}</td>
                      <td>{shortDateTime(window.next_available_at)}</td>
                    </tr>
                  ))
                ))}
                {!requestTypes.length && <tr><td colSpan={5}>Sin métricas de pacing todavía.</td></tr>}
              </tbody>
            </table>
          </div>
          <div className="mini-stats intraday-mini">
            <span>omitidos: {pacing?.omitted_symbols_by_pacing?.length ?? 0}</span>
            <span>última degradación: {shortDateTime(pacing?.last_degraded_at)}</span>
          </div>
        </section>

        <section className="module-panel">
          <h3>Flat EOD</h3>
          <div className="flat-action-row">
            <button onClick={onPreviewFlat} disabled={previewBusy}>
              {previewBusy ? 'Calculando preview...' : 'Preview flat'}
            </button>
            <button className="gated-action" disabled title="Backend gated: flat real requiere adapter broker y preview previo">
              Flat real bloqueado
            </button>
          </div>
          <div className="flat-gate">
            <span>gate: preview obligatorio</span>
            <span>backend: flat/request 409 hasta broker-backed flat</span>
            <span>live_armed: {config?.live_armed ? 'sí' : 'no'}</span>
          </div>
          {previewError && <p className="error">Preview flat fallido: {previewError}</p>}
          {flatPreview && (
            <div className="preview-result">
              <div className="preview-head">
                <strong>{flatPreview.state}</strong>
                <span>{flatPreview.reason_code}</span>
                <span>{flatPreview.orders.length} órdenes preview</span>
              </div>
              {flatPreview.orders.length ? (
                <div className="table-scroll intraday-scroll">
                  <table>
                    <thead>
                      <tr><th>Símbolo</th><th>Lado</th><th>Qty</th><th>Motivo</th></tr>
                    </thead>
                    <tbody>
                      {flatPreview.orders.map((order) => (
                        <tr key={`${order.symbol}-${order.side}-${order.qty}`}>
                          <td className="mono">{order.symbol}</td>
                          <td>{order.side}</td>
                          <td>{order.qty}</td>
                          <td>{order.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="muted">Preview sin posiciones que cerrar.</p>
              )}
            </div>
          )}
        </section>
      </div>
    </section>
  )
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
  const trades = overview?.trades || []
  const activeTrades = trades.filter((trade) => trade.status.toLowerCase() === 'open')
  const pnl = overview?.pnl_points?.length ? overview.pnl_points : [{ timestamp: '', total_pnl_usd: 0, trade_pnl_usd: 0 }]
  const stats = overview?.stats || { signals: 0, trades: 0, open_trades: 0, closed_trades: 0, total_pnl_usd: 0, total_r: 0, win_rate: 0 }
  const executionDiagnostics = overview?.execution_diagnostics || stats.execution_diagnostics
  const scopeNote = overview?.scope_note || 'Dashboard operativo; no fuente Director.'
  const pnlBasis = overview?.pnl_basis || stats.pnl_basis || 'operational_fills_only'
  const operationalOk = Boolean(status?.operational_ok)
  const operationalTone = status?.state === 'market_closed' ? 'warn' : operationalOk ? '' : 'bad'
  const blockedHealthy = Boolean(status?.blocked_but_healthy)
  const lastPoint = pnl[pnl.length - 1]
  const totalPnl = typeof lastPoint?.total_pnl_usd === 'number' ? lastPoint.total_pnl_usd : stats.total_pnl_usd
  return (
    <section className="card full module-card operation-lane">
      <div className="section-head module-head">
        <div>
          <div className="module-kicker">{title}</div>
          <h2>{title}</h2>
          <p className="muted">{subtitle}</p>
        </div>
        <div className="module-actions">
          <div className="pill"><span className={`dot ${operationalTone}`} />{status?.state || 'status'}</div>
          {blockedHealthy && <div className="pill" title={status?.execution_block_reason || undefined}><span className="dot warn" />blocked-but-healthy</div>}
          {typeof status?.paper_orders_allowed === 'boolean' && (
            <div className="pill">paper_orders_allowed: {status.paper_orders_allowed ? 'true' : 'false'}</div>
          )}
          {typeof status?.live_orders_allowed === 'boolean' && (
            <div className="pill">live_orders_allowed: {status.live_orders_allowed ? 'true' : 'false'}</div>
          )}
          <div className="pill" title={`${scopeNote} PnL: ${pnlBasis}`}>PnL cerradas</div>
        </div>
      </div>

      <div className="operation-metrics">
        <div><strong>{activeTrades.length}</strong><span>órdenes activas</span></div>
        <div><strong>{stats.closed_trades}</strong><span>cerradas con fill</span></div>
        <div><strong className={totalPnl > 0 ? 'positive' : totalPnl < 0 ? 'negative' : ''}>{formatMoney(totalPnl)}</strong><span>P/L cerrado</span></div>
        <div title={`EV ${formatRValue(executionDiagnostics?.net_expectancy_r)} · cobertura coste ${((executionDiagnostics?.coverage ?? 0) * 100).toFixed(0)}%`}>
          <strong>{(stats.win_rate * 100).toFixed(1)}%</strong><span>win rate</span>
        </div>
      </div>

      <div className="operation-layout">
        <section className="module-panel">
          <h3>Órdenes activas</h3>
          <div className="table-scroll active-orders-scroll">
            <table>
              <thead>
                <tr><th>Símbolo</th><th>Lado</th><th>Qty</th><th>Entrada</th><th>Stop</th><th>Target</th><th>EV</th><th>Evidencia</th><th>Apertura</th></tr>
              </thead>
              <tbody>
                {activeTrades.map((t) => (
                  <tr key={t.id}>
                    <td>{t.symbol}</td>
                    <td>{t.side}</td>
                    <td>{t.qty}</td>
                    <td>{t.entry}</td>
                    <td>{t.stop}</td>
                    <td>{t.target}</td>
                    <td title={t.expected_value_source || undefined}>{expectedValueLabel(t)}</td>
                    <td>{evidenceLabel(t)}</td>
                    <td>{shortDateTime(t.opened_at)}</td>
                  </tr>
                ))}
                {!activeTrades.length && <tr><td colSpan={9}>Sin órdenes activas.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
        <section className="module-panel">
          <h3>P/L acumulado de cerradas</h3>
          <ResponsiveContainer width="100%" height={230}>
            <AreaChart data={pnl}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis dataKey="timestamp" hide />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="total_pnl_usd" strokeWidth={2} fillOpacity={0.22} />
            </AreaChart>
          </ResponsiveContainer>
        </section>
      </div>
    </section>
  )
}

export default function Page() {
  const [activeTab, setActiveTab] = useState<WorkspaceTab>('research')
  const [lastDiscovery, setLastDiscovery] = useState<DiscoveryRunResponse | null>(null)
  const [busyDiscovery, setBusyDiscovery] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const [selectedIntradayPatternId, setSelectedIntradayPatternId] = useState<number | null>(null)
  const [selectedDailyPatternId, setSelectedDailyPatternId] = useState<number | null>(null)
  const [scanResult, setScanResult] = useState<ScanResult | null>(null)
  const [scanError, setScanError] = useState<string | null>(null)
  const [showWebNotice, setShowWebNotice] = useState(false)
  const [flatPreview, setFlatPreview] = useState<IntradayFlatPreview | null>(null)
  const [flatPreviewBusy, setFlatPreviewBusy] = useState(false)
  const [flatPreviewError, setFlatPreviewError] = useState<string | null>(null)
  const { data, error, mutate, isLoading } = useSWR<Summary>('/dashboard/summary', fetcher, { refreshInterval: 15000 })
  const { data: discoveredPatterns, mutate: mutateResearch } = useSWR<DiscoveredPattern[]>('/research/discovered-patterns?limit=100', fetcher, { refreshInterval: 30000 })
  const { data: discoveryRuns, mutate: mutateRuns } = useSWR<DiscoveryRun[]>('/research/runs?limit=25', fetcher, { refreshInterval: 15000 })
  const { data: labStatus } = useSWR<ModuleStatus>('/laboratory/status', fetcher, { refreshInterval: 5000 })
  const { data: foxStatus } = useSWR<ModuleStatus>('/fox-hunter/status', fetcher, { refreshInterval: 5000 })
  const { data: labDailyOverview } = useSWR<ModuleOverview>('/laboratory/overview?cadence=daily', fetcher, { refreshInterval: 15000 })
  const { data: labIntradayOverview } = useSWR<ModuleOverview>('/laboratory/overview?cadence=intraday', fetcher, { refreshInterval: 15000 })
  const { data: foxDailyOverview } = useSWR<ModuleOverview>('/fox-hunter/overview?cadence=daily', fetcher, { refreshInterval: 15000 })
  const { data: foxIntradayOverview } = useSWR<ModuleOverview>('/fox-hunter/overview?cadence=intraday', fetcher, { refreshInterval: 15000 })
  const { data: intradayStatus } = useSWR<IntradayStatus>('/intraday/status', fetcher, { refreshInterval: 5000 })
  const { data: intradayPacing } = useSWR<IntradayPacing>('/intraday/pacing', fetcher, { refreshInterval: 5000 })
  const { data: intradayFlatStatus, mutate: mutateIntradayFlatStatus } = useSWR<IntradayFlatStatus>('/intraday/flat/status', fetcher, { refreshInterval: 5000 })
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
      const result = await postJson('/laboratory/scan', { limit: 50 }) as ScanResult
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

  async function previewIntradayFlat() {
    setFlatPreviewBusy(true)
    setFlatPreviewError(null)
    try {
      const result = await postJson('/intraday/flat/preview', {}) as IntradayFlatPreview
      setFlatPreview(result)
      await mutateIntradayFlatStatus()
    } catch (err) {
      setFlatPreviewError(err instanceof Error ? err.message : 'Error calculando preview flat')
    } finally {
      setFlatPreviewBusy(false)
    }
  }

  const discoveredPatternRows = useMemo(() => {
    return [...(discoveredPatterns || [])].filter((p) => p.validation_passed).sort((a, b) => {
      const createdDiff = new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      return createdDiff || b.id - a.id
    })
  }, [discoveredPatterns])
  const intradayPatternRows = useMemo(() => discoveredPatternRows.filter((p) => !isDailyPattern(p)), [discoveredPatternRows])
  const dailyPatternRows = useMemo(() => discoveredPatternRows.filter(isDailyPattern), [discoveredPatternRows])
  const intradayRuns = useMemo(() => (discoveryRuns || []).filter(isIntradayRun), [discoveryRuns])
  const dailyRuns = useMemo(() => (discoveryRuns || []).filter(isDailyRun), [discoveryRuns])

  if (error) return <main className="main"><p className="error">No puedo conectar con el backend: {error.message}</p></main>
  if (isLoading || !data) return <main className="main"><p>Cargando Tradeo…</p></main>

  const latestEquity = data.equity.length ? data.equity[data.equity.length - 1].equity : data.initial_capital_usd
  const acceptedResearch = (discoveredPatterns || []).filter((p) => p.validation_passed)
  const latestIntradayRun = intradayRuns[0]
  const latestDailyRun = dailyRuns[0]
  const latestCompletedIntradayRun = intradayRuns.find((run) => run.status === 'completed')
  const latestCompletedDailyRun = dailyRuns.find((run) => run.status === 'completed')

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
            Daily e intradía separados: Research descubre patrones, Laboratorio valida con IB Paper, Fox Hunter opera Producción e Intraday queda bajo gates propios.
          </p>
          <div className="actions">
            <button onClick={runScan} disabled={isScanning}>{isScanning ? 'Escaneando...' : 'Escanear Lab'}</button>
            <button onClick={runBacktest}>Backtest rápido</button>
            <button onClick={generateReport}>Generar revisión</button>
            <button onClick={runDiscovery} disabled={busyDiscovery}>{busyDiscovery ? 'Descubriendo…' : 'Research Lab'}</button>
          </div>
          <nav className="workspace-tabs top-workspace-tabs" aria-label="Módulos Tradeo">
            <button className={activeTab === 'research' ? 'active' : ''} onClick={() => setActiveTab('research')}>
              Research
            </button>
            <button className={activeTab === 'laboratory' ? 'active' : ''} onClick={() => setActiveTab('laboratory')}>
              Laboratorio
            </button>
            <button className={activeTab === 'fox_hunter' ? 'active' : ''} onClick={() => setActiveTab('fox_hunter')}>
              Fox Hunter
            </button>
          </nav>
          {scanResult && (
            <p className="scan-notice">
              Último Lab: {scanResult.symbols_checked} símbolos, {scanResult.matches_found} matches,
              {' '}{scanResult.signals_created} señales, {scanResult.orders_submitted} órdenes,
              {' '}{scanResult.paper_observations_opened} shadows.
              {scanResult.execution_degraded_to_shadow && ` Degradado: ${scanResult.execution_degrade_reason}.`}
            </p>
          )}
          {scanError && <p className="error">Escaneo fallido: {scanError}</p>}
        </div>
        <div className="pill"><span className={`dot ${data.live_armed ? '' : 'warn'}`} />Modo {data.mode} · live {data.live_armed ? 'armado' : 'bloqueado'}</div>
      </section>

      <section className="grid">
        <StatCard label="Equity actual" value={`$${latestEquity.toFixed(2)}`} />
        <StatCard label="Research aceptados" value={acceptedResearch.length} />
        <StatCard label="Lab activas" value={(labDailyOverview?.stats.open_trades ?? 0) + (labIntradayOverview?.stats.open_trades ?? 0)} />
        <StatCard label="Fox activas" value={(foxDailyOverview?.stats.open_trades ?? 0) + (foxIntradayOverview?.stats.open_trades ?? 0)} />

        {activeTab === 'research' && (
          <>
            <ScopeDivider label="Research" title="Intradía">
              <ModeChip label="Aceptados" value={`${intradayPatternRows.length}`} tone={intradayPatternRows.length ? 'good' : 'warn'} />
              <ModeChip label="Run" value={latestIntradayRun ? `#${latestIntradayRun.id}` : 'sin run intradía'} tone={latestIntradayRun ? 'good' : 'warn'} />
              <ModeChip label="Total run" value={latestIntradayRun ? `${latestIntradayRun.accepted_patterns + latestIntradayRun.rejected_patterns}` : '0'} tone="warn" />
            </ScopeDivider>
            <ResearchPatternPanel
              title="Research Intradía"
              subtitle="Patrones intradía detectados y aceptados. Sin gráficos en lista; solo tabla y detalle al seleccionar."
              patterns={intradayPatternRows}
              selectedPatternId={selectedIntradayPatternId}
              onSelectPattern={setSelectedIntradayPatternId}
              latestRun={latestIntradayRun}
              latestCompletedRun={latestCompletedIntradayRun}
              discoveryRunsCount={intradayRuns.length}
            />

            <ScopeDivider label="Research" title="Daily">
              <ModeChip label="Aceptados" value={`${dailyPatternRows.length}`} tone={dailyPatternRows.length ? 'good' : 'warn'} />
              <ModeChip label="Run" value={latestDailyRun ? `#${latestDailyRun.id}` : 'sin run daily'} tone={latestDailyRun ? 'good' : 'warn'} />
              <ModeChip label="Total run" value={latestDailyRun ? `${latestDailyRun.accepted_patterns + latestDailyRun.rejected_patterns}` : '0'} tone="warn" />
            </ScopeDivider>
            <ResearchPatternPanel
              title="Research Daily"
              subtitle="Patrones daily detectados y aceptados. La lista queda en tabla con scroll; el gráfico solo aparece en detalle."
              patterns={dailyPatternRows}
              selectedPatternId={selectedDailyPatternId}
              onSelectPattern={setSelectedDailyPatternId}
              latestRun={latestDailyRun}
              latestCompletedRun={latestCompletedDailyRun}
              discoveryRunsCount={dailyRuns.length}
            />
          </>
        )}

        {activeTab === 'laboratory' && (
          <>
            <ScopeDivider label="Laboratorio" title="Intradía">
              <ModeChip
                label="Paper"
                value={intradayStatus ? intradayModeLabel(intradayStatus.config.paper_enabled) : 'cargando'}
                tone={intradayStatus ? intradayModeTone(intradayStatus.config.paper_enabled) : 'warn'}
              />
              <ModeChip label="Activas" value={`${labIntradayOverview?.stats.open_trades ?? 0}`} tone="good" />
              <ModeChip label="Cerradas" value={`${labIntradayOverview?.stats.closed_trades ?? 0}`} tone="warn" />
            </ScopeDivider>
            <OperationsModule
              title="Lab Intradía"
              subtitle="Órdenes paper intradía activas y P/L acumulado de fills intradía cerrados."
              overview={labIntradayOverview}
              status={labStatus}
            />

            <ScopeDivider label="Laboratorio" title="Daily">
              <ModeChip label="Paper" value={labStatus?.paper_orders_allowed ? 'permitido' : 'bloqueado'} tone={labStatus?.paper_orders_allowed ? 'good' : 'warn'} />
              <ModeChip label="Activas" value={`${labDailyOverview?.stats.open_trades ?? 0}`} tone="good" />
              <ModeChip label="Cerradas" value={`${labDailyOverview?.stats.closed_trades ?? 0}`} tone="warn" />
            </ScopeDivider>
            <OperationsModule
              title="Lab Daily"
              subtitle="Órdenes paper diarias activas y P/L acumulado de fills daily cerrados."
              overview={labDailyOverview}
              status={labStatus}
            />
          </>
        )}

        {activeTab === 'fox_hunter' && (
          <>
            <ScopeDivider label="Fox Hunter" title="Intradía">
              <ModeChip
                label="Live"
                value={intradayStatus ? intradayModeLabel(intradayStatus.config.live_enabled, intradayStatus.config.live_armed) : 'cargando'}
                tone={intradayStatus ? intradayModeTone(intradayStatus.config.live_enabled, intradayStatus.config.live_armed) : 'warn'}
              />
              <ModeChip label="Activas" value={`${foxIntradayOverview?.stats.open_trades ?? 0}`} tone="good" />
              <ModeChip label="Cerradas" value={`${foxIntradayOverview?.stats.closed_trades ?? 0}`} tone="warn" />
            </ScopeDivider>
            <OperationsModule
              title="Fox Intradía"
              subtitle="Órdenes live intradía activas y P/L acumulado de operaciones intradía cerradas."
              overview={foxIntradayOverview}
              status={foxStatus}
            />

            <ScopeDivider label="Fox Hunter" title="Daily">
              <ModeChip label="Live" value={data.live_armed ? 'armado' : 'bloqueado'} tone={data.live_armed ? 'good' : 'warn'} />
              <ModeChip label="Activas" value={`${foxDailyOverview?.stats.open_trades ?? 0}`} tone="good" />
              <ModeChip label="Cerradas" value={`${foxDailyOverview?.stats.closed_trades ?? 0}`} tone="warn" />
            </ScopeDivider>
            <OperationsModule
              title="Fox Daily"
              subtitle="Órdenes live daily activas y P/L acumulado de operaciones daily cerradas."
              overview={foxDailyOverview}
              status={foxStatus}
            />
          </>
        )}

      </section>
    </main>
  )
}
