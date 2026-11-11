import React from 'react'
import { Terminal, RefreshCw, XCircle, CheckCircle, Clock, AlertTriangle, Ban } from 'lucide-react'
import type { Job, JobStatus } from '../types'
import { cancelJob } from '../api'

interface JobQueueViewProps {
  jobs: Job[]
  selectedJobId: string | null
  onSelectJob: (jobId: string) => void
  onRefresh: () => void
  onCancelJob?: (jobId: string) => void
}

export const JobQueueView: React.FC<JobQueueViewProps> = ({
  jobs,
  selectedJobId,
  onSelectJob,
  onRefresh,
  onCancelJob,
}) => {
  const [cancelling, setCancelling] = React.useState<string | null>(null)
  const [liveLogs, setLiveLogs] = React.useState<string[]>([])
  const terminalRef = React.useRef<HTMLDivElement>(null)

  const activeJob = jobs.find((j) => j.job_id === selectedJobId) || jobs[0] || null

  // Connect WebSocket to active job
  React.useEffect(() => {
    if (!activeJob) {
      setLiveLogs([])
      return
    }

    setLiveLogs(activeJob.logs || [])

    const wsUrl = `ws://${window.location.host}/ws/jobs/${activeJob.job_id}`
    let ws: WebSocket | null = null

    try {
      ws = new WebSocket(wsUrl)
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'job_log' && data.log) {
            setLiveLogs((prev) => [...prev, data.log])
          } else if (data.type === 'job_snapshot' && data.job) {
            setLiveLogs(data.job.logs || [])
          } else if (
            data.type === 'job_cancelled' ||
            data.type === 'job_completed' ||
            data.type === 'job_failed'
          ) {
            onRefresh()
          }
        } catch {
          // ignore keep-alive
        }
      }
    } catch {
      // fallback
    }

    return () => {
      if (ws) ws.close()
    }
  }, [activeJob?.job_id])

  // Auto-scroll terminal
  React.useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [liveLogs])

  const handleCancel = async (jobId: string) => {
    setCancelling(jobId)
    const timeStr = new Date().toLocaleTimeString()
    setLiveLogs((prev) => [
      ...prev,
      `[${timeStr}] Cancellation requested by user. Terminating active tasks...`,
    ])
    if (onCancelJob) {
      onCancelJob(jobId)
    }
    try {
      await cancelJob(jobId)
      onRefresh()
    } catch (err) {
      alert(`Could not cancel job: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setCancelling(null)
    }
  }

  const renderStatusBadge = (status: JobStatus) => {
    switch (status) {
      case 'completed':
        return (
          <span className="stage-badge stage-done" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <CheckCircle size={12} /> Completed
          </span>
        )
      case 'running':
        return (
          <span className="stage-badge stage-pending" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <RefreshCw size={12} className="animate-spin" /> Running
          </span>
        )
      case 'queued':
        return (
          <span className="stage-badge stage-missing" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={12} /> Queued
          </span>
        )
      case 'cancelled':
        return (
          <span className="stage-badge stage-missing" style={{ color: 'var(--danger)', borderColor: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Ban size={12} /> Cancelled
          </span>
        )
      case 'failed':
      default:
        return (
          <span className="stage-badge" style={{ background: 'var(--danger-bg)', color: 'var(--danger)', borderColor: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <AlertTriangle size={12} /> Failed
          </span>
        )
    }
  }

  return (
    <section style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) 2fr', gap: '20px' }} aria-label="Job queue and worker console">
      {/* Jobs List */}
      <div className="card">
        <div className="card-title">
          <span>Job queue ({jobs.length})</span>
          <button className="btn btn-outline btn-sm" onClick={onRefresh}>
            <RefreshCw size={13} />
            <span>Refresh</span>
          </button>
        </div>

        {jobs.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '30px' }}>
            No jobs queued yet. Select a script from the catalog to start a job.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {jobs.map((job) => {
              const isSelected = activeJob?.job_id === job.job_id
              const canCancel = job.status === 'queued' || job.status === 'running'

              return (
                <div
                  key={job.job_id}
                  onClick={() => onSelectJob(job.job_id)}
                  style={{
                    background: isSelected ? 'var(--bg-card-hover)' : 'var(--bg-input)',
                    border: `1px solid ${isSelected ? 'var(--border-focus)' : 'var(--border)'}`,
                    borderRadius: '8px',
                    padding: '12px',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <strong style={{ fontSize: '14px', color: 'var(--text-main)' }}>
                      #{job.job_id} — {job.stage.charAt(0).toUpperCase() + job.stage.slice(1).toLowerCase()}
                    </strong>
                    {renderStatusBadge(job.status)}
                  </div>

                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                    Scripts: {job.script_ids.join(', ')}
                  </div>

                  {/* Progress Bar */}
                  {job.progress && job.progress.total > 0 && (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)', marginBottom: '2px' }}>
                        <span>Progress:</span>
                        <span>{job.progress.current} / {job.progress.total}</span>
                      </div>
                      <div className="vram-bar">
                        <div
                          className="vram-fill"
                          style={{
                            width: `${Math.round((job.progress.current / job.progress.total) * 100)}%`,
                            backgroundColor: job.status === 'failed' ? 'var(--danger)' : 'var(--accent)',
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {canCancel && (
                    <div style={{ marginTop: '10px', textAlign: 'right' }}>
                      <button
                        className="btn btn-danger btn-sm"
                        disabled={cancelling === job.job_id}
                        onClick={(e) => {
                          e.stopPropagation()
                          handleCancel(job.job_id)
                        }}
                      >
                        <XCircle size={12} />
                        <span>Cancel</span>
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Live Terminal Console */}
      <div className="card">
        <div className="card-title">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={18} className="icon-accent" />
            <span>
              Live worker console {activeJob ? `(#${activeJob.job_id} · ${activeJob.stage.toLowerCase()})` : ''}
            </span>
          </div>
        </div>

        <div className="terminal-window" ref={terminalRef}>
          {liveLogs.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
              Worker standby. Live task logs will stream here automatically.
            </div>
          ) : (
            liveLogs.map((line, idx) => {
              const isErr = line.includes('ERROR') || line.includes('FAILED') || line.includes('EXCEPTION')
              return (
                <div key={idx} className={`terminal-line ${isErr ? 'error' : ''}`}>
                  {line}
                </div>
              )
            })
          )}
        </div>
      </div>
    </section>
  )
}

