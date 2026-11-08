import React from 'react'
import { RefreshCw } from 'lucide-react'
import type { ScriptSummary, StageState } from '../types'

interface ScriptListProps {
  scripts: ScriptSummary[]
  loading: boolean
  onSelectScript: (scriptId: string) => void
  onRefresh: () => void
}

export const ScriptList: React.FC<ScriptListProps> = ({
  scripts,
  loading,
  onSelectScript,
  onRefresh,
}) => {
  const [searchTerm, setSearchTerm] = React.useState('')
  const [langFilter, setLangFilter] = React.useState('all')
  const [statusFilter, setStatusFilter] = React.useState('all')

  const filtered = scripts.filter((s) => {
    const sid = s.script_id || (s as any).id || ''
    const topic = s.topic || ''
    const matchesSearch =
      sid.toLowerCase().includes(searchTerm.toLowerCase()) ||
      topic.toLowerCase().includes(searchTerm.toLowerCase())

    const lang = s.language || ''
    const matchesLang = langFilter === 'all' || lang.toLowerCase() === langFilter.toLowerCase()

    let matchesStatus = true
    const stages = s.stages || ({} as any)
    if (statusFilter === 'ready_for_assembly') {
      matchesStatus = stages.voice === 'done' && stages.images === 'done' && stages.assembly !== 'done'
    } else if (statusFilter === 'complete') {
      matchesStatus = stages.assembly === 'done'
    } else if (statusFilter === 'missing_images') {
      matchesStatus = stages.images !== 'done'
    } else if (statusFilter === 'missing_voice') {
      matchesStatus = stages.voice !== 'done'
    }

    return matchesSearch && matchesLang && matchesStatus
  })

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

  return (
    <div className="card">
      <div className="card-title">
        <span>Script Library ({filtered.length} of {scripts.length})</span>
        <button className="btn btn-outline btn-sm" onClick={onRefresh} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="toolbar">
        <input
          type="text"
          className="search-input"
          placeholder="Search by ID (e.g. SE37) or topic..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />

        <select
          className="select-filter"
          value={langFilter}
          onChange={(e) => setLangFilter(e.target.value)}
        >
          <option value="all">All Languages</option>
          <option value="spanish">Spanish</option>
          <option value="french">French</option>
          <option value="english">English</option>
        </select>

        <select
          className="select-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="all">All Stages</option>
          <option value="missing_voice">Needs Voice (Stage B)</option>
          <option value="missing_images">Needs Images (Stage C)</option>
          <option value="ready_for_assembly">Ready for Assembly (Stage G)</option>
          <option value="complete">Completed Videos</option>
        </select>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table className="scripts-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Topic</th>
              <th>Language / Type</th>
              <th>Character</th>
              <th>Pipeline Progress (A-B-C-D-F-G)</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '32px' }}>
                  {loading ? 'Loading scripts...' : 'No matching scripts found.'}
                </td>
              </tr>
            ) : (
              filtered.map((s) => {
                const sid = s.script_id || (s as any).id || ''
                const stages = s.stages || ({} as any)
                return (
                  <tr key={sid} onClick={() => onSelectScript(sid)}>
                    <td>
                      <strong style={{ color: 'var(--accent)' }}>{sid}</strong>
                    </td>
                    <td>{s.topic || '—'}</td>
                    <td>
                      <span style={{ textTransform: 'capitalize' }}>{s.language || '—'}</span> / {s.type || (s as any).video_type || '—'}
                    </td>
                    <td>
                      <span style={{ textTransform: 'capitalize' }}>
                        {s.character?.gender || 'Default'}
                      </span>
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
                          onSelectScript(sid)
                        }}
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
