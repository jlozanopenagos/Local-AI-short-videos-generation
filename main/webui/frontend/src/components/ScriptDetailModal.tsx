import React, { useState, useEffect, useCallback } from 'react'
import {
  X,
  Image as ImageIcon,
  Mic,
  Film,
  Sparkles,
  Copy,
  Check,
  Save,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Code,
  Edit3
} from 'lucide-react'
import type { ScriptDetail, JobStage } from '../types'
import { fetchScriptDetail, getMediaUrl, createJob, updateScript } from '../api'

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

  // Script & Chalkboard editor local state
  const [chalkboardTitle, setChalkboardTitle] = useState('')
  const [chalkboardExercise, setChalkboardExercise] = useState('')
  const [scriptFields, setScriptFields] = useState<Record<string, string>>({})
  const [jsonMode, setJsonMode] = useState(false)
  const [rawJsonText, setRawJsonText] = useState('')
  const [savingScript, setSavingScript] = useState(false)
  const [saveStatus, setSaveStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const populateEditorState = (data: ScriptDetail) => {
    const titleVal = data.chalkboard_title || data.target_expression || data.title || ''
    setChalkboardTitle(titleVal)
    setChalkboardExercise(data.chalkboard_exercise || '')

    let sDict: Record<string, any> = {}
    if (data.script_dict && Object.keys(data.script_dict).length > 0) {
      sDict = { ...data.script_dict }
    } else if (data.script_text) {
      try {
        const parsed = JSON.parse(data.script_text)
        if (typeof parsed === 'object' && parsed !== null) {
          sDict = parsed
        }
      } catch {
        sDict = { script_text: data.script_text }
      }
    }
    setScriptFields(sDict)
    setRawJsonText(JSON.stringify(sDict, null, 2))
  }

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchScriptDetail(scriptId)
      setDetail(data)
      populateEditorState(data)
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

  const handleFieldChange = (key: string, value: string) => {
    const updated = { ...scriptFields, [key]: value }
    setScriptFields(updated)
    setRawJsonText(JSON.stringify(updated, null, 2))
  }

  const handleSaveScriptAndChalkboard = async () => {
    setSavingScript(true)
    setSaveStatus(null)
    try {
      let finalScriptDict: Record<string, any> = scriptFields
      let finalScriptText: string = rawJsonText

      if (jsonMode) {
        try {
          finalScriptDict = JSON.parse(rawJsonText)
          finalScriptText = rawJsonText
        } catch {
          setSaveStatus({
            type: 'error',
            message: 'Invalid JSON syntax. Please verify and correct your JSON before saving.',
          })
          setSavingScript(false)
          return
        }
      } else {
        finalScriptText = JSON.stringify(finalScriptDict, null, 2)
      }

      const updated = await updateScript(scriptId, {
        chalkboard_title: chalkboardTitle,
        target_expression: chalkboardTitle,
        chalkboard_exercise: chalkboardExercise,
        script_dict: finalScriptDict,
        script_text: finalScriptText,
      })

      setDetail(updated)
      populateEditorState(updated)
      setSaveStatus({
        type: 'success',
        message: '✓ Saved! Script and Chalkboard state updated on disk.',
      })

      setTimeout(() => {
        setSaveStatus(null)
      }, 4000)
    } catch (err) {
      setSaveStatus({
        type: 'error',
        message: err instanceof Error ? err.message : String(err),
      })
    } finally {
      setSavingScript(false)
    }
  }

  const handleResetEditor = () => {
    if (detail) {
      populateEditorState(detail)
      setSaveStatus(null)
    }
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
                Script & Chalkboard
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

            {/* Tab: Script & Chalkboard (Editable) */}
            {activeTab === 'overview' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* Save Feedback Banner */}
                {saveStatus && (
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      padding: '10px 14px',
                      borderRadius: '6px',
                      background: saveStatus.type === 'success' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                      border: `1px solid ${saveStatus.type === 'success' ? 'var(--success)' : 'var(--danger, #ef4444)'}`,
                      color: saveStatus.type === 'success' ? 'var(--success)' : '#f87171',
                      fontSize: '13px',
                      fontWeight: 500,
                    }}
                  >
                    {saveStatus.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                    <span>{saveStatus.message}</span>
                  </div>
                )}

                {/* Action Bar */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                    Edit the script dialogues and chalkboard content below. Changes persist directly into the script's JSON state file.
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline"
                      onClick={handleResetEditor}
                      disabled={savingScript}
                      title="Discard unsaved changes and reload from state"
                    >
                      <RefreshCw size={13} />
                      <span>Reset</span>
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-primary"
                      onClick={handleSaveScriptAndChalkboard}
                      disabled={savingScript}
                    >
                      <Save size={13} />
                      <span>{savingScript ? 'Saving to JSON...' : 'Save Changes to State'}</span>
                    </button>
                  </div>
                </div>

                {/* Section 1: Chalkboard Content */}
                <div
                  style={{
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Chalkboard Content (Image Definition)
                    </div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Used for thumbnail & Scene 2 chalkboard
                    </span>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                      Chalkboard Title / Target Expression
                    </label>
                    <input
                      type="text"
                      className="search-input"
                      style={{ width: '100%', fontSize: '14px' }}
                      value={chalkboardTitle}
                      onChange={(e) => setChalkboardTitle(e.target.value)}
                      placeholder="e.g. Tomar el pelo / avoir de la chance"
                    />
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '3px' }}>
                      Appears on the video thumbnail and props inside classroom scenes.
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px' }}>
                      Chalkboard Quiz Exercise / Prompt (Scene 2 Image)
                    </label>
                    <textarea
                      rows={4}
                      className="search-input"
                      style={{ width: '100%', fontFamily: 'monospace', fontSize: '12px', lineHeight: '1.5', resize: 'vertical' }}
                      value={chalkboardExercise}
                      onChange={(e) => setChalkboardExercise(e.target.value)}
                      placeholder="e.g. ¿Qué significa exactamente la frase me estás tomando el pelo?&#10;A: Te estás burlando de mí.&#10;B: Me estás peinando.&#10;C: Me estás diciendo la verdad."
                    />
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '3px' }}>
                      Defines the text drawn on the image chalkboard for quiz/game scenes.
                    </div>
                  </div>
                </div>

                {/* Section 2: Script Content */}
                <div
                  style={{
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '16px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                      Script & Dialogues
                    </div>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline"
                      onClick={() => setJsonMode(!jsonMode)}
                      style={{ fontSize: '11px', padding: '4px 8px' }}
                    >
                      {jsonMode ? <Edit3 size={12} /> : <Code size={12} />}
                      <span>{jsonMode ? 'Switch to Form Fields' : 'Switch to Raw JSON'}</span>
                    </button>
                  </div>

                  {jsonMode ? (
                    <div>
                      <textarea
                        rows={12}
                        className="search-input"
                        style={{
                          width: '100%',
                          fontFamily: 'monospace',
                          fontSize: '12px',
                          lineHeight: '1.5',
                          background: 'var(--bg-main)',
                          resize: 'vertical',
                        }}
                        value={rawJsonText}
                        onChange={(e) => setRawJsonText(e.target.value)}
                      />
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                        Edit the full JSON document directly. Syntax will be verified before saving.
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {Object.keys(scriptFields).length === 0 ? (
                        <div style={{ color: 'var(--text-muted)', fontSize: '13px', fontStyle: 'italic', padding: '10px 0' }}>
                          No script fields found. Switch to Raw JSON view to add lines.
                        </div>
                      ) : (
                        Object.entries(scriptFields).map(([key, val]) => {
                          const isShort = key.toLowerCase() === 'title' || key.toLowerCase() === 'answer'
                          const stringVal = typeof val === 'object' && val !== null ? JSON.stringify(val) : String(val ?? '')
                          return (
                            <div key={key}>
                              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '3px', textTransform: 'capitalize' }}>
                                {key.replace(/_/g, ' ')}
                              </label>
                              {isShort ? (
                                <input
                                  type="text"
                                  className="search-input"
                                  style={{ width: '100%', fontSize: '13px' }}
                                  value={stringVal}
                                  onChange={(e) => handleFieldChange(key, e.target.value)}
                                />
                              ) : (
                                <textarea
                                  rows={2}
                                  className="search-input"
                                  style={{ width: '100%', fontSize: '13px', resize: 'vertical' }}
                                  value={stringVal}
                                  onChange={(e) => handleFieldChange(key, e.target.value)}
                                />
                              )}
                            </div>
                          )
                        })
                      )}
                    </div>
                  )}
                </div>

                {/* Bottom Save Button */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '4px' }}>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleSaveScriptAndChalkboard}
                    disabled={savingScript}
                    style={{ padding: '8px 18px', fontWeight: 600 }}
                  >
                    <Save size={15} />
                    <span>{savingScript ? 'Saving to JSON...' : 'Save Changes to State'}</span>
                  </button>
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
