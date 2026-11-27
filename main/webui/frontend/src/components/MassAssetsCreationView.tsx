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
import type {
  JobStage,
  SystemStatus,
  ValidatedScriptId,
  ScriptCatalogResponse,
  VoiceProvider,
  ElevenLabsModelId,
  ElevenLabsStatus,
  VoiceCreditEstimateResponse,
} from '../types'
import {
  createJob,
  validateScriptIds,
  fetchScriptCatalog,
  fetchElevenLabsStatus,
  saveElevenLabsKey,
  estimateVoiceCredits,
} from '../api'

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
  const [seed, setSeed] = useState('')
  const [accent, setAccent] = useState('')
  const [voiceEngine, setVoiceEngine] = useState('')
  const [voiceProvider, setVoiceProvider] = useState<VoiceProvider>('auto')
  const [elevenLabsModel, setElevenLabsModel] = useState<ElevenLabsModelId>('eleven_v3')
  const [elevenLabsStatus, setElevenLabsStatus] = useState<ElevenLabsStatus | null>(null)
  const [creditEstimate, setCreditEstimate] = useState<VoiceCreditEstimateResponse | null>(null)
  const [showElevenLabsKeyModal, setShowElevenLabsKeyModal] = useState(false)
  const [elevenLabsKeyInput, setElevenLabsKeyInput] = useState('')
  const [savingElevenLabsKey, setSavingElevenLabsKey] = useState(false)
  const [recast, setRecast] = useState(false)
  const [keepSubtitles, setKeepSubtitles] = useState(false)
  const [driveScope, setDriveScope] = useState<'all' | 'video' | 'thumbnail'>('all')
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

  // Fetch ElevenLabs status when voice stage is selected
  useEffect(() => {
    if (targetStage !== 'voice') return
    fetchElevenLabsStatus(true)
      .then((st) => setElevenLabsStatus(st))
      .catch(() => {})
  }, [targetStage])

  // Estimate ElevenLabs credits whenever validIds / provider / model changes
  useEffect(() => {
    if (targetStage !== 'voice' || !validIds.length) {
      setCreditEstimate(null)
      return
    }
    let cancelled = false
    estimateVoiceCredits(validIds, voiceProvider, elevenLabsModel)
      .then((est) => {
        if (!cancelled) setCreditEstimate(est)
      })
      .catch(() => {
        if (!cancelled) setCreditEstimate(null)
      })
    return () => {
      cancelled = true
    }
  }, [targetStage, validIds, voiceProvider, elevenLabsModel])

  const handleSaveElevenLabsKey = async () => {
    if (!elevenLabsKeyInput.trim()) return
    setSavingElevenLabsKey(true)
    try {
      await saveElevenLabsKey(elevenLabsKeyInput.trim())
      setElevenLabsKeyInput('')
      setShowElevenLabsKeyModal(false)
      const st = await fetchElevenLabsStatus(true)
      setElevenLabsStatus(st)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : String(err))
    } finally {
      setSavingElevenLabsKey(false)
    }
  }
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

  // Drive upload readiness (adapts to selected scope: both, video only, or thumbnail only)
  const isItemDriveReady = useCallback(
    (item: ValidatedScriptId) => {
      if (!item.exists) return false
      if (driveScope === 'video') return Boolean(item.has_video)
      if (driveScope === 'thumbnail') return Boolean(item.has_thumbnail)
      return Boolean(item.can_upload_drive)
    },
    [driveScope]
  )
  const driveReadyIds = useMemo(
    () => validatedItems.filter(isItemDriveReady).map((item) => item.id),
    [validatedItems, isItemDriveReady]
  )
  const driveNotReadyItems = useMemo(
    () => validatedItems.filter((item) => item.exists && !isItemDriveReady(item)),
    [validatedItems, isItemDriveReady]
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
        pageSize: filterKey === 'thumbnails' ? 500 : 100,
        stageFilter,
      })

      const loadedIds = data.items
        .filter((s) =>
          filterKey === 'drive'
            ? s.has_video && s.has_thumbnail
            : filterKey === 'thumbnails'
              ? s.stages.thumbnails !== 'done'
              : true
        )
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
          ? driveScope === 'video'
            ? 'None of the provided script IDs have a final assembled video on disk to upload.'
            : driveScope === 'thumbnail'
            ? 'None of the provided script IDs have a generated thumbnail on disk to upload.'
            : 'None of the provided script IDs are ready for Google Drive upload. Both the final assembled video and thumbnail must exist on disk.'
          : 'Please provide at least one valid script ID.'
      )
      return
    }

    setIsSubmitting(true)
    setErrorMessage(null)

    try {
      const options: Record<string, unknown> = { force: targetStage === 'assembly' || forceRegenerate }
      if (targetStage === 'images' && seed) {
        const seedValue = Number(seed)
        if (!Number.isSafeInteger(seedValue) || seedValue < 1) {
          throw new Error('Image seed must be a positive whole number.')
        }
        options.seed = seedValue
      }
      if (targetStage === 'voice') {
        if (accent.trim()) options.accent = accent.trim()
        if (voiceEngine) options.voice_engine = voiceEngine
        options.voice_provider = voiceProvider
        options.elevenlabs_model = elevenLabsModel
        options.recast = recast
        if (recast) options.force = true
      }
      if (targetStage === 'assembly') {
        options.keep_subtitles = keepSubtitles
        options.force_subtitles = !keepSubtitles
        options.auto_keep_subtitles = keepSubtitles
      }
      if (targetStage === 'drive_upload') options.drive_scope = driveScope
      const job = await createJob(targetStage, targetIds, options)
      onJobStarted(job.job_id)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : String(err))
      setIsSubmitting(false)
    }
  }

  const comfyOnline = system?.comfyui?.status === 'online' || (system as any)?.comfy?.status === 'online'
  const voiceUsesLocal =
    targetStage === 'voice' &&
    (voiceProvider === 'local' || (voiceProvider === 'auto' && (creditEstimate ? creditEstimate.local_count > 0 : true)))
  const voiceUsesElevenLabs =
    targetStage === 'voice' &&
    (voiceProvider === 'elevenlabs' || (voiceProvider === 'auto' && (creditEstimate ? creditEstimate.elevenlabs_count > 0 : true)))
  const isComfyRequired = targetStage === 'images' || voiceUsesLocal

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
                Multi-character spoken dialogue and narration synthesized via ElevenLabs (eleven_v3) &amp; local Qwen3-TTS.
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
                High-contrast vertical title card thumbnails (576x1024, 9:16) for YouTube Shorts.
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
                Batch upload completed final videos (&lt;ID&gt;.mp4) and thumbnails (&lt;ID&gt;_thumbnail.png) directly into your Google Drive hierarchy. Supports full bundle, video-only, or thumbnail-only uploads.
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
                {driveScope === 'video'
                  ? 'Final video (.mp4) is missing for'
                  : driveScope === 'thumbnail'
                  ? 'Thumbnail (.png) is missing for'
                  : 'Google Drive upload (video + thumbnail) requires both files.'}{' '}
                {driveNotReadyItems.length} script(s) not ready yet:{' '}
                <strong>
                  {driveNotReadyItems.slice(0, 5).map((i) => {
                    const missing =
                      driveScope === 'video'
                        ? 'video'
                        : driveScope === 'thumbnail'
                        ? 'thumb'
                        : !i.has_video && !i.has_thumbnail
                        ? 'video & thumb'
                        : !i.has_video
                        ? 'video'
                        : 'thumb'
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

                  {item.exists && targetStage === 'drive_upload' && (() => {
                    const ready = isItemDriveReady(item)
                    return (
                    <span
                      className="chip-meta-tag"
                      style={{
                        background: ready ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                        color: ready ? '#10b981' : '#ef4444',
                        borderColor: ready ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)',
                        borderWidth: '1px',
                        borderStyle: 'solid',
                        fontWeight: 600,
                        fontSize: '10px',
                      }}
                    >
                      {ready
                        ? (item.drive_uploaded ? 'drive ✓' : 'ready')
                        : driveScope === 'video'
                        ? 'no video'
                        : driveScope === 'thumbnail'
                        ? 'no thumb'
                        : (!item.has_video && !item.has_thumbnail
                            ? 'no video/thumb'
                            : !item.has_video
                            ? 'no video'
                            : 'no thumb')}
                    </span>
                    )
                  })()}

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
                  ? 'renders a replacement for every selected script and publishes it after the render succeeds.'
                  : 're-creates and overwrites existing asset files for all targeted IDs, resetting downstream status.'}
              </span>
            </span>
          </label>

          {targetStage === 'images' && (
            <label>
              Image seed (optional)
              <input className="search-input" type="number" min="1" step="1" value={seed} onChange={(e) => setSeed(e.target.value)} />
            </label>
          )}
          {targetStage === 'voice' && (
            <>
              <label>
                Voice provider
                <select
                  className="search-input"
                  value={voiceProvider}
                  onChange={(e) => setVoiceProvider(e.target.value as VoiceProvider)}
                >
                  <option value="auto">Auto Hybrid (Roleplay, Expression &amp; Fun Facts → ElevenLabs | Game → Local)</option>
                  <option value="elevenlabs">ElevenLabs (All selected IDs)</option>
                  <option value="local">Local Qwen3-TTS (All selected IDs)</option>
                </select>
              </label>

              {voiceProvider !== 'local' && (
                <label>
                  ElevenLabs model
                  <select
                    className="search-input"
                    value={elevenLabsModel}
                    onChange={(e) => setElevenLabsModel(e.target.value as ElevenLabsModelId)}
                  >
                    <option value="eleven_v3">Eleven v3 (Most Expressive — 1 cr/char)</option>
                    <option value="eleven_multilingual_v2">Multilingual v2 (Classic Stable — 1 cr/char)</option>
                    <option value="eleven_flash_v2_5">Flash v2.5 (Budget 2x — 0.5 cr/char)</option>
                  </select>
                </label>
              )}

              {voiceProvider !== 'local' && (
                <div
                  style={{
                    background: 'var(--bg-main)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    fontSize: '12px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '8px',
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                    <div>
                      <strong>ElevenLabs:</strong>{' '}
                      {elevenLabsStatus?.configured ? (
                        <span style={{ color: '#10b981' }}>
                          API key configured
                          {elevenLabsStatus.subscription
                            ? ` · ${elevenLabsStatus.subscription.remaining_credits.toLocaleString()} / ${elevenLabsStatus.subscription.character_limit.toLocaleString()} credits left (${elevenLabsStatus.subscription.tier})`
                            : ''}
                        </span>
                      ) : (
                        <span style={{ color: '#f59e0b' }}>API key not set in local main/.env</span>
                      )}
                    </div>
                    {creditEstimate && (
                      <div style={{ color: 'var(--text-muted)' }}>
                        Estimated batch cost: <strong>~{creditEstimate.total_estimated_credits.toLocaleString()} credits</strong>{' '}
                        ({creditEstimate.elevenlabs_count} ElevenLabs, {creditEstimate.local_count} Local)
                      </div>
                    )}
                  </div>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline"
                    onClick={() => setShowElevenLabsKeyModal(true)}
                  >
                    {elevenLabsStatus?.configured ? 'update ElevenLabs key' : 'set ElevenLabs API key'}
                  </button>
                </div>
              )}

              {voiceUsesElevenLabs && elevenLabsStatus && !elevenLabsStatus.configured && (
                <div className="sheets-alert error">
                  <AlertTriangle size={18} />
                  <span>
                    <strong>ElevenLabs API key missing.</strong> Click <em>set ElevenLabs API key</em> above to save your private key to local <code>main/.env</code> (gitignored), or switch provider to Local Qwen3-TTS.
                  </span>
                </div>
              )}

              <label>
                Accent override
                <input className="search-input" value={accent} placeholder="e.g. es_latam_neutral or es_spain_castilian" onChange={(e) => setAccent(e.target.value)} />
              </label>
              {voiceProvider !== 'elevenlabs' && (
                <label>
                  Local voice engine
                  <select className="search-input" value={voiceEngine} onChange={(e) => setVoiceEngine(e.target.value)}>
                    <option value="">Configured default</option>
                    <option value="typed">Typed</option>
                    <option value="legacy">Legacy</option>
                  </select>
                </label>
              )}
              <label className="checkbox-label">
                <input type="checkbox" checked={recast} onChange={(e) => setRecast(e.target.checked)} />
                Choose new voices
              </label>
            </>
          )}
          {targetStage === 'assembly' && (
            <label className="checkbox-label">
              <input type="checkbox" checked={keepSubtitles} onChange={(e) => setKeepSubtitles(e.target.checked)} />
              Reuse existing subtitles
            </label>
          )}
          {targetStage === 'drive_upload' && (
            <label>
              Assets to upload to Google Drive
              <select
                className="search-input"
                value={driveScope}
                onChange={(e) => setDriveScope(e.target.value as 'all' | 'video' | 'thumbnail')}
              >
                <option value="all">Both: Final Video + Thumbnail(s)</option>
                <option value="video">Final Video Only (.mp4)</option>
                <option value="thumbnail">Thumbnail(s) Only (.png)</option>
              </select>
            </label>
          )}

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
                    ? `launch mass drive upload — ${driveScope === 'video' ? 'video only' : driveScope === 'thumbnail' ? 'thumbnail only' : 'video + thumb'} (${driveReadyIds.length} scripts)`
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

      {/* Secure ElevenLabs API Key Modal */}
      {showElevenLabsKeyModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 2000,
          }}
          onClick={() => setShowElevenLabsKeyModal(false)}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: '10px',
              padding: '24px',
              maxWidth: '480px',
              width: '90%',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <Mic size={18} style={{ color: 'var(--accent)' }} />
              <h3 style={{ fontSize: '16px', fontWeight: 700, margin: 0 }}>Enter ElevenLabs API Key</h3>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '14px', lineHeight: 1.5 }}>
              Saved strictly locally to <code>main/.env</code> (gitignored — never committed or exposed in API responses).
            </p>
            <input
              type="password"
              className="search-input"
              placeholder="Paste your ElevenLabs API key (sk_...)"
              value={elevenLabsKeyInput}
              onChange={(e) => setElevenLabsKeyInput(e.target.value)}
              style={{ width: '100%', marginBottom: '16px' }}
            />
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
              <button
                type="button"
                className="btn btn-sm btn-outline"
                onClick={() => setShowElevenLabsKeyModal(false)}
                disabled={savingElevenLabsKey}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-sm btn-primary"
                onClick={handleSaveElevenLabsKey}
                disabled={!elevenLabsKeyInput.trim() || savingElevenLabsKey}
              >
                {savingElevenLabsKey ? 'Saving...' : 'Save Key to .env'}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

