export type AgentScoreCard = {
  score: number
  breakdown: Record<string, number>
  reason: string
}

export type SearchRequestPayload = {
  query_text: string
  skill_terms: string[]
  occupation_terms: string[]
  industry_terms: string[]
  experience_min_months: number | null
  experience_max_months: number | null
  education_min_rank: number | null
  education_max_rank: number | null
  locations: string[]
  limit: number
}

export type SearchResultItem = {
  candidate_id: string
  rank: number
  keyword_score: number
  vector_score: number
  fusion_score: number
  cross_encoder_score: number
  retrieval_final_score: number
  fr04_overall_score: number
  final_score: number
  recommendation_summary: string
  skill_matches: string[]
  transferable_skills: string[]
  experience_matches: string[]
  major_gaps: string[]
  agent_scores: Record<string, AgentScoreCard>
  agent_errors: string[]
}

export type SearchResponsePayload = {
  retry_required: boolean
  conflict_fields: string[]
  conflict_reason: string
  results: SearchResultItem[]
}

export type CandidateDetailPayload = {
  candidate_id: string
  source_dataset: string
  source_record_id: string
  current_location: string
  category: string
  resume_text: string
  occupation_candidates: Record<string, unknown>[]
  skill_candidates: Record<string, unknown>[]
  experiences: Record<string, unknown>[]
  educations: Record<string, unknown>[]
}

export type CandidateResumeRawPayload = {
  candidate_id: string
  source_dataset: string
  source_record_id: string
  resume_text: string
}
