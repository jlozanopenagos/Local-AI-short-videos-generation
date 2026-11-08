import type { SystemStatus, ScriptSummary, ScriptDetail, Job, JobStage, ScriptCatalogResponse, ScriptFacets } from './types'

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch('/api/system/status')
  if (!res.ok) throw new Error(`Status HTTP ${res.status}`)
  return res.json()
}

export async function controlService(
  service: 'comfyui' | 'llm',
  action: 'start' | 'stop' | 'restart'
): Promise<{ status: string; message: string }> {
  const res = await fetch(`/api/system/service/${service}/${action}`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Action ${action} failed`)
  }
  return res.json()
}

export interface CatalogQueryOptions {
  page?: number
  pageSize?: number
  search?: string
  language?: string
  videoType?: string
  stageFilter?: string
}

export async function fetchScriptCatalog(options: CatalogQueryOptions = {}): Promise<ScriptCatalogResponse> {
  const params = new URLSearchParams()
  params.set('page', String(options.page || 1))
  params.set('page_size', String(options.pageSize || 24))

  if (options.search) params.set('search', options.search)
  if (options.language && options.language !== 'all') params.set('language', options.language)
  if (options.videoType && options.videoType !== 'all') params.set('video_type', options.videoType)
  if (options.stageFilter && options.stageFilter !== 'all') params.set('stage_filter', options.stageFilter)

  const res = await fetch(`/api/scripts?${params.toString()}`)
  if (!res.ok) throw new Error(`Catalog HTTP ${res.status}`)
  return res.json()
}

export async function fetchFacets(): Promise<ScriptFacets> {
  const res = await fetch('/api/scripts/facets')
  if (!res.ok) throw new Error(`Facets HTTP ${res.status}`)
  return res.json()
}

export async function refreshScriptCache(): Promise<{ total_indexed: number }> {
  const res = await fetch('/api/scripts/refresh', { method: 'POST' })
  if (!res.ok) throw new Error(`Refresh HTTP ${res.status}`)
  return res.json()
}

export async function fetchScripts(): Promise<ScriptSummary[]> {
  const res = await fetch('/api/scripts')
  if (!res.ok) throw new Error(`Scripts HTTP ${res.status}`)
  return res.json()
}

export async function fetchScriptDetail(scriptId: string): Promise<ScriptDetail> {
  const res = await fetch(`/api/scripts/${scriptId}`)
  if (!res.ok) throw new Error(`Script HTTP ${res.status}`)
  return res.json()
}

export interface ScriptUpdatePayload {
  script_text?: string
  script_dict?: Record<string, any>
  chalkboard_exercise?: string
  chalkboard_title?: string
  target_expression?: string
}

export async function updateScript(scriptId: string, payload: ScriptUpdatePayload): Promise<ScriptDetail> {
  const res = await fetch(`/api/scripts/${scriptId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Failed to update script ${scriptId}`)
  }
  return res.json()
}

export async function fetchJobs(): Promise<Job[]> {
  const res = await fetch('/api/jobs')
  if (!res.ok) throw new Error(`Jobs HTTP ${res.status}`)
  return res.json()
}

export async function createJob(stage: JobStage, scriptIds: string[], options: Record<string, unknown> = {}): Promise<Job> {
  const res = await fetch('/api/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      stage,
      script_ids: scriptIds,
      options,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Failed to create job`)
  }
  return res.json()
}

export async function cancelJob(jobId: string): Promise<void> {
  const res = await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `Failed to cancel job`)
  }
}

export function getMediaUrl(pathOrFilename?: string | null): string {
  if (!pathOrFilename) return ''
  if (pathOrFilename.startsWith('http://') || pathOrFilename.startsWith('https://')) {
    return pathOrFilename
  }
  return `/api/media?file=${encodeURIComponent(pathOrFilename)}`
}
