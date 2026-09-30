export interface KnowledgeStatus {
  ready: boolean
  code: string
  message: string
  document_count: number
  chunk_count: number
  embedding_model: string | null
  dimensions: number | null
}

export interface KnowledgeChunk {
  chunk_id: string
  document_id: string
  title: string
  source: string
  section: string
  ordinal: number
  content: string
  content_hash: string
  document_hash: string
  similarity: number
}

export interface RetrievalResult {
  question: string
  top_k: number
  min_similarity: number
  chunks: KnowledgeChunk[]
}

export interface AnswerResult extends RetrievalResult {
  status: 'answered' | 'insufficient_evidence'
  answer: string
  citations: KnowledgeChunk[]
}
