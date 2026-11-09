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
} from 'lucide-react'
import type { SheetsSyncStatus, SheetsSyncRecord } from '../types'
import { fetchSheetsSyncStatus, startSheetsSync, resetSheetsSyncStatus } from '../api'

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
    <div className="sheets-sync-container">
      {/* View Header */}
      <div className="sheets-sync-header">
        <div className="sheets-title-group">
          <div className="sheets-icon-wrap">
            <FileSpreadsheet size={28} className="text-emerald-400" />
          </div>
          <div>
            <h1 className="sheets-title">Handle Googlesheets changes</h1>
            <p className="sheets-subtitle">
              Fetch script modifications from Google Sheets (Column D: SCRIPT_CHANGED), purge cached CSVs, and update
              local State JSON files with automatic downstream reset.
            </p>
          </div>
        </div>

        {isCompleted && (
          <button className="btn btn-secondary btn-sm" onClick={handleReset}>
            <RefreshCw size={14} />
            <span>Reset Status</span>
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
          <span>Synchronization failed: {syncStatus?.error || 'Unknown error occurred during sync.'}</span>
        </div>
      )}

      {/* Control Panel Card */}
      <div className="sheets-control-card">
        <div className="control-options">
          <label className="checkbox-label" title="Deletes all CSVs in input/csv/script_to_change/ before fetching">
            <input
              type="checkbox"
              checked={cleanCache}
              onChange={(e) => setCleanCache(e.target.checked)}
              disabled={isRunning}
            />
            <span className="checkbox-text">
              <strong>Purge cached CSVs in <code>script_to_change/</code> before fetch</strong>
              <span className="checkbox-hint">
                (Recommended: deletes stale CSV files so Google Sheets changes are cleanly refreshed at every run)
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
            <span>{isRunning ? 'Synchronizing with Sheets...' : 'Fetch & Update All JSON States'}</span>
          </button>

          <button
            className="btn btn-secondary"
            disabled={isRunning}
            onClick={() => handleStartSync(false)}
            title="Fetches and checks differences without modifying local State JSONs"
          >
            <Info size={16} />
            <span>Audit / Preview Only</span>
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

      {/* Summary Stat Cards */}
      {result && (
        <div className="sheets-stats-grid">
          <div className="stat-card">
            <div className="stat-label">
              <Trash2 size={16} className="text-amber-400" />
              <span>Purged CSVs</span>
            </div>
            <div className="stat-val">{result.purged_csvs?.length || 0}</div>
            <div className="stat-sub">Stale files cleaned</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">
              <FileSpreadsheet size={16} className="text-blue-400" />
              <span>Sheets Fetched</span>
            </div>
            <div className="stat-val">{result.fetched_files?.length || 0}</div>
            <div className="stat-sub">{result.total_fetched || 0} scripts with corrections</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">
              <Sparkles size={16} className="text-purple-400" />
              <span>Changes Detected</span>
            </div>
            <div className="stat-val">{result.changed_count || 0}</div>
            <div className="stat-sub">Differs from local state</div>
          </div>

          <div className="stat-card highlight">
            <div className="stat-label">
              <CheckCircle2 size={16} className="text-emerald-400" />
              <span>States Updated</span>
            </div>
            <div className="stat-val text-emerald-400">{result.updated_count || 0}</div>
            <div className="stat-sub">Downstream stages reset</div>
          </div>

          <div className="stat-card">
            <div className="stat-label">
              <CheckCircle2 size={16} className="text-slate-400" />
              <span>Already In Sync</span>
            </div>
            <div className="stat-val">{result.identical_count || 0}</div>
            <div className="stat-sub">No modifications needed</div>
          </div>
        </div>
      )}

      {/* Updated Scripts Section */}
      {result && result.updated_records && result.updated_records.length > 0 && (
        <div className="sheets-section">
          <div className="section-header">
            <h2>Detected & Updated Scripts ({result.updated_records.length})</h2>
            <span className="section-badge">
              {result.updated_count > 0 ? `${result.updated_count} States Overwritten` : 'Audit Mode'}
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
                      <span className="word-delta-tag" title="Word count comparison">
                        {rec.words_current}w &rarr; {rec.words_new}w
                        <strong className="delta-pill">{rec.delta_words}</strong>
                      </span>

                      <span className={`status-pill ${rec.status}`}>
                        {rec.status === 'updated' ? 'Updated & Reset' : rec.status === 'failed' ? 'Failed' : 'Pending'}
                      </span>

                      <button
                        className="btn btn-icon btn-sm"
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
                        <span>Changes Preview (diff)</span>
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
          <CheckCircle2 size={20} className="text-emerald-400" />
          <div>
            <strong>100% Synchronized!</strong>
            <p>All scripts in your local State JSONs are already completely in sync with Google Sheets.</p>
          </div>
        </div>
      )}

      {/* Execution Logs Terminal */}
      <div className="sheets-terminal-card">
        <div className="terminal-header">
          <div className="terminal-title">
            <Terminal size={16} />
            <span>Execution Console</span>
            {isRunning && <span className="running-tag">RUNNING</span>}
          </div>
          <div className="terminal-actions">
            <label className="autoscroll-toggle">
              <input
                type="checkbox"
                checked={autoScrollLogs}
                onChange={(e) => setAutoScrollLogs(e.target.checked)}
              />
              <span>Auto-scroll</span>
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
              Ready to sync. Click "Fetch & Update All JSON States" above to run the pipeline.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
