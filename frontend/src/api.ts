import type {
  CandidateDetailPayload,
  CandidateResumeRawPayload,
  SearchRequestPayload,
  SearchResponsePayload,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

async function parseErrorMessage(response: Response): Promise<string> {
  let message = `Request failed with status ${response.status}`
  try {
    const parsed = (await response.json()) as { detail?: string }
    if (parsed?.detail) {
      message = parsed.detail
    }
  } catch {
    // keep fallback message when body is not json
  }
  return message
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init)
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response))
  }
  return (await response.json()) as T
}

export async function postSearch(payload: SearchRequestPayload): Promise<SearchResponsePayload> {
  return requestJson<SearchResponsePayload>('/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
}

export async function getCandidateDetail(candidateId: string): Promise<CandidateDetailPayload> {
  return requestJson<CandidateDetailPayload>(`/candidates/${encodeURIComponent(candidateId)}`)
}

export async function getCandidateResumeRaw(candidateId: string): Promise<CandidateResumeRawPayload> {
  return requestJson<CandidateResumeRawPayload>(`/candidates/${encodeURIComponent(candidateId)}/resume`)
}

