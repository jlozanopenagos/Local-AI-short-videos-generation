import React, { useState, useEffect, useCallback } from 'react'
import {
  X,
  Image as ImageIcon,
  Mic,
  Film,
  Sparkles,
  Copy,
  Check
} from 'lucide-react'
import type { ScriptDetail, JobStage } from '../types'
import { fetchScriptDetail, getMediaUrl, createJob } from '../api'

interface ScriptDetailModalProps {
  scriptId: string
  onClose: () => void
  onJobStarted: (jobId: string) => void
}

export const ScriptDetailModal: React.FC<ScriptDetailModalProps> = ({
  scriptId,
  onClose,
  onJobStarted,
}) => {
  const [detail, setDetail] = useState<ScriptDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'storyboard' | 'overview' | 'youtube' | 'media'>('storyboard')
  const [triggeringStage, setTriggeringStage] = useState<string | null>(null)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchScriptDetail(scriptId)
      setDetail(data)
    } catch (err) {
      alert(`Failed to load script ${scriptId}: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setLoading(false)
    }
  }, [scriptId])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleRunStage = async (stage: JobStage) => {
    setTriggeringStage(stage)
    try {
      const job = await createJob(stage, [scriptId])
      onJobStarted(job.job_id)
      onClose()
    } catch (err) {
      alert(`Could not start ${stage}: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setTriggeringStage(null)
    }
  }

  const copyToClipboard = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>
          <X size={20} />
        </button>

        {loading || !detail ? (
          <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
            Loading script data for {scriptId}...
          </div>
        ) : (
          <div>
            {/* Header info */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
              <h2 style={{ fontSize: '20px', fontWeight: 700 }}>
                <span style={{ color: 'var(--accent)' }}>[{detail.script_id}]</span> {detail.title || detail.topic}
              </h2>
              <span className="brand-badge" style={{ textTransform: 'uppercase' }}>
                {detail.language} / {detail.type}
              </span>
            </div>

            {/* Pipeline Stage Action Bar */}
            <div
              style={{
                display: 'flex',
                gap: '8px',
                flexWrap: 'wrap',
                background: 'var(--bg-input)',
                padding: '12px',
                borderRadius: '8px',
                marginBottom: '20px',
                border: '1px solid var(--border)',
                alignItems: 'center',
              }}
            >
              <span style={{ fontSize: '13px', fontWeight: 600, marginRight: '4px' }}>
                Run Pipeline:
              </span>
              <button
                className={`btn btn-sm ${detail.stages.voice === 'done' ? 'btn-outline' : 'btn-primary'}`}
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('voice')}
              >
                <Mic size={13} />
                <span>Voice (B) {detail.stages.voice === 'done' ? '✓' : ''}</span>
              </button>
              <button
                className={`btn btn-sm ${detail.stages.images === 'done' ? 'btn-outline' : 'btn-primary'}`}
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('images')}
              >
                <ImageIcon size={13} />
                <span>Images (C) {detail.stages.images === 'done' ? '✓' : ''}</span>
              </button>
              <button
                className={`btn btn-sm ${detail.stages.thumbnails === 'done' ? 'btn-outline' : 'btn-primary'}`}
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('thumbnails')}
              >
                <Sparkles size={13} />
                <span>Thumbnail (F) {detail.stages.thumbnails === 'done' ? '✓' : ''}</span>
              </button>
              <button
                className={`btn btn-sm ${detail.stages.assembly === 'done' ? 'btn-outline' : 'btn-success'}`}
                disabled={triggeringStage !== null}
                onClick={() => handleRunStage('assembly')}
              >
                <Film size={13} />
                <span>Assemble (G) {detail.stages.assembly === 'done' ? '✓' : ''}</span>
              </button>
            </div>

            {/* Navigation Tabs */}
            <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '16px' }}>
              <button
                className={`nav-btn ${activeTab === 'storyboard' ? 'active' : ''}`}
                onClick={() => setActiveTab('storyboard')}
              >
                Storyboard Scenes ({(detail.scenes || []).length})
              </button>
              <button
                className={`nav-btn ${activeTab === 'overview' ? 'active' : ''}`}
                onClick={() => setActiveTab('overview')}
              >
                Story & Character
              </button>
              <button
                className={`nav-btn ${activeTab === 'youtube' ? 'active' : ''}`}
                onClick={() => setActiveTab('youtube')}
              >
                YouTube Metadata
              </button>
              <button
                className={`nav-btn ${activeTab === 'media' ? 'active' : ''}`}
                onClick={() => setActiveTab('media')}
              >
                Media Players
              </button>
            </div>

            {/* Tab: Storyboard */}
            {activeTab === 'storyboard' && (
              <div>
                {detail.general_prompt && (
                  <div style={{ marginBottom: '16px', background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: '8px', padding: '12px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent)', marginBottom: '4px' }}>
                      GENERAL SCENE ANCHOR PROMPT
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
                      {detail.general_prompt}
                    </div>
                  </div>
                )}

                {(detail.scenes || []).map((sc, idx) => {
                  const imgUrl = sc.image_file ? getMediaUrl(sc.image_file) : null
                  return (
                    <div key={idx} className="storyboard-card">
                      <div className="storyboard-thumb">
                        {imgUrl ? (
                          <a href={imgUrl} target="_blank" rel="noreferrer" title="Click to view full image">
                            <img src={imgUrl} alt={sc.scene_type} loading="lazy" />
                          </a>
                        ) : (
                          <div style={{ color: 'var(--text-muted)', fontSize: '11px', textAlign: 'center', padding: '8px' }}>
                            <ImageIcon size={22} style={{ margin: '0 auto 4px auto' }} />
                            <div>Pending Render</div>
                          </div>
                        )}
                      </div>

                      <div className="storyboard-body">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span className="brand-badge">{sc.label || sc.scene_type}</span>
                          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Scene {idx + 1}</span>
                        </div>

                        <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-main)', marginTop: '2px' }}>
                          "{sc.voice_line}"
                        </div>

                        {sc.prompt && (
                          <div style={{ background: 'var(--bg-main)', border: '1px solid var(--border)', borderRadius: '6px', padding: '8px', marginTop: '6px' }}>
                            <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '2px' }}>
                              ComfyUI Prompt:
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontStyle: 'italic', maxHeight: '80px', overflowY: 'auto' }}>
                              {sc.prompt}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            )}

            {/* Tab: Overview */}
            {activeTab === 'overview' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '14px' }}>
                <div>
                  <strong style={{ color: 'var(--text-muted)' }}>Story Scenario:</strong>
                  <p style={{ marginTop: '4px', background: 'var(--bg-input)', padding: '10px', borderRadius: '6px' }}>
                    {detail.story_scenario || 'Not configured yet.'}
                  </p>
                </div>

                <div>
                  <strong style={{ color: 'var(--text-muted)' }}>Base Setting:</strong>
                  <p style={{ marginTop: '4px', background: 'var(--bg-input)', padding: '10px', borderRadius: '6px' }}>
                    {detail.base_setting || 'Not configured yet.'}
                  </p>
                </div>

                <div>
                  <strong style={{ color: 'var(--text-muted)' }}>Character & Voices:</strong>
                  <div style={{ marginTop: '4px', background: 'var(--bg-input)', padding: '12px', borderRadius: '6px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div><strong>Gender:</strong> {detail.character?.gender || 'Default'}</div>
                    {detail.speakers_voice && (
                      <div style={{ marginTop: '6px' }}>
                        <strong style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Assigned Audio Models:</strong>
                        {Object.entries(detail.speakers_voice).map(([spk, voice]) => (
                          <div key={spk} style={{ fontSize: '12px', marginTop: '2px' }}>
                            • <strong>{spk}</strong>: {voice}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Tab: YouTube Metadata */}
            {activeTab === 'youtube' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {detail.youtube_metadata ? (
                  <>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <strong style={{ fontSize: '13px', color: 'var(--text-muted)' }}>YouTube Video Title:</strong>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(detail.youtube_metadata?.title || '', 'title')}
                        >
                          {copiedKey === 'title' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
                          <span>{copiedKey === 'title' ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                      <input
                        type="text"
                        readOnly
                        value={detail.youtube_metadata.title}
                        className="search-input"
                        style={{ width: '100%' }}
                      />
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <strong style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Description:</strong>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(detail.youtube_metadata?.description || '', 'desc')}
                        >
                          {copiedKey === 'desc' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
                          <span>{copiedKey === 'desc' ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                      <textarea
                        readOnly
                        rows={4}
                        value={detail.youtube_metadata.description}
                        className="search-input"
                        style={{ width: '100%', resize: 'vertical' }}
                      />
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <strong style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Tags (comma-separated):</strong>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(detail.youtube_metadata?.tags || '', 'tags')}
                        >
                          {copiedKey === 'tags' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
                          <span>{copiedKey === 'tags' ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                      <input
                        type="text"
                        readOnly
                        value={detail.youtube_metadata.tags}
                        className="search-input"
                        style={{ width: '100%' }}
                      />
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                        <strong style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Hashtags:</strong>
                        <button
                          className="copy-btn"
                          onClick={() => copyToClipboard(detail.youtube_metadata?.hashtags || '', 'hashtags')}
                        >
                          {copiedKey === 'hashtags' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />}
                          <span>{copiedKey === 'hashtags' ? 'Copied' : 'Copy'}</span>
                        </button>
                      </div>
                      <input
                        type="text"
                        readOnly
                        value={detail.youtube_metadata.hashtags}
                        className="search-input"
                        style={{ width: '100%' }}
                      />
                    </div>
                  </>
                ) : (
                  <div style={{ color: 'var(--text-muted)' }}>No YouTube metadata found for this script.</div>
                )}
              </div>
            )}

            {/* Tab: Media Players */}
            {activeTab === 'media' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {detail.assets?.audio ? (
                  <div>
                    <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Master Voice Audio</h4>
                    <audio controls style={{ width: '100%' }} src={getMediaUrl(detail.assets.audio)} />
                  </div>
                ) : (
                  <div style={{ color: 'var(--text-muted)', fontSize: '13px' }}>No voice generated yet.</div>
                )}

                {detail.assets?.video && (
                  <div>
                    <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Final Short Video</h4>
                    <video controls style={{ maxWidth: '320px', borderRadius: '8px', border: '1px solid var(--border)' }} src={getMediaUrl(detail.assets.video)} />
                  </div>
                )}

                {detail.assets?.thumbnail && (
                  <div>
                    <h4 style={{ fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Chalkboard Thumbnail</h4>
                    <img
                      src={getMediaUrl(detail.assets.thumbnail)}
                      alt="Thumbnail"
                      style={{ maxWidth: '240px', borderRadius: '8px', border: '1px solid var(--border)' }}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
