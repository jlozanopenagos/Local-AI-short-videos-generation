import React, { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Layers,
  Mic,
  Image as ImageIcon,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  X,
  Upload,
  FileSpreadsheet,
  Trash2,
  Play,
  Filter,
  ExternalLink,
  FileText,
  Video,
  CloudUpload
} from 'lucide-react'
import type { JobStage, SystemStatus, ValidatedScriptId, ScriptCatalogResponse } from '../types'
import { createJob, validateScriptIds, fetchScriptCatalog } from '../api'

interface MassAssetsCreationViewProps {
  system: SystemStatus | null
  onJobStarted: (jobId: string) => void
  onSelectScript: (scriptId: string) => void
}

type CollectionMode = 'text' | 'csv' | 'catalog'

export const MassAssetsCreationView: React.FC<MassAssetsCreationViewProps> = ({
  system,
  onJobStarted,
  onSelectScript,
}) => {
  // Selected Target Stage
  const [targetStage, setTargetStage] = useState<JobStage>('images')

  // Collection Mode
  const [collectionMode, setCollectionMode] = useState<CollectionMode>('text')

  // Textarea input
  const [rawIdInput, setRawIdInput] = useState<string>('')

  // Validated items
  const [validatedItems, setValidatedItems] = useState<ValidatedScriptId[]>([])
  const [isValidating, setIsValidating] = useState<boolean>(false)

  // Options
  const [forceRegenerate, setForceRegenerate] = useState<boolean>(true)
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // CSV file loading state
  const [csvFileName, setCsvFileName] = useState<string | null>(null)

  // Parse raw text into unique sanitized IDs
  const parsedRawIds = useMemo(() => {
    if (!rawIdInput.trim()) return []
    const tokens = rawIdInput.split(/[\s,;\n\r\t]+/)
    const seen = new Set<string>()
    const ids: string[] = []
    for (const t of tokens) {
      const clean = t.trim().toUpperCase().replace(/^SCRIPT_/, '').replace(/\.JSON$/, '')
      if (clean && !seen.has(clean)) {
        seen.add(clean)
        ids.push(clean)
      }
    }
    return ids
  }, [rawIdInput])

  // Trigger ID validation against backend
  const handleValidate = useCallback(async (idsToValidate: string[]) => {
    if (!idsToValidate.length) {
      setValidatedItems([])
      return
    }
    setIsValidating(true)
    setErrorMessage(null)
    try {
      const res = await validateScriptIds(idsToValidate)
      setValidatedItems(res.items)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setIsValidating(false)
    }
  }, [])

  // Debounced auto-validate when typing/pasting
  useEffect(() => {
    if (!parsedRawIds.length) {
      setValidatedItems([])
      return
    }
    const timer = setTimeout(() => {
      handleValidate(parsedRawIds)
    }, 600)
    return () => clearInterval(timer)
  }, [parsedRawIds, handleValidate])

  // Valid and Invalid lists
  const validIds = useMemo(
    () => validatedItems.filter((item) => item.exists).map((item) => item.id),
    [validatedItems]
  )
  const invalidItems = useMemo(
    () => validatedItems.filter((item) => !item.exists),
    [validatedItems]
  )

  const isGameId = useCallback((id: string) => {
    const clean = id.trim().toUpperCase()
    return clean.length >= 2 && clean.charAt(1) === 'G'
  }, [])

  const gameIds = useMemo(() => validIds.filter(isGameId), [validIds, isGameId])
  const nonGameIds = useMemo(() => validIds.filter((id) => !isGameId(id)), [validIds, isGameId])

  // Drive upload readiness (both video and thumbnail are mandatory)
  const driveReadyIds = useMemo(
    () => validatedItems.filter((item) => item.exists && item.can_upload_drive).map((item) => item.id),
    [validatedItems]
  )
  const driveNotReadyItems = useMemo(
    () => validatedItems.filter((item) => item.exists && !item.can_upload_drive),
    [validatedItems]
  )

  // Remove an individual ID
  const handleRemoveId = (idToRemove: string) => {
    const updated = rawIdInput
      .split(/[\s,;\n\r\t]+/)
      .filter((id) => id.trim().toUpperCase() !== idToRemove.toUpperCase())
      .join(', ')
    setRawIdInput(updated)
  }

  // Remove all invalid IDs
  const handleRemoveInvalid = () => {
    const invalidSet = new Set(invalidItems.map((i) => i.id.toUpperCase()))
    const updated = rawIdInput
      .split(/[\s,;\n\r\t]+/)
      .filter((id) => !invalidSet.has(id.trim().toUpperCase()))
      .join(', ')
    setRawIdInput(updated)
  }

  // Clear all
  const handleClearAll = () => {
    setRawIdInput('')
    setValidatedItems([])
    setCsvFileName(null)
    setErrorMessage(null)
  }

  // Quick preset loader from catalog by stage
  const handleLoadFromCatalog = async (filterKey: 'voice' | 'images' | 'thumbnails' | 'assembly' | 'drive') => {
    setIsValidating(true)
    setErrorMessage(null)
    try {
      const stageFilter =
        filterKey === 'voice'
          ? 'missing_voice'
          : filterKey === 'images'
            ? 'missing_images'
            : filterKey === 'assembly'
              ? 'ready_for_assembly'
              : filterKey === 'drive'
                ? 'complete'
                : 'all'

      const data: ScriptCatalogResponse = await fetchScriptCatalog({
        pageSize: 100,
        stageFilter,
      })

      const loadedIds = data.items
        .filter((s) => (filterKey === 'drive' ? s.has_video && s.has_thumbnail : true))
        .map((s) => s.id)

      if (!loadedIds.length) {
        setErrorMessage(
          filterKey === 'drive'
            ? 'No scripts found in catalog with both completed final video and thumbnail.'
            : filterKey === 'assembly'
            ? 'No scripts currently ready for video assembly (voice and images must be completed first).'
            : `No scripts found with pending ${filterKey}.`
        )
        return
      }

      setRawIdInput(loadedIds.join(', '))
      handleValidate(loadedIds)
    } catch (err) {
      setErrorMessage(`Failed to query catalog: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsValidating(false)
    }
  }

  // Handle local CSV file upload
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setCsvFileName(file.name)
    const reader = new FileReader()
    reader.onload = (event) => {
      const content = String(event.target?.result || '')
      const lines = content.split(/\r?\n/)
      if (!lines.length) return

      let idColIdx = 0
      const header = lines[0].split(',')
      const foundIdx = header.findIndex((h) => {
        const clean = h.trim().toUpperCase().replace(/["']/g, '')
        return clean === 'ID' || clean === 'SCRIPT_ID'
      })
      if (foundIdx !== -1) {
        idColIdx = foundIdx
      }

      const extracted: string[] = []
      for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim()
        if (!line) continue
        const cols = line.split(',')
        if (cols[idColIdx]) {
          const val = cols[idColIdx].trim().toUpperCase().replace(/["']/g, '')
          if (val && !extracted.includes(val)) {
            extracted.push(val)
          }
        }
      }

      if (extracted.length) {
        setRawIdInput(extracted.join(', '))
        handleValidate(extracted)
      } else {
        setErrorMessage(`No valid IDs found in CSV file "${file.name}".`)
      }
    }
    reader.readAsText(file)
  }

  // Launch Mass Asset Job
  const handleLaunch = async () => {
    const targetIds =
      targetStage === 'chalkboard'
        ? gameIds
        : targetStage === 'drive_upload'
        ? driveReadyIds
        : validIds

    if (!targetIds.length) {
      setErrorMessage(
        targetStage === 'chalkboard'
          ? 'Please provide at least one valid Game script ID (e.g. EG01, FG01, SG01, IG01) for chalkboard creation.'
          : targetStage === 'drive_upload'
          ? 'None of the provided script IDs are ready for Google Drive upload. Both the final assembled video and thumbnail must exist on disk.'
          : 'Please provide at least one valid script ID.'
      )
      return
    }

    setIsSubmitting(true)
    setErrorMessage(null)

    try {
      const job = await createJob(targetStage, targetIds, {
        force: targetStage === 'assembly' ? true : forceRegenerate,
      })
      onJobStarted(job.job_id)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : String(err))
      setIsSubmitting(false)
    }
  }

  const comfyOnline = system?.comfyui?.status === 'online' || (system as any)?.comfy?.status === 'online'
  const isComfyRequired = targetStage === 'images' || targetStage === 'voice'

  return (
    <section className="mass-creation-container" aria-label="Mass asset creation">
      {/* View Header */}
      <div className="mass-creation-header">
        <div className="header-title-group">
          <div className="header-icon-wrap">
            <Layers size={28} className="icon-accent" />
          </div>
          <div>
            <h1 className="header-title">Mass asset creation</h1>
            <p className="header-subtitle">
              Batch create voice tracks, scene illustrations, or chalkboard images for arbitrary IDs across any
              language or video format with enforced regeneration.
            </p>
          </div>
        </div>
      </div>

      {errorMessage && (
        <div className="sheets-alert error">
          <AlertTriangle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* STEP 1: Select Asset Target */}
      <div className="mass-step-card">
        <div className="step-badge-row">
          <span className="step-number">step 1</span>
          <span className="step-heading">choose asset type to create</span>
        </div>

        <div className="asset-cards-grid">
          {/* Option A: Script Generation */}
          <div
            className={`asset-option-card ${targetStage === 'scripts' ? 'selected' : ''}`}
            onClick={() => setTargetStage('scripts')}
          >
            <div className="option-icon-box" style={{ background: 'var(--accent-subtle)', color: 'var(--accent)', border: '1px solid var(--accent-border)' }}>
              <FileText size={24} />
            </div>
            <div className="option-content">
              <div className="option-title">script dialogues</div>
              <div className="option-desc">
                Modular domain engines generating spoken script dialogues, timing, and chalkboard text.
              </div>
            </div>
            <div className="option-stage-pill">stage A</div>
          </div>

          {/* Option B: Images */}
          <div
            className={`asset-option-card ${targetStage === 'images' ? 'selected' : ''}`}
            onClick={() => setTargetStage('images')}
          >
            <div className="option-icon-box images">
              <ImageIcon size={24} />
            </div>
            <div className="option-content">
              <div className="option-title">scene images</div>
              <div className="option-desc">
                Cartoon narrative illustrations generated through ComfyUI for all scenes in each script.
              </div>
            </div>
            <div className="option-stage-pill">stage C</div>
          </div>

          {/* Option C: Voice */}
          <div
            className={`asset-option-card ${targetStage === 'voice' ? 'selected' : ''}`}
            onClick={() => setTargetStage('voice')}
          >
            <div className="option-icon-box voice">
              <Mic size={24} />
            </div>
            <div className="option-content">
              <div className="option-title">voice files (audio)</div>
              <div className="option-desc">
                Multi-character spoken dialogue and narration synthesized via Kokoro / ComfyUI.
              </div>
            </div>
            <div className="option-stage-pill">stage B</div>
          </div>

          {/* Option D: Thumbnails */}
          <div
            className={`asset-option-card ${targetStage === 'thumbnails' ? 'selected' : ''}`}
            onClick={() => setTargetStage('thumbnails')}
          >
            <div className="option-icon-box thumbnails">
              <Sparkles size={24} />
            </div>
            <div className="option-content">
              <div className="option-title">thumbnail image</div>
              <div className="option-desc">
                High-contrast vertical title card thumbnails (1080x1920) for YouTube Shorts.
              </div>
            </div>
            <div className="option-stage-pill">stage F</div>
          </div>

          {/* Option E: Chalkboard Images (Game) */}
          <div
            className={`asset-option-card ${targetStage === 'chalkboard' ? 'selected' : ''}`}
            onClick={() => setTargetStage('chalkboard')}
          >
            <div className="option-icon-box" style={{ background: 'var(--sand-subtle)', color: 'var(--sand)', border: '1px solid var(--sand-border)' }}>
              <Layers size={24} />
            </div>
            <div className="option-content">
              <div className="option-title">chalkboard images</div>
              <div className="option-desc">
                High-resolution native chalk typography on empty chalkboard for Game quiz scenes (instant, no ComfyUI/LLM).
              </div>
            </div>
            <div className="option-stage-pill" style={{ background: 'var(--sand-subtle)', color: 'var(--sand)', border: '1px solid var(--sand-border)' }}>game only</div>
          </div>

          {/* Option F: Video Assembly */}
          <div
            className={`asset-option-card ${targetStage === 'assembly' ? 'selected' : ''}`}
            onClick={() => setTargetStage('assembly')}
          >
            <div className="option-icon-box" style={{ background: 'rgba(59, 130, 246, 0.12)', color: '#3b82f6', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
              <Video size={24} />
            </div>
            <div className="option-content">
              <div className="option-title">video assembly</div>
              <div className="option-desc">
                Full vertical YouTube Shorts (master voice audio, scene visuals, ASS subtitles, bank music, and opening/closure cards).
              </div>
            </div>
            <div className="option-stage-pill" style={{ background: 'rgba(59, 130, 246, 0.12)', color: '#3b82f6', border: '1px solid rgba(59, 130, 246, 0.3)' }}>stage G</div>
          </div>

          {/* Option G: Google Drive Upload */}
          <div
            className={`asset-option-card ${targetStage === 'drive_upload' ? 'selected' : ''}`}
            onClick={() => setTargetStage('drive_upload')}
          >
            <div className="option-icon-box" style={{ background: 'rgba(16, 185, 129, 0.12)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
              <CloudUpload size={24} />
            </div>
            <div className="option-content">
              <div className="option-title">google drive upload</div>
              <div className="option-desc">
                Batch upload completed final videos (&lt;ID&gt;.mp4) and thumbnails (&lt;ID&gt;_thumbnail.png) directly into your Google Drive hierarchy. Both assets are strictly mandatory.
              </div>
            </div>
            <div className="option-stage-pill" style={{ background: 'rgba(16, 185, 129, 0.12)', color: '#10b981', border: '1px solid rgba(16, 185, 129, 0.3)' }}>cloud export</div>
          </div>
        </div>
      </div>

      {/* STEP 2: Collect Script IDs */}
      <div className="mass-step-card">
        <div className="step-header-with-actions">
          <div className="step-badge-row">
            <span className="step-number">step 2</span>
            <span className="step-heading">collect script IDs</span>
          </div>

          <div className="mode-tabs">
            <button
              className={`mode-tab ${collectionMode === 'text' ? 'active' : ''}`}
              onClick={() => setCollectionMode('text')}
            >
              Direct paste / input
            </button>
            <button
              className={`mode-tab ${collectionMode === 'csv' ? 'active' : ''}`}
              onClick={() => setCollectionMode('csv')}
            >
              Load from CSV
            </button>
            <button
              className={`mode-tab ${collectionMode === 'catalog' ? 'active' : ''}`}
              onClick={() => setCollectionMode('catalog')}
            >
              Presets & filters
            </button>
          </div>
        </div>

        {/* Input Method A: Text Area */}
        {collectionMode === 'text' && (
          <div className="input-method-box">
            <textarea
              className="id-textarea"
              rows={4}
              placeholder="Paste IDs separated by commas, spaces, or lines (e.g. EE01, SR02, FE05, IG10)..."
              value={rawIdInput}
              onChange={(e) => setRawIdInput(e.target.value)}
            />
            <div className="textarea-footer">
              <span className="id-count-hint">
                {parsedRawIds.length} unique ID(s) typed/pasted
              </span>
              {rawIdInput && (
                <button className="btn btn-outline btn-sm" onClick={handleClearAll}>
                  <Trash2 size={13} />
                  <span>Clear input</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Input Method B: CSV Upload */}
        {collectionMode === 'csv' && (
          <div className="input-method-box csv-upload-box">
            <label className="csv-dropzone">
              <Upload size={32} className="icon-accent" />
              <div className="dropzone-text">
                <strong>Click to select a CSV file</strong> or drag & drop here
              </div>
              <div className="dropzone-hint">
                Extracts the <code>ID</code> column automatically
              </div>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                style={{ display: 'none' }}
              />
            </label>

            {csvFileName && (
              <div className="loaded-file-pill">
                <FileSpreadsheet size={16} />
                <span>{csvFileName}</span>
                <span className="file-id-count">({parsedRawIds.length} IDs loaded)</span>
              </div>
            )}
          </div>
        )}

        {/* Input Method C: Catalog Presets */}
        {collectionMode === 'catalog' && (
          <div className="input-method-box presets-box">
            <div className="presets-label">
              <Filter size={16} />
              <span>quick scenario presets:</span>
            </div>
            <div className="presets-buttons-row">
              <button
                className="btn btn-outline btn-sm"
                onClick={() => handleLoadFromCatalog('images')}
                disabled={isValidating}
              >
                <ImageIcon size={14} />
                <span>all pending scene images</span>
              </button>
              <button
                className="btn btn-outline btn-sm"
                onClick={() => handleLoadFromCatalog('voice')}
                disabled={isValidating}
              >
                <Mic size={14} />
                <span>all pending voice tracks</span>
              </button>
              <button
                className="btn btn-outline btn-sm"
                onClick={() => handleLoadFromCatalog('thumbnails')}
                disabled={isValidating}
              >
                <Sparkles size={14} />
                <span>all pending thumbnails</span>
              </button>
              <button
                className="btn btn-outline btn-sm"
                onClick={() => handleLoadFromCatalog('assembly')}
                disabled={isValidating}
                style={{ borderColor: 'rgba(59, 130, 246, 0.5)', color: '#3b82f6' }}
              >
                <Video size={14} />
                <span>ready for video assembly</span>
              </button>
              <button
                className="btn btn-outline btn-sm"
                onClick={() => handleLoadFromCatalog('drive')}
                disabled={isValidating}
                style={{ borderColor: 'rgba(16, 185, 129, 0.5)', color: '#10b981' }}
              >
                <CloudUpload size={14} />
                <span>ready for drive upload (video + thumb)</span>
              </button>
              <button
                className="btn btn-outline btn-sm"
                onClick={async () => {
                  setIsValidating(true)
                  setErrorMessage(null)
                  try {
                    const data: ScriptCatalogResponse = await fetchScriptCatalog({ pageSize: 100, stageFilter: 'all' })
                    const gIds = data.items.filter((s) => isGameId(s.id)).map((s) => s.id)
                    if (!gIds.length) {
                      setErrorMessage('no Game scripts found in catalog.')
                      return
                    }
                    setRawIdInput(gIds.join(', '))
                    handleValidate(gIds)
                  } catch (err) {
                    setErrorMessage(`failed to query catalog: ${err instanceof Error ? err.message : String(err)}`)
                  } finally {
                    setIsValidating(false)
                  }
                }}
                disabled={isValidating}
              >
                <Layers size={14} />
                <span>all game scripts (G-series)</span>
              </button>
            </div>
          </div>
        )}

        {/* Chalkboard Stage: Non-Game Scripts Warning Banner */}
        {targetStage === 'chalkboard' && nonGameIds.length > 0 && (
          <div
            className="sheets-alert error"
            style={{ margin: '14px 0 8px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={18} />
              <span>
                Chalkboard images only apply to Game videos (G-series). {nonGameIds.length} non-game ID(s) detected: <strong>{nonGameIds.slice(0, 5).join(', ')}{nonGameIds.length > 5 ? '...' : ''}</strong>.
              </span>
            </div>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              style={{ background: 'rgba(255, 255, 255, 0.12)', borderColor: 'rgba(255, 255, 255, 0.3)', color: 'var(--text-main)' }}
              onClick={() => {
                const updated = rawIdInput
                  .split(/[\s,;\n\r\t]+/)
                  .filter((id) => isGameId(id))
                  .join(', ')
                setRawIdInput(updated)
              }}
            >
              Keep only Game IDs ({gameIds.length})
            </button>
          </div>
        )}

        {/* Drive Upload Stage: Missing Video or Thumbnail Warning Banner */}
        {targetStage === 'drive_upload' && driveNotReadyItems.length > 0 && (
          <div
            className="sheets-alert error"
            style={{ margin: '14px 0 8px 0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={18} />
              <span>
                Google Drive upload strictly requires both final video and thumbnail. {driveNotReadyItems.length} script(s) are not ready yet:{' '}
                <strong>
                  {driveNotReadyItems.slice(0, 5).map((i) => {
                    const missing = !i.has_video && !i.has_thumbnail ? 'video & thumb' : !i.has_video ? 'video' : 'thumb'
                    return `${i.id} (${missing} missing)`
                  }).join(', ')}
                  {driveNotReadyItems.length > 5 ? '...' : ''}
                </strong>
              </span>
            </div>
            <button
              type="button"
              className="btn btn-outline btn-sm"
              style={{ background: 'rgba(255, 255, 255, 0.12)', borderColor: 'rgba(255, 255, 255, 0.3)', color: 'var(--text-main)' }}
              onClick={() => {
                const readySet = new Set(driveReadyIds)
                const updated = rawIdInput
                  .split(/[\s,;\n\r\t]+/)
                  .filter((id) => readySet.has(id.trim().toUpperCase()))
                  .join(', ')
                setRawIdInput(updated)
              }}
            >
              Keep only ready scripts ({driveReadyIds.length})
            </button>
          </div>
        )}

        {/* Validated ID Chips Container */}
        {validatedItems.length > 0 && (
          <div className="chips-container-wrapper">
            <div className="chips-header">
              <div className="chips-counts">
                {targetStage === 'drive_upload' ? (
                  <>
                    <span className="count-badge valid" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
                      <CheckCircle2 size={14} />
                      {driveReadyIds.length} ready to upload
                    </span>
                    {driveNotReadyItems.length > 0 && (
                      <span className="count-badge invalid">
                        <AlertTriangle size={14} />
                        {driveNotReadyItems.length} missing video/thumb
                      </span>
                    )}
                  </>
                ) : (
                  <>
                    <span className="count-badge valid">
                      <CheckCircle2 size={14} />
                      {validIds.length} valid
                    </span>
                    {invalidItems.length > 0 && (
                      <span className="count-badge invalid">
                        <AlertTriangle size={14} />
                        {invalidItems.length} not found
                      </span>
                    )}
                  </>
                )}
              </div>

              <div className="chips-actions">
                {invalidItems.length > 0 && (
                  <button className="btn btn-outline btn-sm" style={{ color: 'var(--warning)', borderColor: 'var(--warning-border)' }} onClick={handleRemoveInvalid}>
                    Remove {invalidItems.length} invalid
                  </button>
                )}
                <button className="btn btn-outline btn-sm" onClick={handleClearAll}>
                  Clear all
                </button>
              </div>
            </div>

            <div className="chips-grid">
              {validatedItems.map((item) => (
                <div
                  key={item.id}
                  className={`script-id-chip ${item.exists ? 'valid' : 'invalid'}`}
                  title={item.exists ? `${item.language || ''} ${item.type || ''}` : 'Script state does not exist in state/'}
                >
                  <span
                    className="chip-id-text"
                    onClick={() => item.exists && onSelectScript(item.id)}
                  >
                    {item.id}
                    {item.exists && <ExternalLink size={10} className="chip-link-icon" />}
                  </span>

                  {item.exists && item.language && (
                    <span className="chip-meta-tag">
                      {item.language}/{item.type}
                    </span>
                  )}

                  {item.exists && targetStage === 'drive_upload' && (
                    <span
                      className="chip-meta-tag"
                      style={{
                        background: item.can_upload_drive ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                        color: item.can_upload_drive ? '#10b981' : '#ef4444',
                        borderColor: item.can_upload_drive ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)',
                        borderWidth: '1px',
                        borderStyle: 'solid',
                        fontWeight: 600,
                        fontSize: '10px',
                      }}
                    >
                      {item.can_upload_drive
                        ? (item.drive_uploaded ? 'drive ✓' : 'ready')
                        : (!item.has_video && !item.has_thumbnail
                            ? 'no video/thumb'
                            : !item.has_video
                            ? 'no video'
                            : 'no thumb')}
                    </span>
                  )}

                  <button
                    className="chip-remove-btn"
                    onClick={() => handleRemoveId(item.id)}
                    title={`Remove ${item.id}`}
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* STEP 3: Execution Settings & Launch */}
      <div className="mass-step-card">
        <div className="step-badge-row">
          <span className="step-number">step 3</span>
          <span className="step-heading">execution & force overwrite</span>
        </div>

        <div className="settings-content">
          <label className="checkbox-label highlight">
            <input
              type="checkbox"
              checked={targetStage === 'assembly' ? true : forceRegenerate}
              disabled={targetStage === 'assembly'}
              onChange={(e) => setForceRegenerate(e.target.checked)}
            />
            <span className="checkbox-text">
              <strong>
                {targetStage === 'assembly'
                  ? 'always force video assembly for targeted IDs'
                  : 'force regeneration even if marked as "done" in state JSON'}
              </strong>
              <span className="checkbox-hint">
                {targetStage === 'assembly'
                  ? 'mass video assembly always forces all targeted IDs: any existing final video (.mp4) is deleted and created again from scratch.'
                  : 're-creates and overwrites existing asset files for all targeted IDs, resetting downstream status.'}
              </span>
            </span>
          </label>

          {/* ComfyUI Service Warning */}
          {isComfyRequired && !comfyOnline && (
            <div className="sheets-alert error">
              <AlertTriangle size={18} />
              <span>
                <strong>ComfyUI is currently offline.</strong> please start ComfyUI using the toggle in the top navbar
                before launching generation for {targetStage}.
              </span>
            </div>
          )}

          <div className="launch-action-row">
            <button
              className={`btn btn-lg ${targetStage === 'drive_upload' ? '' : 'btn-primary'}`}
              style={
                targetStage === 'drive_upload'
                  ? {
                      background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                      color: '#ffffff',
                      border: 'none',
                      fontWeight: 600,
                      boxShadow: '0 2px 6px rgba(16, 185, 129, 0.35)',
                    }
                  : undefined
              }
              disabled={
                (targetStage === 'chalkboard'
                  ? gameIds.length === 0
                  : targetStage === 'drive_upload'
                  ? driveReadyIds.length === 0
                  : validIds.length === 0) || isSubmitting
              }
              onClick={handleLaunch}
            >
              {targetStage === 'drive_upload' ? (
                <CloudUpload size={18} />
              ) : (
                <Play size={18} />
              )}
              <span>
                {isSubmitting
                  ? 'dispatching job...'
                  : targetStage === 'chalkboard'
                    ? `launch chalkboard creation (${gameIds.length} Game scripts)`
                    : targetStage === 'drive_upload'
                    ? `launch mass drive upload (${driveReadyIds.length} scripts)`
                    : `launch mass generation (${validIds.length} scripts)`}
              </span>
            </button>
            <span className="launch-hint">
              target: <strong>{targetStage}</strong> •{' '}
              {targetStage === 'chalkboard'
                ? gameIds.length
                : targetStage === 'drive_upload'
                ? driveReadyIds.length
                : validIds.length}{' '}
              script(s) queued
            </span>
          </div>
        </div>
      </div>
    </section>
  )
}

