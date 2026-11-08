import type { SystemStatus, ScriptSummary, ScriptDetail, Job, JobStage } from './types'

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

