import React, { useState, useEffect, useMemo } from 'react'
import {
  CheckCircle2,
  RefreshCw,
  Search,
  Filter,
  Sparkles,
  Layers,
  ArrowRight,
  Film,
  Music,
  Image as ImageIcon,
  FileText
} from 'lucide-react'
import type { ScriptSummary } from '../types'
import { fetchScripts, refreshScriptCache } from '../api'

export type BingoColor = 'grey' | 'red' | 'yellow' | 'orange' | 'green'

const LANGUAGES = [
  { id: 'all', label: 'all languages', flag: '🌐' },
  { id: 'english', label: 'English', flag: '🇬🇧' },
  { id: 'french', label: 'French', flag: '🇫🇷' },
  { id: 'spanish', label: 'Spanish', flag: '🇪🇸' },
  { id: 'italian', label: 'Italian', flag: '🇮🇹' },
] as const

const VIDEO_TYPES = [
  { id: 'all', label: 'all formats', code: 'ALL' },
  { id: 'expression', label: 'expression', code: 'E' },
  { id: 'game', label: 'game', code: 'G' },
  { id: 'roleplay', label: 'roleplay', code: 'R' },
  { id: 'fun_facts', label: 'fun facts', code: 'F' },
] as const

interface BingoMatrixViewProps {
  onSelectScript: (scriptId: string) => void
}

export function calculateBingoStatus(s: ScriptSummary): BingoColor {
  const hasVoice = Boolean(s.has_voice || s.stages?.voice === 'done' || s.assets?.audio)
  const hasImages = Boolean(
    s.has_images || s.stages?.images === 'done' || (s.assets?.images && s.assets.images.length > 0)
  )
  const hasThumbnail = Boolean(
    s.has_thumbnail || s.stages?.thumbnails === 'done' || s.assets?.thumbnail
  )
  const hasVideo = Boolean(
    s.has_video || s.stages?.assembly === 'done' || s.assets?.video
  )

  // 5-Color Progression:
  // 1. Green: All previous done + final video assembled
  if (hasVoice && hasImages && hasThumbnail && hasVideo) return 'green'
  // 2. Orange: Script + voice + images + thumbnail done (video pending)
  if (hasVoice && hasImages && hasThumbnail) return 'orange'
  // 3. Yellow: Script + voice + images done (thumbnail pending)
  if (hasVoice && hasImages) return 'yellow'
  // 4. Red: Script + voice done (images pending)
  if (hasVoice) return 'red'
  // 5. Grey: Only script exists (voice pending)
  return 'grey'
}

export const BingoMatrixView: React.FC<BingoMatrixViewProps> = ({ onSelectScript }) => {
  const [scripts, setScripts] = useState<ScriptSummary[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false)

  // Filters
  const [selectedLanguage, setSelectedLanguage] = useState<string>('all')
  const [selectedType, setSelectedType] = useState<string>('all')
  const [filterColor, setFilterColor] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState<string>('')

  // Active / selected tile for quick preview card
  const [activeScriptId, setActiveScriptId] = useState<string | null>(null)

  const loadData = async (forceDiskScan = false) => {
    if (forceDiskScan) {
      setIsRefreshing(true)
      try {
        await refreshScriptCache()
      } catch (err) {
        console.error('Failed to refresh cache:', err)
      }
    } else {
      setIsLoading(true)
    }

    try {
      const data = await fetchScripts()
      if (Array.isArray(data)) {
        setScripts(data)
      }
    } catch (err) {
      console.error('Failed to load scripts for bingo matrix:', err)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // Augmented scripts with computed 5-color status
  const matrixItems = useMemo(() => {
    return scripts.map((s) => ({
      ...s,
      bingoStatus: calculateBingoStatus(s),
    }))
  }, [scripts])

  // Filtered list
  const filteredItems = useMemo(() => {
    return matrixItems.filter((item) => {
      // Language filter
      if (selectedLanguage !== 'all' && item.language.toLowerCase() !== selectedLanguage.toLowerCase()) {
        return false
      }

      // Video Type filter
      if (selectedType !== 'all') {
        const itemType = (item.type || item.video_type || '').toLowerCase()
        if (itemType !== selectedType.toLowerCase()) return false
      }

      // Color stage filter
      if (filterColor !== 'all' && item.bingoStatus !== filterColor) {
        return false
      }

      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.trim().toLowerCase()
        const idMatch = (item.script_id || item.id || '').toLowerCase().includes(q)
        const topicMatch = (item.topic || item.title || '').toLowerCase().includes(q)
        if (!idMatch && !topicMatch) return false
      }

      return true
    })
  }, [matrixItems, selectedLanguage, selectedType, filterColor, searchQuery])

  // Global statistics across current filtered scope or total
  const stats = useMemo(() => {
    const total = matrixItems.length
    const greenCount = matrixItems.filter((i) => i.bingoStatus === 'green').length
    const orangeCount = matrixItems.filter((i) => i.bingoStatus === 'orange').length
    const yellowCount = matrixItems.filter((i) => i.bingoStatus === 'yellow').length
    const redCount = matrixItems.filter((i) => i.bingoStatus === 'red').length
    const greyCount = matrixItems.filter((i) => i.bingoStatus === 'grey').length

    const greenPct = total > 0 ? Math.round((greenCount / total) * 1000) / 10 : 0
    const orangePct = total > 0 ? Math.round((orangeCount / total) * 1000) / 10 : 0
    const yellowPct = total > 0 ? Math.round((yellowCount / total) * 1000) / 10 : 0
    const redPct = total > 0 ? Math.round((redCount / total) * 1000) / 10 : 0
    const greyPct = total > 0 ? Math.round((greyCount / total) * 1000) / 10 : 0

    return {
      total,
      greenCount,
      orangeCount,
      yellowCount,
      redCount,
      greyCount,
      greenPct,
      orangePct,
      yellowPct,
      redPct,
      greyPct,
    }
  }, [matrixItems])

  const activeScript = useMemo(() => {
    if (!activeScriptId) return null
    return matrixItems.find((i) => i.id === activeScriptId || i.script_id === activeScriptId) || null
  }, [matrixItems, activeScriptId])

  return (
    <div className="bingo-matrix-container animate-fadeIn">
      {/* Header Banner */}
      <div className="bingo-header-card">
        <div className="bingo-header-top">
          <div>
            <div className="home-hero-badge">
              <Sparkles size={13} />
              <span>asset pipeline visual radar</span>
            </div>
            <h1 className="bingo-title">asset bingo matrix</h1>
            <p className="bingo-subtitle">
              interactive 5-stage asset completion grid across all 1,225+ scripts. color states are determined
              purely from verified local disk assets.
            </p>
          </div>

          <button
            type="button"
            className="btn btn-outline btn-sm"
            onClick={() => loadData(true)}
            disabled={isRefreshing || isLoading}
            title="scan state files on disk to refresh asset properties"
          >
            <RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />
            <span>{isRefreshing ? 'scanning disk...' : 'refresh state'}</span>
          </button>
        </div>

        {/* Language & Format Pickers */}
        <div className="bingo-controls-bar">
          {/* Languages */}
          <div className="bingo-picker-group">
            <span className="bingo-picker-label">language:</span>
            <div className="bingo-pill-group">
              {LANGUAGES.map((lang) => (
                <button
                  key={lang.id}
                  type="button"
                  onClick={() => setSelectedLanguage(lang.id)}
                  className={`bingo-pill-btn ${selectedLanguage === lang.id ? 'active' : ''}`}
                >
                  <span>{lang.flag}</span>
                  <span>{lang.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Formats */}
          <div className="bingo-picker-group">
            <span className="bingo-picker-label">format:</span>
            <div className="bingo-pill-group">
              {VIDEO_TYPES.map((vtype) => (
                <button
                  key={vtype.id}
                  type="button"
                  onClick={() => setSelectedType(vtype.id)}
                  className={`bingo-pill-btn ${selectedType === vtype.id ? 'active' : ''}`}
                >
                  <span>{vtype.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 5-Stage Metrics & Multi-Segment Progress Dashboard */}
      <div className="bingo-metrics-card">
        <div className="bingo-stats-row">
          {/* Total */}
          <div className="bingo-stat-item">
            <span className="bingo-stat-label">total IDs</span>
            <span className="bingo-stat-value">{stats.total}</span>
          </div>

          <div className="bingo-stat-divider" />

          {/* Green: Final Video */}
          <div className="bingo-stat-item">
            <span className="bingo-stat-label" style={{ color: 'var(--success)' }}>
              <CheckCircle2 size={13} />
              <span>green (video)</span>
            </span>
            <div className="bingo-stat-num-wrap">
              <span className="bingo-stat-value" style={{ color: 'var(--success)' }}>{stats.greenCount}</span>
              <span className="bingo-stat-pct">({stats.greenPct}%)</span>
            </div>
            <span className="bingo-stat-sub">complete assembled video</span>
          </div>

          <div className="bingo-stat-divider" />

          {/* Orange: Thumbnail Done */}
          <div className="bingo-stat-item">
            <span className="bingo-stat-label" style={{ color: '#fb923c' }}>
              <ImageIcon size={13} />
              <span>orange (thumbnail)</span>
            </span>
            <div className="bingo-stat-num-wrap">
              <span className="bingo-stat-value" style={{ color: '#fb923c' }}>{stats.orangeCount}</span>
              <span className="bingo-stat-pct">({stats.orangePct}%)</span>
            </div>
            <span className="bingo-stat-sub">+ thumbnail ready</span>
          </div>

          <div className="bingo-stat-divider" />

          {/* Yellow: Images Done */}
          <div className="bingo-stat-item">
            <span className="bingo-stat-label" style={{ color: '#facc15' }}>
              <Layers size={13} />
              <span>yellow (images)</span>
            </span>
            <div className="bingo-stat-num-wrap">
              <span className="bingo-stat-value" style={{ color: '#facc15' }}>{stats.yellowCount}</span>
              <span className="bingo-stat-pct">({stats.yellowPct}%)</span>
            </div>
            <span className="bingo-stat-sub">+ scene images ready</span>
          </div>

          <div className="bingo-stat-divider" />

          {/* Red: Voices Done */}
          <div className="bingo-stat-item">
            <span className="bingo-stat-label" style={{ color: '#f43f5e' }}>
              <Music size={13} />
              <span>red (voices)</span>
            </span>
            <div className="bingo-stat-num-wrap">
              <span className="bingo-stat-value" style={{ color: '#f43f5e' }}>{stats.redCount}</span>
              <span className="bingo-stat-pct">({stats.redPct}%)</span>
            </div>
            <span className="bingo-stat-sub">+ voice audio ready</span>
          </div>

          <div className="bingo-stat-divider" />

          {/* Grey: Script Only */}
          <div className="bingo-stat-item">
            <span className="bingo-stat-label" style={{ color: 'var(--text-muted)' }}>
              <FileText size={13} />
              <span>grey (script)</span>
            </span>
            <div className="bingo-stat-num-wrap">
              <span className="bingo-stat-value" style={{ color: 'var(--text-muted)' }}>{stats.greyCount}</span>
              <span className="bingo-stat-pct">({stats.greyPct}%)</span>
            </div>
            <span className="bingo-stat-sub">voices pending</span>
          </div>
        </div>

        {/* 5-Color Segmented Progress Bar */}
        <div className="bingo-progress-wrap">
          <div className="bingo-progress-labels">
            <span className="bingo-progress-title">studio production health</span>
            <span className="bingo-progress-summary">
              {stats.greenCount + stats.orangeCount + stats.yellowCount + stats.redCount} of {stats.total} assets initiated
            </span>
          </div>

          <div className="bingo-multibar" role="progressbar" aria-valuenow={stats.greenPct} aria-valuemin={0} aria-valuemax={100}>
            {/* Green Segment */}
            <div
              className="bingo-bar-segment bingo-bar-green"
              style={{ width: `${stats.greenPct}%` }}
              title={`Green (Video): ${stats.greenCount} (${stats.greenPct}%)`}
            />
            {/* Orange Segment */}
            <div
              className="bingo-bar-segment bingo-bar-orange"
              style={{ width: `${stats.orangePct}%` }}
              title={`Orange (Thumbnail): ${stats.orangeCount} (${stats.orangePct}%)`}
            />
            {/* Yellow Segment */}
            <div
              className="bingo-bar-segment bingo-bar-yellow"
              style={{ width: `${stats.yellowPct}%` }}
              title={`Yellow (Images): ${stats.yellowCount} (${stats.yellowPct}%)`}
            />
            {/* Red Segment */}
            <div
              className="bingo-bar-segment bingo-bar-red"
              style={{ width: `${stats.redPct}%` }}
              title={`Red (Voices): ${stats.redCount} (${stats.redPct}%)`}
            />
            {/* Grey Segment */}
            <div
              className="bingo-bar-segment bingo-bar-grey"
              style={{ width: `${stats.greyPct}%` }}
              title={`Grey (Script only): ${stats.greyCount} (${stats.greyPct}%)`}
            />
          </div>
        </div>
      </div>

      {/* Filter Pills & Instant Search */}
      <div className="bingo-filter-search-row">
        {/* Color Filters */}
        <div className="bingo-filter-pills">
          <button
            type="button"
            onClick={() => setFilterColor('all')}
            className={`bingo-filter-btn ${filterColor === 'all' ? 'active' : ''}`}
          >
            all IDs ({filteredItems.length})
          </button>
          <button
            type="button"
            onClick={() => setFilterColor('green')}
            className={`bingo-filter-btn ${filterColor === 'green' ? 'active green' : ''}`}
          >
            <span className="dot dot-green" />
            <span>green ({stats.greenCount})</span>
          </button>
          <button
            type="button"
            onClick={() => setFilterColor('orange')}
            className={`bingo-filter-btn ${filterColor === 'orange' ? 'active orange' : ''}`}
          >
            <span className="dot dot-orange" />
            <span>orange ({stats.orangeCount})</span>
          </button>
          <button
            type="button"
            onClick={() => setFilterColor('yellow')}
            className={`bingo-filter-btn ${filterColor === 'yellow' ? 'active yellow' : ''}`}
          >
            <span className="dot dot-yellow" />
            <span>yellow ({stats.yellowCount})</span>
          </button>
          <button
            type="button"
            onClick={() => setFilterColor('red')}
            className={`bingo-filter-btn ${filterColor === 'red' ? 'active red' : ''}`}
          >
            <span className="dot dot-red" />
            <span>red ({stats.redCount})</span>
          </button>
          <button
            type="button"
            onClick={() => setFilterColor('grey')}
            className={`bingo-filter-btn ${filterColor === 'grey' ? 'active grey' : ''}`}
          >
            <span className="dot dot-grey" />
            <span>grey ({stats.greyCount})</span>
          </button>
        </div>

        {/* Quick Search */}
        <div className="bingo-search-box">
          <Search size={14} className="bingo-search-icon" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="search by ID (e.g. EE01) or topic..."
            className="bingo-search-input mono-font"
          />
        </div>
      </div>

      {/* Quick Inspection Card (Active Script Tile) */}
      {activeScript && (
        <div className="bingo-inspector-card animate-slideDown">
          <div className="bingo-inspector-left">
            <div className={`bingo-inspector-badge status-${activeScript.bingoStatus}`}>
              {activeScript.script_id || activeScript.id}
            </div>

            <div className="bingo-inspector-info">
              <div className="bingo-inspector-title-row">
                <span className="bingo-inspector-topic">{activeScript.topic || activeScript.title || 'untitled script'}</span>
                <span className={`bingo-stage-tag stage-${activeScript.bingoStatus}`}>
                  {activeScript.bingoStatus === 'green' && 'stage 5: final video done'}
                  {activeScript.bingoStatus === 'orange' && 'stage 4: thumbnail done'}
                  {activeScript.bingoStatus === 'yellow' && 'stage 3: images done'}
                  {activeScript.bingoStatus === 'red' && 'stage 2: voices done'}
                  {activeScript.bingoStatus === 'grey' && 'stage 1: script only'}
                </span>
              </div>

              {/* Asset Breakdown Chips */}
              <div className="bingo-inspector-assets">
                <span className={`asset-chip ${activeScript.has_voice ? 'done' : 'missing'}`}>
                  <Music size={11} />
                  <span>voice: {activeScript.has_voice ? '✓' : '✗'}</span>
                </span>
                <span className={`asset-chip ${activeScript.has_images ? 'done' : 'missing'}`}>
                  <ImageIcon size={11} />
                  <span>images: {activeScript.has_images ? '✓' : '✗'}</span>
                </span>
                <span className={`asset-chip ${activeScript.has_thumbnail ? 'done' : 'missing'}`}>
                  <Layers size={11} />
                  <span>thumbnail: {activeScript.has_thumbnail ? '✓' : '✗'}</span>
                </span>
                <span className={`asset-chip ${activeScript.has_video ? 'done' : 'missing'}`}>
                  <Film size={11} />
                  <span>video: {activeScript.has_video ? '✓' : '✗'}</span>
                </span>
              </div>
            </div>
          </div>

          <div className="bingo-inspector-right">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => onSelectScript(activeScript.script_id || activeScript.id)}
            >
              <span>open script studio</span>
              <ArrowRight size={13} />
            </button>
          </div>
        </div>
      )}

      {/* Main Bingo Grid */}
      <div className="bingo-grid-wrapper">
        {isLoading ? (
          <div className="bingo-loading-state">
            <RefreshCw size={28} className="animate-spin" />
            <p className="bingo-loading-text">loading script pipeline states...</p>
            <p className="bingo-loading-sub">scanning 1,225+ local state documents</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="bingo-empty-state">
            <Filter size={28} />
            <p className="bingo-empty-text">no script IDs match this filter</p>
            <p className="bingo-empty-sub">try adjusting the language, format, or search term</p>
          </div>
        ) : (
          <div className="bingo-grid">
            {filteredItems.map((item) => {
              const id = item.script_id || item.id
              const isSelected = activeScriptId === id
              const status = item.bingoStatus

              return (
                <div
                  key={id}
                  title={`${id}: ${item.topic || 'no topic'}\nstatus: ${status}\n(click to inspect · double-click to open studio)`}
                  onClick={() => setActiveScriptId(isSelected ? null : id)}
                  onDoubleClick={() => onSelectScript(id)}
                  className={`bingo-tile status-${status} ${isSelected ? 'selected' : ''}`}
                >
                  {/* ID Code ONLY */}
                  <span className="bingo-tile-id">{id}</span>

                  {/* Subtle Status Mini Dot */}
                  <span className={`bingo-tile-dot dot-${status}`} />
                </div>
              );
            })}
          </div>
        )}

        {/* Legend Footer */}
        <div className="bingo-legend-footer">
          <div className="bingo-legend-items">
            <span className="legend-item">
              <span className="legend-dot" style={{ background: 'var(--success)' }} />
              <strong>green:</strong> video assembled
            </span>
            <span className="legend-item">
              <span className="legend-dot" style={{ background: '#fb923c' }} />
              <strong>orange:</strong> + thumbnail done
            </span>
            <span className="legend-item">
              <span className="legend-dot" style={{ background: '#facc15' }} />
              <strong>yellow:</strong> + images done
            </span>
            <span className="legend-item">
              <span className="legend-dot" style={{ background: '#f43f5e' }} />
              <strong>red:</strong> + voice done
            </span>
            <span className="legend-item">
              <span className="legend-dot" style={{ background: 'var(--border)' }} />
              <strong>grey:</strong> script only
            </span>
          </div>

          <div className="bingo-legend-tip">
            <Sparkles size={13} />
            <span>click to inspect · double-click to open script studio</span>
          </div>
        </div>
      </div>
    </div>
  )
}
