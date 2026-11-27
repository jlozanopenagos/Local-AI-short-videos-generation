import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  FileSpreadsheet,
  RefreshCw,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Terminal,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Info,
  Image as ImageIcon,
} from 'lucide-react'
import type { SheetsSyncStatus, SheetsSyncRecord } from '../types'
import { fetchSheetsSyncStatus, startSheetsSync, startThumbnailTitlesSync, resetSheetsSyncStatus } from '../api'

interface GoogleSheetsSyncViewProps {
  onSelectScript: (scriptId: string) => void
}

export const GoogleSheetsSyncView: React.FC<GoogleSheetsSyncViewProps> = ({ onSelectScript }) => {
  const [syncStatus, setSyncStatus] = useState<SheetsSyncStatus | null>(null)
  const [cleanCache, setCleanCache] = useState(true)
  const [isStarting, setIsStarting] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [expandedDiffs, setExpandedDiffs] = useState<Record<string, boolean>>({})
  const [autoScrollLogs, setAutoScrollLogs] = useState(true)

  const logContainerRef = useRef<HTMLDivElement>(null)

  // Poll status while running or periodically
  const loadStatus = useCallback(async () => {
    try {
      const data = await fetchSheetsSyncStatus()
      setSyncStatus(data)
      if (data.status === 'completed' || data.status === 'failed') {
        setIsStarting(false)
      }
    } catch (err) {
      console.error('Error fetching sheets status:', err)
    }
  }, [])

  useEffect(() => {
    loadStatus()
    const timer = setInterval(() => {
      loadStatus()
    }, syncStatus?.status === 'running' || isStarting ? 800 : 3000)
    return () => clearInterval(timer)
  }, [loadStatus, syncStatus?.status, isStarting])

  // Auto-scroll logs to bottom when new logs arrive
  useEffect(() => {
    if (autoScrollLogs && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [syncStatus?.logs, autoScrollLogs])

  const handleStartSync = async (applyChanges: boolean) => {
    setErrorMsg(null)
    setIsStarting(true)
    try {
      await startSheetsSync({ clean_cache: cleanCache, apply_changes: applyChanges })
      await loadStatus()
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err))
      setIsStarting(false)
    }
  }

  const handleStartThumbnailTitlesSync = async (applyChanges: boolean) => {
    setErrorMsg(null)
    setIsStarting(true)
    try {
      await startThumbnailTitlesSync({ apply_changes: applyChanges })
      await loadStatus()
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err))
      setIsStarting(false)
    }
  }

  const handleReset = async () => {
    try {
      await resetSheetsSyncStatus()
      await loadStatus()
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : String(err))
    }
  }

  const toggleDiff = (id: string) => {
    setExpandedDiffs((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const isRunning = syncStatus?.status === 'running' || isStarting
  const isCompleted = syncStatus?.status === 'completed'
  const isFailed = syncStatus?.status === 'failed'
  const result = syncStatus?.result

  return (
    <section className="sheets-sync-container" aria-label="Google Sheets synchronization">
      {/* View Header */}
      <div className="sheets-sync-header">
        <div className="sheets-title-group">
          <div className="sheets-icon-wrap">
            <FileSpreadsheet size={28} className="icon-success" />
          </div>
          <div>
            <h1 className="sheets-title">Google Sheets synchronization</h1>
            <p className="sheets-subtitle">
              Fetch script modifications (Column D: SCRIPT_CHANGED) and thumbnail titles (Column J: short_title /
              THUMBNAIL_TITLE) from Google Sheets, and update local JSON state files cleanly.
            </p>
          </div>
        </div>

        {isCompleted && (
          <button className="btn btn-outline btn-sm" onClick={handleReset}>
            <RefreshCw size={14} />
            <span>reset status</span>
          </button>
        )}
      </div>

      {errorMsg && (
        <div className="sheets-alert error">
          <AlertTriangle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {isFailed && (
        <div className="sheets-alert error">
          <AlertTriangle size={18} />
          <span>synchronization failed: {syncStatus?.error || 'unknown error occurred during sync.'}</span>
        </div>
      )}

      {/* Control Panel Card */}
      <div className="sheets-control-card">
        <div className="control-options">
          <label className="checkbox-label" title="deletes all CSVs in input/csv/script_to_change/ before fetching">
            <input
              type="checkbox"
              checked={cleanCache}
              onChange={(e) => setCleanCache(e.target.checked)}
              disabled={isRunning}
            />
            <span className="checkbox-text">
              <strong>purge cached CSVs in <code>script_to_change/</code> before fetch</strong>
              <span className="checkbox-hint">
                (recommended: deletes stale CSV files so Google Sheets changes are cleanly refreshed at every run)
              </span>
            </span>
          </label>
        </div>

        <div className="control-actions">
          <button
            className="btn btn-primary btn-lg"
            disabled={isRunning}
            onClick={() => handleStartSync(true)}
          >
            <RefreshCw size={18} className={isRunning ? 'spin' : ''} />
            <span>{isRunning ? 'synchronizing with Google Sheets...' : 'fetch & update all JSON states'}</span>
          </button>

          <button
            className="btn btn-outline"
            disabled={isRunning}
            onClick={() => handleStartSync(false)}
            title="fetches and checks differences without modifying local JSON states"
          >
            <Info size={16} />
            <span>audit / preview only</span>
          </button>
        </div>

        {/* Live Progress Bar when Running */}
        {isRunning && (
          <div className="sheets-progress-box">
            <div className="progress-info">
              <span className="step-label">
                <span className="pulse-dot" />
                {syncStatus?.current_step || 'Processing Google Sheets synchronization...'}
              </span>
              <span className="progress-pct">{syncStatus?.progress || 10}%</span>
            </div>
            <div className="progress-bar-bg">
              <div
                className="progress-bar-fill"
                style={{ width: `${Math.max(syncStatus?.progress || 10, 8)}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Thumbnail Titles Sync Card (Column J) */}
      <div className="sheets-control-card">
        <div className="control-options">
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
            <ImageIcon size={20} className="icon-accent" style={{ marginTop: '2px', flexShrink: 0 }} />
            <div>
              <strong>Thumbnail titles sync (Column J)</strong>
              <p className="checkbox-hint" style={{ margin: '4px 0 0 0', display: 'block' }}>
                Fetches custom thumbnail titles from Column J across all 16 Google Sheets and updates{' '}
                <code>content_metadata.thumbnail_title</code> in your local JSON states. Only resets{' '}
                <code>thumbnail_generation</code> to <em>pending</em> (never touches voice, scene images, or video assembly).
              </p>
            </div>
          </div>
        </div>

        <div className="control-actions">
          <button
            className="btn btn-primary"
            disabled={isRunning}
            onClick={() => handleStartThumbnailTitlesSync(true)}
          >
            <Sparkles size={16} className={isRunning ? 'spin' : ''} />
            <span>{isRunning ? 'synchronizing...' : 'fetch & update thumbnail titles (col J)'}</span>
          </button>

          <button
            className="btn btn-outline"
            disabled={isRunning}
            onClick={() => handleStartThumbnailTitlesSync(false)}
            title="fetches Column J and previews thumbnail title differences without modifying local JSON states"
          >
            <Info size={16} />
            <span>preview thumbnail titles only</span>
          </button>
        </div>
      </div>

      {/* Summary Stat Cards */}
      {result && (
        <div className="sheets-stats-grid">
          <div className="stat-card">
            <div className="stat-label">
              <Trash2 size={16} className="icon-warning" />
              <span>purged CSVs</span>
            </div>
            <div className="stat-val">{result.purged_csvs?.length || 0}</div>
            <div className="stat-sub">stale files cleaned</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">
              <FileSpreadsheet size={16} className="icon-accent" />
              <span>sheets fetched</span>
            </div>
            <div className="stat-val">{result.fetched_files?.length || 0}</div>
            <div className="stat-sub">{result.total_fetched || 0} scripts with corrections</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">
              <Sparkles size={16} className="icon-sand" />
              <span>changes detected</span>
            </div>
            <div className="stat-val">{result.changed_count || 0}</div>
            <div className="stat-sub">differs from local state</div>
          </div>

          <div className="stat-card highlight">
            <div className="stat-label">
              <CheckCircle2 size={16} className="icon-success" />
              <span>states updated</span>
            </div>
            <div className="stat-val icon-success">{result.updated_count || 0}</div>
            <div className="stat-sub">downstream stages reset</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">
              <CheckCircle2 size={16} className="icon-muted" />
              <span>already in sync</span>
            </div>
            <div className="stat-val">{result.identical_count || 0}</div>
            <div className="stat-sub">no modifications needed</div>
          </div>
        </div>
      )}

      {/* Updated Scripts Section */}
      {result && result.updated_records && result.updated_records.length > 0 && (
        <div className="sheets-section">
          <div className="section-header">
            <h2>detected & updated scripts ({result.updated_records.length})</h2>
            <span className="section-badge">
              {result.updated_count > 0 ? `${result.updated_count} states overwritten` : 'audit mode'}
            </span>
          </div>

          <div className="updated-scripts-list">
            {result.updated_records.map((rec: SheetsSyncRecord) => {
              const isExpanded = Boolean(expandedDiffs[rec.id])
              return (
                <div key={rec.id} className="script-update-card">
                  <div className="card-top">
                    <div className="script-meta-left">
                      <button
                        className="script-id-badge clickable"
                        onClick={() => onSelectScript(rec.id)}
                        title={`Open details for ${rec.id}`}
                      >
                        <span>{rec.id}</span>
                        <ExternalLink size={12} />
                      </button>
                      <span className="script-file-tag">{rec.file}</span>
                    </div>

                    <div className="script-meta-right">
                      {result.sync_mode === 'thumbnails' && rec.new_title ? (
                        <span className="word-delta-tag" title="New thumbnail title from Column J">
                          &ldquo;{rec.new_title}&rdquo;
                        </span>
                      ) : (
                        <span className="word-delta-tag" title="Word count comparison">
                          {rec.words_current}w &rarr; {rec.words_new}w
                          <strong className="delta-pill">{rec.delta_words}</strong>
                        </span>
                      )}

                      <span className={`status-pill ${rec.status}`}>
                        {rec.status === 'updated'
                          ? result.sync_mode === 'thumbnails'
                            ? 'Title updated'
                            : 'Updated & reset'
                          : rec.status === 'failed'
                            ? 'Failed'
                            : 'Pending'}
                      </span>

                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => toggleDiff(rec.id)}
                        title={isExpanded ? 'Hide diff preview' : 'View diff preview'}
                      >
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </button>
                    </div>
                  </div>

                  {/* Diff Snippet Preview */}
                  {isExpanded && rec.diff_preview && (
                    <div className="diff-preview-container">
                      <div className="diff-header">
                        <FileText size={14} />
                        <span>changes preview (diff)</span>
                      </div>
                      <pre className="diff-code">{rec.diff_preview}</pre>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* All In Sync Notice */}
      {result && result.changed_count === 0 && (
        <div className="sheets-alert success">
          <CheckCircle2 size={20} className="icon-success" />
          <div>
            <strong>100% synchronized</strong>
            <p>all scripts in your local JSON states are already completely in sync with Google Sheets.</p>
          </div>
        </div>
      )}

      {/* Execution Logs Terminal */}
      <div className="sheets-terminal-card">
        <div className="terminal-header">
          <div className="terminal-title">
            <Terminal size={16} />
            <span>execution console</span>
            {isRunning && <span className="running-tag">running</span>}
          </div>
          <div className="terminal-actions">
            <label className="autoscroll-toggle">
              <input
                type="checkbox"
                checked={autoScrollLogs}
                onChange={(e) => setAutoScrollLogs(e.target.checked)}
              />
              <span>auto-scroll</span>
            </label>
          </div>
        </div>

        <div className="terminal-body" ref={logContainerRef}>
          {syncStatus?.logs && syncStatus.logs.length > 0 ? (
            syncStatus.logs.map((line, idx) => (
              <div key={idx} className="terminal-line">
                {line}
              </div>
            ))
          ) : (
            <div className="terminal-placeholder">
              Ready to sync. Click "Fetch & update all JSON states" above to run the pipeline.
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
