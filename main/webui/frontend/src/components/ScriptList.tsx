import React, { useState, useEffect, useCallback } from 'react'
import {
  RefreshCw,
  LayoutGrid,
  List,
  CheckSquare,
  Square,
  Image as ImageIcon,
  Mic,
  Film,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  X
} from 'lucide-react'
import type { ScriptSummary, ScriptFacets, StageState, JobStage } from '../types'
import { fetchScriptCatalog, getMediaUrl, createJob, refreshScriptCache } from '../api'

interface ScriptListProps {
  onSelectScript: (scriptId: string) => void
  onJobStarted: (jobId: string) => void
}

export const ScriptList: React.FC<ScriptListProps> = ({
  onSelectScript,
  onJobStarted,
}) => {
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid')
  const [loading, setLoading] = useState(false)
  const [scripts, setScripts] = useState<ScriptSummary[]>([])
  const [facets, setFacets] = useState<ScriptFacets | null>(null)

  // Filters & Pagination State
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedLang, setSelectedLang] = useState('all')
  const [selectedType, setSelectedType] = useState('all')
  const [stageFilter, setStageFilter] = useState('all')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(24)
  const [totalCount, setTotalCount] = useState(0)
  const [totalPages, setTotalPages] = useState(1)

  // Multi-selection state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [batchActionLoading, setBatchActionLoading] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const resp = await fetchScriptCatalog({
        page,
        pageSize,
        search: searchTerm,
        language: selectedLang,
        videoType: selectedType,
        stageFilter: stageFilter,
      })
      const rawList = Array.isArray(resp) ? resp : (resp?.items || [])
      const total = Array.isArray(resp) ? resp.length : (resp?.total ?? rawList.length)
      const pages = Array.isArray(resp) ? Math.max(1, Math.ceil(total / pageSize)) : (resp?.total_pages ?? 1)
      setScripts(rawList)
      setTotalCount(total)
      setTotalPages(pages)
      if (!Array.isArray(resp) && resp?.facets) setFacets(resp.facets)
    } catch (err) {
      console.error('Failed to load script catalog:', err)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, searchTerm, selectedLang, selectedType, stageFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Debounced search reset to page 1
  const handleSearchChange = (val: string) => {
    setSearchTerm(val)
    setPage(1)
  }

  const handleRefresh = async () => {
    setLoading(true)
    try {
      await refreshScriptCache()
      await loadData()
    } catch (err) {
      console.error('Cache refresh failed:', err)
    } finally {
      setLoading(false)
    }
  }

  // Selection handlers
  const toggleSelect = (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectPage = () => {
    const pageIds = scripts.map((s) => s.script_id)
    const allSelected = pageIds.every((id) => selectedIds.has(id))
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (allSelected) {
        pageIds.forEach((id) => next.delete(id))
      } else {
        pageIds.forEach((id) => next.add(id))
      }
      return next
    })
  }

  const clearSelection = () => {
    setSelectedIds(new Set())
  }

  // Trigger batch job
  const handleBatchRun = async (stage: JobStage) => {
    if (selectedIds.size === 0) return
    const ids = Array.from(selectedIds)
    setBatchActionLoading(stage)
    try {
      const job = await createJob(stage, ids)
      clearSelection()
      onJobStarted(job.job_id)
    } catch (err) {
      alert(`Batch job failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setBatchActionLoading(null)
    }
  }

  const renderBadge = (label: string, state?: StageState) => {
    let cls = 'stage-missing'
    if (state === 'done') cls = 'stage-done'
    else if (state === 'pending') cls = 'stage-pending'

    return (
      <span key={label} className={`stage-badge ${cls}`} title={`${label}: ${state || 'missing'}`}>
        {label}
      </span>
    )
  }

  const isPageAllSelected = scripts.length > 0 && scripts.every((s) => selectedIds.has(s.script_id))

  return (
    <div className="card" style={{ position: 'relative' }}>
      {/* Title & View Switcher */}
      <div className="card-title">
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span>Script Library ({totalCount.toLocaleString()} Total)</span>
          <div className="btn-group">
            <button
              className={`btn btn-sm ${viewMode === 'grid' ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setViewMode('grid')}
              title="Card Grid View"
            >
              <LayoutGrid size={14} />
              <span>Cards</span>
            </button>
            <button
              className={`btn btn-sm ${viewMode === 'table' ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setViewMode('table')}
              title="Table View"
            >
              <List size={14} />
              <span>Table</span>
            </button>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button className="btn btn-outline btn-sm" onClick={handleRefresh} disabled={loading} title="Re-scan state files">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Sync</span>
          </button>
        </div>
      </div>

      {/* Dynamic Filter Toolbar */}
      <div className="toolbar">
        <input
          type="text"
          className="search-input"
          placeholder="Search 1,200+ scripts by ID, topic, title, scenario..."
          value={searchTerm}
          onChange={(e) => handleSearchChange(e.target.value)}
        />

        {/* Dynamic Languages */}
        <select
          className="select-filter"
          value={selectedLang}
          onChange={(e) => {
            setSelectedLang(e.target.value)
            setPage(1)
          }}
        >
          <option value="all">All Languages ({facets?.total ?? totalCount})</option>
          {(facets?.languages || []).map((l) => (
            <option key={l.name} value={l.name}>
              {l.name} ({l.count})
            </option>
          ))}
        </select>

        {/* Dynamic Video Types */}
        <select
          className="select-filter"
          value={selectedType}
          onChange={(e) => {
            setSelectedType(e.target.value)
            setPage(1)
          }}
        >
          <option value="all">All Formats</option>
          {(facets?.types || []).map((t) => (
            <option key={t.name} value={t.name}>
              {t.name.toUpperCase()} ({t.count})
            </option>
          ))}
        </select>

        {/* Pipeline Stage Status Filter */}
        <select
          className="select-filter"
          value={stageFilter}
          onChange={(e) => {
            setStageFilter(e.target.value)
            setPage(1)
          }}
        >
          <option value="all">All Statuses</option>
          <option value="missing_voice">
            Needs Voice ({facets?.stage_counts?.missing_voice ?? 0})
          </option>
          <option value="missing_images">
            Needs Images ({facets?.stage_counts?.missing_images ?? 0})
          </option>
          <option value="ready_for_assembly">
            Ready for Assembly ({facets?.stage_counts?.ready_for_assembly ?? 0})
          </option>
          <option value="complete">
            Complete ({facets?.stage_counts?.complete ?? 0})
          </option>
        </select>

        {/* Select All on Page Button */}
        <button className="btn btn-outline btn-sm" onClick={toggleSelectPage}>
          {isPageAllSelected ? <CheckSquare size={14} /> : <Square size={14} />}
          <span>{isPageAllSelected ? 'Deselect Page' : 'Select Page'}</span>
        </button>
      </div>

      {/* Main Content: Grid vs Table */}
      {loading && scripts.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          <RefreshCw size={24} className="animate-spin" style={{ margin: '0 auto 12px auto' }} />
          <div>Scanning script library...</div>
        </div>
      ) : scripts.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          No scripts matching current filters. Try adjusting search or filters.
        </div>
      ) : viewMode === 'grid' ? (
        /* Visual Card Grid View */
        <div className="cards-grid">
          {scripts.map((s) => {
            const isSelected = selectedIds.has(s.script_id)
            const stages = s.stages || ({} as any)
            const posterUrl = s.assets?.poster ? getMediaUrl(s.assets.poster) : null

            return (
              <div
                key={s.script_id}
                className={`script-card ${isSelected ? 'selected' : ''}`}
                onClick={() => onSelectScript(s.script_id)}
              >
                {/* Poster Box */}
                <div className="card-poster">
                  <div
                    className={`card-select-btn ${isSelected ? 'active' : ''}`}
                    onClick={(e) => toggleSelect(s.script_id, e)}
                    title={isSelected ? 'Deselect script' : 'Select script'}
                  >
                    {isSelected ? <CheckSquare size={14} /> : null}
                  </div>

                  {posterUrl ? (
                    <img src={posterUrl} alt={s.script_id} loading="lazy" />
                  ) : (
                    <div className="card-poster-placeholder">
                      <ImageIcon size={28} />
                      <span>No Visual Yet</span>
                    </div>
                  )}

                  <div className="card-badges-overlay">
                    <span className="brand-badge">{s.type.toUpperCase()}</span>
                    <span
                      style={{
                        background: 'rgba(0,0,0,0.7)',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: 600,
                        textTransform: 'capitalize',
                      }}
                    >
                      {s.language}
                    </span>
                  </div>
                </div>

                {/* Card Info */}
                <div className="card-info">
                  <div className="card-id-row">
                    <strong style={{ color: 'var(--accent)', fontSize: '14px' }}>{s.script_id}</strong>
                    <div className="stage-badges">
                      {renderBadge('B', stages.voice)}
                      {renderBadge('C', stages.images)}
                      {renderBadge('G', stages.assembly)}
                    </div>
                  </div>

                  <div className="card-title-text" title={s.topic}>
                    {s.title || s.topic}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        /* Dense Table View */
        <div style={{ overflowX: 'auto' }}>
          <table className="scripts-table">
            <thead>
              <tr>
                <th style={{ width: '40px' }}>
                  <input
                    type="checkbox"
                    checked={isPageAllSelected}
                    onChange={toggleSelectPage}
                    style={{ cursor: 'pointer' }}
                  />
                </th>
                <th>ID</th>
                <th>Topic / Title</th>
                <th>Language / Format</th>
                <th>Character</th>
                <th>Pipeline (A-B-C-D-F-G)</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {scripts.map((s) => {
                const isSelected = selectedIds.has(s.script_id)
                const stages = s.stages || ({} as any)
                return (
                  <tr
                    key={s.script_id}
                    onClick={() => onSelectScript(s.script_id)}
                    style={{ background: isSelected ? 'var(--bg-card-hover)' : undefined }}
                  >
                    <td onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(s.script_id)}
                        style={{ cursor: 'pointer' }}
                      />
                    </td>
                    <td>
                      <strong style={{ color: 'var(--accent)' }}>{s.script_id}</strong>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{s.title || s.topic}</div>
                      {s.lexical_field && (
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{s.lexical_field}</div>
                      )}
                    </td>
                    <td>
                      <span style={{ textTransform: 'capitalize' }}>{s.language}</span> /{' '}
                      <span className="brand-badge" style={{ fontSize: '10px' }}>
                        {s.type.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span style={{ textTransform: 'capitalize' }}>{s.character?.gender || 'Default'}</span>
                    </td>
                    <td>
                      <div className="stage-badges">
                        {renderBadge('A', stages.scripts || 'missing')}
                        {renderBadge('B', stages.voice || 'missing')}
                        {renderBadge('C', stages.images || 'missing')}
                        {renderBadge('D', stages.music || 'missing')}
                        {renderBadge('F', stages.thumbnails || 'missing')}
                        {renderBadge('G', stages.assembly || 'missing')}
                      </div>
                    </td>
                    <td>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={(e) => {
                          e.stopPropagation()
                          onSelectScript(s.script_id)
                        }}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Footer Bar */}
      <div className="pagination-bar">
        <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Showing {Math.min((page - 1) * pageSize + 1, totalCount)}–{Math.min(page * pageSize, totalCount)} of{' '}
          {totalCount.toLocaleString()} scripts
        </div>

        <div className="pagination-controls">
          <select
            className="select-filter"
            style={{ padding: '4px 8px', fontSize: '12px' }}
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value))
              setPage(1)
            }}
          >
            <option value={12}>12 per page</option>
            <option value={24}>24 per page</option>
            <option value={48}>48 per page</option>
            <option value={96}>96 per page</option>
          </select>

          <button
            className="page-btn"
            disabled={page <= 1}
            onClick={() => setPage(1)}
            title="First page"
          >
            «
          </button>
          <button
            className="page-btn"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            title="Previous page"
          >
            <ChevronLeft size={16} />
          </button>

          <span style={{ padding: '0 8px', fontSize: '13px', fontWeight: 600 }}>
            Page {page} of {totalPages}
          </span>

          <button
            className="page-btn"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            title="Next page"
          >
            <ChevronRight size={16} />
          </button>
          <button
            className="page-btn"
            disabled={page >= totalPages}
            onClick={() => setPage(totalPages)}
            title="Last page"
          >
            »
          </button>
        </div>
      </div>

      {/* Floating Bottom Batch Action Bar */}
      {selectedIds.size > 0 && (
        <div className="floating-batch-bar">
          <div className="batch-counter">
            {selectedIds.size} Script{selectedIds.size > 1 ? 's' : ''} Selected
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn btn-outline btn-sm"
              disabled={batchActionLoading !== null}
              onClick={() => handleBatchRun('voice')}
              title="Generate Voice for selected scripts"
            >
              <Mic size={13} />
              <span>Voice (B)</span>
            </button>

            <button
              className="btn btn-outline btn-sm"
              disabled={batchActionLoading !== null}
              onClick={() => handleBatchRun('images')}
              title="Generate Scene Images for selected scripts"
            >
              <ImageIcon size={13} />
              <span>Images (C)</span>
            </button>

            <button
              className="btn btn-outline btn-sm"
              disabled={batchActionLoading !== null}
              onClick={() => handleBatchRun('thumbnails')}
              title="Generate Chalkboard Thumbnails for selected scripts"
            >
              <Sparkles size={13} />
              <span>Thumbnails (F)</span>
            </button>

            <button
              className="btn btn-primary btn-sm"
              disabled={batchActionLoading !== null}
              onClick={() => handleBatchRun('assembly')}
              title="Assemble Final Short Videos for selected scripts"
            >
              <Film size={13} />
              <span>Assemble (G)</span>
            </button>
          </div>

          <button
            className="btn btn-outline btn-sm"
            onClick={clearSelection}
            title="Clear selection"
            style={{ padding: '4px 6px' }}
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  )
}
