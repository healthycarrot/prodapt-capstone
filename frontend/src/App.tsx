import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  LinearProgress,
  MenuItem,
  Paper,
  Slider,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { useEffect, useMemo, useRef, useState } from 'react'
import { fetchEscoSuggestions, getCandidateDetail, getCandidateResumeRaw, postSearch } from './api'
import type {
  CandidateDetailPayload,
  CandidateResumeRawPayload,
  EscoDomain,
  EscoOption,
  SearchRequestPayload,
  SearchResponsePayload,
  SearchResultItem,
} from './types'

const LOCATION_OPTIONS = ['Remote', 'Tokyo', 'Yokohama', 'Osaka', 'Kyoto', 'Singapore', 'Bangalore']
const ESCO_MIN_QUERY_LENGTH = 2
const ESCO_DEBOUNCE_MS = 300

const EDUCATION_RANK_OPTIONS = [
  { value: '', label: 'Not specified' },
  { value: '0', label: '0 - Unknown' },
  { value: '1', label: '1 - Secondary' },
  { value: '2', label: '2 - Associate / Diploma' },
  { value: '3', label: '3 - Bachelor' },
  { value: '4', label: '4 - Master' },
  { value: '5', label: '5 - Doctorate' },
]

type FormState = {
  queryText: string
  skillTerms: EscoOption[]
  occupationTerms: EscoOption[]
  industryTerms: EscoOption[]
  experienceMinMonths: string
  experienceMaxMonths: string
  educationMinRank: string
  educationMaxRank: string
  locations: string[]
  limit: number
}

const DEFAULT_FORM: FormState = {
  queryText: '',
  skillTerms: [],
  occupationTerms: [],
  industryTerms: [],
  experienceMinMonths: '',
  experienceMaxMonths: '',
  educationMinRank: '',
  educationMaxRank: '',
  locations: [],
  limit: 20,
}

function normalizeTerms(values: string[]): string[] {
  const dedup = new Set<string>()
  for (const value of values) {
    const trimmed = value.trim()
    if (trimmed) {
      dedup.add(trimmed)
    }
  }
  return [...dedup]
}

function normalizeEscoOptions(values: EscoOption[]): EscoOption[] {
  const dedup = new Map<string, EscoOption>()
  for (const value of values) {
    const escoId = value.esco_id.trim()
    const label = value.label.trim()
    if (!escoId || !label) {
      continue
    }
    if (!dedup.has(escoId)) {
      dedup.set(escoId, { esco_id: escoId, label })
    }
  }
  return [...dedup.values()]
}

function parseOptionalNumber(value: string): number | null {
  if (!value.trim()) {
    return null
  }
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) {
    return null
  }
  return parsed
}

function buildPayload(form: FormState): SearchRequestPayload {
  return {
    query_text: form.queryText.trim(),
    skill_terms: normalizeTerms(form.skillTerms.map((item) => item.label)),
    occupation_terms: normalizeTerms(form.occupationTerms.map((item) => item.label)),
    industry_terms: normalizeTerms(form.industryTerms.map((item) => item.label)),
    experience_min_months: parseOptionalNumber(form.experienceMinMonths),
    experience_max_months: parseOptionalNumber(form.experienceMaxMonths),
    education_min_rank: parseOptionalNumber(form.educationMinRank),
    education_max_rank: parseOptionalNumber(form.educationMaxRank),
    locations: normalizeTerms(form.locations),
    limit: form.limit,
  }
}

type UseEscoSuggestResult = {
  options: EscoOption[]
  loading: boolean
  inputValue: string
  setInputValue: (value: string) => void
  clear: () => void
}

function useEscoSuggest(domain: EscoDomain): UseEscoSuggestResult {
  const [options, setOptions] = useState<EscoOption[]>([])
  const [loading, setLoading] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const requestIdRef = useRef(0)

  const updateInputValue = (value: string) => {
    setInputValue(value)
    if (value.trim().length >= ESCO_MIN_QUERY_LENGTH) {
      return
    }
    requestIdRef.current += 1
    setLoading(false)
    setOptions([])
  }

  useEffect(() => {
    const query = inputValue.trim()
    if (query.length < ESCO_MIN_QUERY_LENGTH) {
      return
    }

    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId
    const timeoutId = window.setTimeout(() => {
      setLoading(true)
      fetchEscoSuggestions(domain, query)
        .then((results) => {
          if (requestIdRef.current !== requestId) {
            return
          }
          setOptions(results)
        })
        .catch(() => {
          if (requestIdRef.current !== requestId) {
            return
          }
          setOptions([])
        })
        .finally(() => {
          if (requestIdRef.current !== requestId) {
            return
          }
          setLoading(false)
        })
    }, ESCO_DEBOUNCE_MS)

    return () => {
      window.clearTimeout(timeoutId)
    }
  }, [domain, inputValue])

  return {
    options,
    loading,
    inputValue,
    setInputValue: updateInputValue,
    clear: () => {
      requestIdRef.current += 1
      setInputValue('')
      setOptions([])
      setLoading(false)
    },
  }
}

function formatScore(value: number): string {
  if (!Number.isFinite(value)) {
    return 'N/A'
  }
  return value.toFixed(4)
}

function toPercent(value: number): number {
  if (!Number.isFinite(value)) {
    return 0
  }
  if (value <= 1) {
    return Math.max(0, Math.min(100, value * 100))
  }
  return Math.max(0, Math.min(100, value))
}

function pickText(item: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = item[key]
    if (typeof value === 'string' && value.trim()) {
      return value.trim()
    }
    if (typeof value === 'number' && Number.isFinite(value)) {
      return String(value)
    }
  }
  return ''
}

function compactText(value: string, maxLength = 280): string {
  if (value.length <= maxLength) {
    return value
  }
  return `${value.slice(0, maxLength)}...`
}

function MetricRow({ label, value }: { label: string; value: number }) {
  return (
    <Stack direction="row" justifyContent="space-between" alignItems="center">
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="subtitle2">{formatScore(value)}</Typography>
    </Stack>
  )
}

function ResultField({
  title,
  values,
  color,
}: {
  title: string
  values: string[]
  color: 'default' | 'success' | 'error'
}) {
  if (values.length === 0) {
    return null
  }

  return (
    <Stack spacing={0.8}>
      <Typography variant="subtitle2" color="text.secondary">
        {title}
      </Typography>
      <Stack direction="row" flexWrap="wrap" gap={1}>
        {values.map((value, index) => (
          <Chip
            key={`${title}-${value}-${index}`}
            label={value}
            color={color === 'default' ? undefined : color}
            variant={color === 'default' ? 'outlined' : 'filled'}
            size="small"
          />
        ))}
      </Stack>
    </Stack>
  )
}

function ScoreDetailDialog({
  open,
  candidate,
  onClose,
}: {
  open: boolean
  candidate: SearchResultItem | null
  onClose: () => void
}) {
  const coreScores = candidate
    ? ([
        ['Final', candidate.final_score],
        ['Retrieval', candidate.retrieval_final_score],
        ['Agent score', candidate.fr04_overall_score],
        ['Keyword', candidate.keyword_score],
        ['Vector', candidate.vector_score],
        ['Fusion', candidate.fusion_score],
        ['Cross Encoder', candidate.cross_encoder_score],
      ] as const)
    : []
  const agentEntries = candidate ? Object.entries(candidate.agent_scores) : []

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md" keepMounted disablePortal>
      <DialogTitle>{candidate ? `Score Details - Candidate ${candidate.candidate_id}` : 'Score Details'}</DialogTitle>
      <DialogContent dividers>
        {!candidate ? (
          <Alert severity="info" variant="outlined">
            Select a candidate to view score details.
          </Alert>
        ) : (
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              <Chip label={`Rank #${candidate.rank}`} color="primary" size="small" />
              <Chip label={`Final ${formatScore(candidate.final_score)}`} variant="outlined" size="small" />
            </Stack>

            <Paper sx={{ p: 1.6 }}>
              <Stack spacing={1}>
                <Typography variant="subtitle2" color="text.secondary">
                  Core Score Values
                </Typography>
                {coreScores.map(([label, value]) => (
                  <MetricRow key={`${candidate.candidate_id}-${label}`} label={label} value={value} />
                ))}
                <Typography variant="caption" color="text.secondary">
                  Core metrics are numeric outputs. Textual reasons are returned per agent score.
                </Typography>
              </Stack>
            </Paper>

            <Stack spacing={1.2}>
              <Typography variant="subtitle2" color="text.secondary">
                Agent Score Breakdown and Reasons
              </Typography>

              {agentEntries.length === 0 && (
                <Alert severity="info" variant="outlined">
                  No agent score details were returned for this candidate.
                </Alert>
              )}

              {agentEntries.map(([agentName, scoreCard]) => {
                const breakdownEntries = Object.entries(scoreCard.breakdown).sort((left, right) => right[1] - left[1])

                return (
                  <Paper key={`${candidate.candidate_id}-${agentName}-details`} sx={{ p: 1.6 }}>
                    <Stack spacing={1}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Typography variant="subtitle1">{agentName}</Typography>
                        <Chip label={`Score ${formatScore(scoreCard.score)}`} size="small" color="primary" variant="outlined" />
                      </Stack>

                      <Typography variant="subtitle2" color="text.secondary">
                        Reason
                      </Typography>
                      <Typography variant="body2">{scoreCard.reason || 'No reason text returned.'}</Typography>

                      <Typography variant="subtitle2" color="text.secondary">
                        Breakdown
                      </Typography>
                      {breakdownEntries.length === 0 && (
                        <Typography variant="body2" color="text.secondary">
                          No breakdown values returned.
                        </Typography>
                      )}
                      {breakdownEntries.map(([key, value], index) => (
                        <Stack
                          key={`${candidate.candidate_id}-${agentName}-${key}-${index}`}
                          direction="row"
                          justifyContent="space-between"
                          alignItems="center"
                        >
                          <Typography variant="body2" color="text.secondary">
                            {key}
                          </Typography>
                          <Typography variant="body2">{formatScore(value)}</Typography>
                        </Stack>
                      ))}
                    </Stack>
                  </Paper>
                )
              })}
            </Stack>

            {candidate.agent_errors.length > 0 && (
              <Alert severity="warning" variant="outlined">
                Agent warnings: {candidate.agent_errors.join(' | ')}
              </Alert>
            )}
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  )
}

function CandidateDetailDialog({
  open,
  candidateId,
  detail,
  resumeRaw,
  loading,
  error,
  onClose,
}: {
  open: boolean
  candidateId: string | null
  detail: CandidateDetailPayload | null
  resumeRaw: CandidateResumeRawPayload | null
  loading: boolean
  error: string
  onClose: () => void
}) {
  const occupationLabels = detail
    ? detail.occupation_candidates.map((item) => pickText(item, ['preferred_label', 'raw_text', 'esco_id'])).filter(Boolean)
    : []
  const skillLabels = detail
    ? detail.skill_candidates.map((item) => pickText(item, ['preferred_label', 'raw_text', 'esco_id'])).filter(Boolean)
    : []
  const rawResumeText = resumeRaw?.resume_text || detail?.resume_text || ''

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="lg"
      keepMounted
      disablePortal
      PaperProps={{
        sx: {
          minHeight: { md: '78vh' },
        },
      }}
    >
      <DialogTitle>{candidateId ? `Candidate Detail - ${candidateId}` : 'Candidate Detail'}</DialogTitle>
      <DialogContent dividers>
        {loading ? (
          <Stack spacing={1.2} alignItems="center" justifyContent="center" sx={{ py: 6 }}>
            <CircularProgress />
            <Typography variant="body2" color="text.secondary">
              Loading candidate detail and raw resume...
            </Typography>
          </Stack>
        ) : error ? (
          <Alert severity="error">{error}</Alert>
        ) : !detail ? (
          <Alert severity="info" variant="outlined">
            Select a candidate to view detail information.
          </Alert>
        ) : (
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              <Chip label={`Candidate ${detail.candidate_id}`} color="primary" size="small" />
              {detail.category ? <Chip label={`Category ${detail.category}`} size="small" variant="outlined" /> : null}
              {detail.current_location ? <Chip label={`Location ${detail.current_location}`} size="small" variant="outlined" /> : null}
              {detail.source_dataset ? (
                <Chip label={`Dataset ${detail.source_dataset}`} size="small" variant="outlined" />
              ) : null}
              {detail.source_record_id ? (
                <Chip label={`Record ${detail.source_record_id}`} size="small" variant="outlined" />
              ) : null}
            </Stack>

            <Paper sx={{ p: 1.8 }}>
              <Stack spacing={1}>
                <Typography variant="subtitle2" color="text.secondary">
                  Structured Profile
                </Typography>
                <MetricRow label="Occupation Candidates" value={occupationLabels.length} />
                <MetricRow label="Skill Candidates" value={skillLabels.length} />
                <MetricRow label="Experiences" value={detail.experiences.length} />
                <MetricRow label="Educations" value={detail.educations.length} />
              </Stack>
            </Paper>

            <ResultField title="Occupation Candidates" values={occupationLabels} color="default" />
            <ResultField title="Skill Candidates" values={skillLabels} color="default" />

            <Stack spacing={1.2}>
              <Typography variant="subtitle2" color="text.secondary">
                Experiences
              </Typography>
              {detail.experiences.length === 0 ? (
                <Alert severity="info" variant="outlined">
                  No experience records.
                </Alert>
              ) : (
                detail.experiences.map((experience, index) => {
                  const title = pickText(experience, ['title', 'raw_title']) || 'Untitled role'
                  const company = pickText(experience, ['company'])
                  const startDate = pickText(experience, ['start_date'])
                  const endDate = pickText(experience, ['end_date'])
                  const durationMonths = pickText(experience, ['duration_months'])
                  const description = pickText(experience, ['description_raw'])
                  const isCurrent = experience['is_current'] === true
                  const period = startDate || endDate ? `${startDate || '?'} - ${isCurrent ? 'current' : endDate || '?'}` : ''

                  return (
                    <Paper key={`${title}-${company}-${index}`} sx={{ p: 1.5 }}>
                      <Stack spacing={0.7}>
                        <Typography variant="subtitle1">{title}</Typography>
                        {(company || period || durationMonths) && (
                          <Typography variant="body2" color="text.secondary">
                            {[company, period, durationMonths ? `${durationMonths} months` : ''].filter(Boolean).join(' | ')}
                          </Typography>
                        )}
                        {description ? <Typography variant="body2">{compactText(description, 360)}</Typography> : null}
                      </Stack>
                    </Paper>
                  )
                })
              )}
            </Stack>

            <Stack spacing={1.2}>
              <Typography variant="subtitle2" color="text.secondary">
                Educations
              </Typography>
              {detail.educations.length === 0 ? (
                <Alert severity="info" variant="outlined">
                  No education records.
                </Alert>
              ) : (
                detail.educations.map((education, index) => {
                  const institution = pickText(education, ['institution']) || 'Unknown institution'
                  const degree = pickText(education, ['degree'])
                  const field = pickText(education, ['field_of_study'])
                  const graduationYear = pickText(education, ['graduation_year'])
                  const span = [degree, field, graduationYear].filter(Boolean).join(' | ')

                  return (
                    <Paper key={`${institution}-${index}`} sx={{ p: 1.5 }}>
                      <Stack spacing={0.5}>
                        <Typography variant="subtitle1">{institution}</Typography>
                        {span ? (
                          <Typography variant="body2" color="text.secondary">
                            {span}
                          </Typography>
                        ) : null}
                      </Stack>
                    </Paper>
                  )
                })
              )}
            </Stack>

            <Stack spacing={1}>
              <Typography variant="subtitle2" color="text.secondary">
                Raw Resume Text
              </Typography>
              {rawResumeText ? (
                <Paper sx={{ p: 1.6, maxHeight: 320, overflowY: 'auto' }}>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                    {rawResumeText}
                  </Typography>
                </Paper>
              ) : (
                <Alert severity="info" variant="outlined">
                  No raw resume text returned.
                </Alert>
              )}
            </Stack>
          </Stack>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  )
}

function CandidateCard({
  item,
  onOpenScoreDetails,
  onOpenCandidateDetail,
}: {
  item: SearchResultItem
  onOpenScoreDetails: (item: SearchResultItem) => void
  onOpenCandidateDetail: (candidateId: string) => void
}) {
  const agentEntries = useMemo(() => Object.entries(item.agent_scores), [item.agent_scores])
  const retrievalComponentEntries = useMemo(
    () =>
      ([
        ['Keyword', item.keyword_score],
        ['Vector', item.vector_score],
        ['Fusion', item.fusion_score],
        ['Cross Encoder', item.cross_encoder_score],
      ] as const),
    [item.keyword_score, item.vector_score, item.fusion_score, item.cross_encoder_score]
  )

  return (
    <Paper sx={{ p: 2.2, borderLeft: '4px solid', borderLeftColor: 'primary.main' }}>
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2.5} alignItems="stretch">
        <Stack spacing={1.2} sx={{ flexGrow: 1 }}>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
            <Chip label={`Rank #${item.rank}`} color="primary" size="small" />
            <Chip label={`Candidate ${item.candidate_id}`} variant="outlined" size="small" />
          </Stack>

          <Typography variant="body1" sx={{ lineHeight: 1.45 }}>
            {item.recommendation_summary || 'No recommendation summary available.'}
          </Typography>

          <Divider />

          <Stack spacing={1.3}>
            <ResultField title="Skill Matches" values={item.skill_matches} color="success" />
            <ResultField title="Transferable Skills" values={item.transferable_skills} color="default" />
            <ResultField title="Experience Matches" values={item.experience_matches} color="default" />
            <ResultField title="Major Gaps" values={item.major_gaps} color="error" />
          </Stack>

          {agentEntries.length > 0 && (
            <Stack spacing={0.8}>
              <Typography variant="subtitle2" color="text.secondary">
                Agent Scores
              </Typography>
              <Stack direction="row" gap={1} flexWrap="wrap">
                {agentEntries.map(([name, scoreCard]) => (
                  <Chip
                    key={`${item.candidate_id}-${name}`}
                    label={`${name}: ${formatScore(scoreCard.score)}`}
                    size="small"
                    variant="outlined"
                  />
                ))}
              </Stack>
            </Stack>
          )}

          <Stack spacing={0.8}>
            <Typography variant="subtitle2" color="text.secondary">
              Retrieval Scores
            </Typography>
            <Stack direction="row" gap={1} flexWrap="wrap">
              {retrievalComponentEntries.map(([label, value]) => (
                <Chip
                  key={`${item.candidate_id}-${label}-retrieval-component`}
                  label={`${label}: ${formatScore(value)}`}
                  size="small"
                  variant="outlined"
                />
              ))}
            </Stack>
          </Stack>

          {item.agent_errors.length > 0 && (
            <Alert severity="warning" variant="outlined">
              Agent warnings: {item.agent_errors.join(' | ')}
            </Alert>
          )}
        </Stack>

        <Stack spacing={1.4} sx={{ minWidth: { xs: '100%', md: 260 } }}>
          <Typography variant="subtitle2" color="text.secondary">
            Integrated Final Score
          </Typography>
          <Typography variant="h5" color="primary.main">
            {formatScore(item.final_score)}
          </Typography>
          <LinearProgress variant="determinate" value={toPercent(item.final_score)} sx={{ height: 8, borderRadius: 999 }} />

          <Divider />

          <MetricRow label="Retrieval" value={item.retrieval_final_score} />
          <MetricRow label="Agent score" value={item.fr04_overall_score} />

          <Button variant="contained" size="small" onClick={() => onOpenCandidateDetail(item.candidate_id)}>
            View Detail
          </Button>
          <Button variant="outlined" size="small" onClick={() => onOpenScoreDetails(item)}>
            View Score Details
          </Button>
        </Stack>
      </Stack>
    </Paper>
  )
}

function App() {
  const [form, setForm] = useState<FormState>(DEFAULT_FORM)
  const [responseData, setResponseData] = useState<SearchResponsePayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>('')
  const [selectedCandidate, setSelectedCandidate] = useState<SearchResultItem | null>(null)
  const [isScoreDialogOpen, setIsScoreDialogOpen] = useState(false)
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false)
  const [detailCandidateId, setDetailCandidateId] = useState<string | null>(null)
  const [candidateDetail, setCandidateDetail] = useState<CandidateDetailPayload | null>(null)
  const [candidateResumeRaw, setCandidateResumeRaw] = useState<CandidateResumeRawPayload | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const skillSuggest = useEscoSuggest('skill')
  const occupationSuggest = useEscoSuggest('occupation')
  const industrySuggest = useEscoSuggest('industry')

  const validationError = useMemo(() => {
    const query = form.queryText.trim()
    if (!query) {
      return 'Please enter the job requirement text.'
    }

    const minExperience = parseOptionalNumber(form.experienceMinMonths)
    const maxExperience = parseOptionalNumber(form.experienceMaxMonths)
    if (minExperience !== null && maxExperience !== null && minExperience > maxExperience) {
      return 'Experience minimum must be less than or equal to maximum.'
    }

    const minEducation = parseOptionalNumber(form.educationMinRank)
    const maxEducation = parseOptionalNumber(form.educationMaxRank)
    if (minEducation !== null && maxEducation !== null && minEducation > maxEducation) {
      return 'Education minimum rank must be less than or equal to maximum rank.'
    }

    return ''
  }, [form])

  const handleSearch = async () => {
    setError('')
    setSelectedCandidate(null)
    setIsScoreDialogOpen(false)
    setIsDetailDialogOpen(false)
    setDetailCandidateId(null)
    setCandidateDetail(null)
    setCandidateResumeRaw(null)
    setDetailLoading(false)
    setDetailError('')

    if (validationError) {
      setError(validationError)
      return
    }

    setLoading(true)
    try {
      const payload = buildPayload(form)
      const response = await postSearch(payload)
      setResponseData(response)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unexpected error occurred.')
    } finally {
      setLoading(false)
    }
  }

  const handleOpenCandidateDetail = async (candidateId: string) => {
    setIsDetailDialogOpen(true)
    setDetailCandidateId(candidateId)
    setCandidateDetail(null)
    setCandidateResumeRaw(null)
    setDetailError('')
    setDetailLoading(true)

    try {
      const [detail, resume] = await Promise.all([getCandidateDetail(candidateId), getCandidateResumeRaw(candidateId)])
      setCandidateDetail(detail)
      setCandidateResumeRaw(resume)
    } catch (caught) {
      setDetailError(caught instanceof Error ? caught.message : 'Failed to load candidate detail.')
    } finally {
      setDetailLoading(false)
    }
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Stack spacing={2.5}>
        <Paper sx={{ p: 2.6 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ xs: 'flex-start', md: 'center' }}>
            <Stack spacing={0.5} sx={{ flexGrow: 1 }}>
              <Typography variant="subtitle2" color="primary.main">
                RECRUITMENT OPS / SEARCH CONSOLE
              </Typography>
              <Typography variant="h4">Candidate Search Interface</Typography>
              <Typography variant="body2" color="text.secondary">
                Enter natural language requirements, tune hard filters, and inspect ranked candidate responses from
                `/search`.
              </Typography>
            </Stack>
            <Chip label="FR-09 MVP" color="primary" variant="outlined" />
          </Stack>
        </Paper>

        <Stack direction={{ xs: 'column', xl: 'row' }} spacing={2.2} alignItems="stretch">
          <Paper sx={{ p: 2.4, flex: { xs: '1 1 auto', xl: '0 0 460px' } }}>
            <Stack spacing={2}>
              <Typography variant="h5">Input</Typography>

              <TextField
                label="Natural Language Requirement"
                placeholder="Example: Senior backend engineer with Python, FastAPI, and distributed systems experience"
                value={form.queryText}
                multiline
                minRows={3}
                onChange={(event) => setForm((current) => ({ ...current, queryText: event.target.value }))}
                fullWidth
              />

              <Autocomplete
                multiple
                disablePortal
                filterOptions={(options) => options}
                options={skillSuggest.options}
                value={form.skillTerms}
                inputValue={skillSuggest.inputValue}
                loading={skillSuggest.loading}
                getOptionLabel={(option) => option.label}
                isOptionEqualToValue={(option, value) => option.esco_id === value.esco_id}
                onInputChange={(_, next) => skillSuggest.setInputValue(next)}
                onChange={(_, next) => setForm((current) => ({ ...current, skillTerms: normalizeEscoOptions(next) }))}
                noOptionsText={
                  skillSuggest.inputValue.trim().length < ESCO_MIN_QUERY_LENGTH
                    ? 'Type at least 2 characters'
                    : 'No ESCO skill candidates'
                }
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Skill Terms"
                    placeholder="Type to search ESCO skills"
                    fullWidth
                  />
                )}
              />

              <Autocomplete
                multiple
                disablePortal
                filterOptions={(options) => options}
                options={occupationSuggest.options}
                value={form.occupationTerms}
                inputValue={occupationSuggest.inputValue}
                loading={occupationSuggest.loading}
                getOptionLabel={(option) => option.label}
                isOptionEqualToValue={(option, value) => option.esco_id === value.esco_id}
                onInputChange={(_, next) => occupationSuggest.setInputValue(next)}
                onChange={(_, next) =>
                  setForm((current) => ({ ...current, occupationTerms: normalizeEscoOptions(next) }))
                }
                noOptionsText={
                  occupationSuggest.inputValue.trim().length < ESCO_MIN_QUERY_LENGTH
                    ? 'Type at least 2 characters'
                    : 'No ESCO occupation candidates'
                }
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Occupation Terms"
                    placeholder="Type to search ESCO occupations"
                    fullWidth
                  />
                )}
              />

              <Autocomplete
                multiple
                disablePortal
                filterOptions={(options) => options}
                options={industrySuggest.options}
                value={form.industryTerms}
                inputValue={industrySuggest.inputValue}
                loading={industrySuggest.loading}
                getOptionLabel={(option) => option.label}
                isOptionEqualToValue={(option, value) => option.esco_id === value.esco_id}
                onInputChange={(_, next) => industrySuggest.setInputValue(next)}
                onChange={(_, next) => setForm((current) => ({ ...current, industryTerms: normalizeEscoOptions(next) }))}
                noOptionsText={
                  industrySuggest.inputValue.trim().length < ESCO_MIN_QUERY_LENGTH
                    ? 'Type at least 2 characters'
                    : 'No ESCO industry candidates'
                }
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Industry Terms"
                    placeholder="Type to search ESCO industries"
                    fullWidth
                  />
                )}
              />

              <Autocomplete
                multiple
                freeSolo
                disablePortal
                options={LOCATION_OPTIONS}
                value={form.locations}
                onChange={(_, next) => setForm((current) => ({ ...current, locations: normalizeTerms(next) }))}
                renderInput={(params) => <TextField {...params} label="Locations" placeholder="Add location" fullWidth />}
              />

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.2}>
                <TextField
                  label="Experience Min (months)"
                  type="number"
                  inputProps={{ min: 0 }}
                  value={form.experienceMinMonths}
                  onChange={(event) => setForm((current) => ({ ...current, experienceMinMonths: event.target.value }))}
                  fullWidth
                />
                <TextField
                  label="Experience Max (months)"
                  type="number"
                  inputProps={{ min: 0 }}
                  value={form.experienceMaxMonths}
                  onChange={(event) => setForm((current) => ({ ...current, experienceMaxMonths: event.target.value }))}
                  fullWidth
                />
              </Stack>

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.2}>
                <TextField
                  select
                  label="Education Min Rank"
                  value={form.educationMinRank}
                  onChange={(event) => setForm((current) => ({ ...current, educationMinRank: event.target.value }))}
                  fullWidth
                >
                  {EDUCATION_RANK_OPTIONS.map((option) => (
                    <MenuItem key={`edu-min-${option.value}`} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </TextField>

                <TextField
                  select
                  label="Education Max Rank"
                  value={form.educationMaxRank}
                  onChange={(event) => setForm((current) => ({ ...current, educationMaxRank: event.target.value }))}
                  fullWidth
                >
                  {EDUCATION_RANK_OPTIONS.map((option) => (
                    <MenuItem key={`edu-max-${option.value}`} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </TextField>
              </Stack>

              <Box>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.7 }}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Result Limit
                  </Typography>
                  <Typography variant="subtitle2">{form.limit}</Typography>
                </Stack>
                <Slider
                  value={form.limit}
                  min={1}
                  max={50}
                  marks={[
                    { value: 1, label: '1' },
                    { value: 20, label: '20' },
                    { value: 50, label: '50' },
                  ]}
                  onChange={(_, next) => {
                    if (typeof next === 'number') {
                      setForm((current) => ({ ...current, limit: next }))
                    }
                  }}
                />
              </Box>

              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.2}>
                <Button
                  variant="contained"
                  color="primary"
                  onClick={handleSearch}
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={16} color="inherit" /> : undefined}
                  sx={{ flex: 1 }}
                >
                  {loading ? 'Searching...' : 'Run Search'}
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => {
                    setForm(DEFAULT_FORM)
                    setError('')
                    setResponseData(null)
                    setSelectedCandidate(null)
                    setIsScoreDialogOpen(false)
                    setIsDetailDialogOpen(false)
                    setDetailCandidateId(null)
                    setCandidateDetail(null)
                    setCandidateResumeRaw(null)
                    setDetailLoading(false)
                    setDetailError('')
                    skillSuggest.clear()
                    occupationSuggest.clear()
                    industrySuggest.clear()
                  }}
                  disabled={loading}
                  sx={{ flex: 1 }}
                >
                  Reset
                </Button>
              </Stack>
            </Stack>
          </Paper>

          <Paper sx={{ p: 2.4, flex: 1, minHeight: 620 }}>
            <Stack spacing={2}>
              <Typography variant="h5">Search Response</Typography>

              {error && <Alert severity="error">{error}</Alert>}

              {loading && (
                <Stack spacing={1.2}>
                  <LinearProgress />
                  <Typography variant="body2" color="text.secondary">
                    Querying `/search` endpoint...
                  </Typography>
                </Stack>
              )}

              {!loading && !responseData && !error && (
                <Alert severity="info" variant="outlined">
                  Submit a query to display ranked candidates.
                </Alert>
              )}

              {responseData && (
                <Stack spacing={1.4}>
                  <Paper sx={{ p: 1.6 }}>
                    <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} justifyContent="space-between">
                      <Typography variant="subtitle2">
                        Results: <strong>{responseData.results.length}</strong>
                      </Typography>
                      <Typography variant="subtitle2">
                        Retry Required: <strong>{responseData.retry_required ? 'Yes' : 'No'}</strong>
                      </Typography>
                    </Stack>
                    {responseData.conflict_reason ? (
                      <Typography variant="body2" color="warning.main" sx={{ mt: 0.8 }}>
                        Conflict reason: {responseData.conflict_reason}
                      </Typography>
                    ) : null}
                    {responseData.conflict_fields.length > 0 ? (
                      <Typography variant="body2" color="warning.main">
                        Conflict fields: {responseData.conflict_fields.join(', ')}
                      </Typography>
                    ) : null}
                  </Paper>

                  {responseData.results.length === 0 && (
                    <Alert severity="warning" variant="outlined">
                      The API returned no candidates for this query.
                    </Alert>
                  )}

                  <Stack spacing={1.4}>
                    {responseData.results.map((item, index) => (
                      <CandidateCard
                        key={`${item.candidate_id}-${item.rank}-${index}`}
                        item={item}
                        onOpenScoreDetails={(next) => {
                          setSelectedCandidate(next)
                          setIsScoreDialogOpen(true)
                        }}
                        onOpenCandidateDetail={handleOpenCandidateDetail}
                      />
                    ))}
                  </Stack>
                </Stack>
              )}
            </Stack>
          </Paper>
        </Stack>
      </Stack>

      <CandidateDetailDialog
        open={isDetailDialogOpen}
        candidateId={detailCandidateId}
        detail={candidateDetail}
        resumeRaw={candidateResumeRaw}
        loading={detailLoading}
        error={detailError}
        onClose={() => {
          setIsDetailDialogOpen(false)
          setDetailCandidateId(null)
          setCandidateDetail(null)
          setCandidateResumeRaw(null)
          setDetailLoading(false)
          setDetailError('')
        }}
      />
      <ScoreDetailDialog
        open={isScoreDialogOpen}
        candidate={selectedCandidate}
        onClose={() => {
          setIsScoreDialogOpen(false)
          setSelectedCandidate(null)
        }}
      />
    </Container>
  )
}

export default App
