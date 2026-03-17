import type {
  CandidateDetailPayload,
  CandidateResumeRawPayload,
  EscoDomain,
  EscoOption,
  EscoSuggestResponsePayload,
  SearchRequestPayload,
  SearchResponsePayload,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'
const ESCO_SUGGEST_CACHE_TTL_MS = 5 * 60 * 1000
const escoSuggestCache = new Map<string, { expiresAt: number; results: EscoOption[] }>()

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

export async function fetchEscoSuggestions(domain: EscoDomain, query: string, limit = 10): Promise<EscoOption[]> {
  const trimmed = query.trim()
  if (trimmed.length < 2) {
    return []
  }

  const normalizedLimit = Math.max(1, Math.min(limit, 20))
  const cacheKey = `${domain}::${trimmed.toLowerCase()}::${normalizedLimit}`
  const now = Date.now()
  const cached = escoSuggestCache.get(cacheKey)
  if (cached && cached.expiresAt > now) {
    return cached.results
  }

  const params = new URLSearchParams({
    domain,
    q: trimmed,
    limit: String(normalizedLimit),
  })
  const response = await requestJson<EscoSuggestResponsePayload>(`/esco/suggest?${params.toString()}`)
  escoSuggestCache.set(cacheKey, {
    expiresAt: now + ESCO_SUGGEST_CACHE_TTL_MS,
    results: response.results,
  })
  return response.results
}
