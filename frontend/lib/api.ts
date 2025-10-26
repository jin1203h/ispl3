/**
 * API 클라이언트
 * Backend API와 통신하기 위한 유틸리티
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface UploadResponse {
  message: string;
  document_id: number;
  filename: string;
  pdf_path: string;
  markdown_path?: string;
  metadata: {
    total_pages?: number;
    processing_time?: number;
    similarity?: number;
    quality?: {
      completeness: number;
      consistency: number;
      accuracy: number;
      overall_score: number;
      status: string;
      issues: string[];
    };
  };
  processing_time_ms: number;
  chunks?: {
    total_chunks: number;
    text_chunks: number;
    table_chunks: number;
    total_tokens: number;
    saved_to_db: boolean;
    saved_count: number;
  };
}

export interface ApiError {
  detail: string;
}

/**
 * PDF 파일 업로드
 */
export async function uploadPDF(
  file: File,
  method: 'pymupdf' | 'vision' | 'both' = 'pymupdf',
  enableChunking: boolean = true,  // 항상 true (백엔드에서 무조건 청킹)
  onProgress?: (progress: number) => void,
  documentType?: string,
  insuranceType?: string,
  companyName?: string
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('method', method);
  
  // 추가 메타데이터
  if (documentType) formData.append('document_type', documentType);
  if (insuranceType) formData.append('insurance_type', insuranceType);
  if (companyName) formData.append('company_name', companyName);
  // enable_chunking은 백엔드에서 무조건 true이므로 전송하지 않음

  const response = await fetch(`${API_BASE_URL}/api/pdf/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || '업로드 실패');
  }

  return response.json();
}

/**
 * Health 체크
 */
export async function checkHealth(): Promise<{ status: string; database: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  
  if (!response.ok) {
    throw new Error('Health check failed');
  }

  return response.json();
}

/**
 * 채팅 요청/응답 인터페이스
 */
export interface ChatRequest {
  query: string;
  thread_id?: string;
  stream?: boolean;
}

export interface ChatResponse {
  query: string;
  answer: string;
  search_results: SearchResult[];
  task_results: {
    search?: {
      success: boolean;
      count: number;
      query: string;
    };
    answer?: {
      success: boolean;
      model: string;
      tokens_used: number;
      validation: {
        has_structure: boolean;
        has_references: boolean;
        has_clause_numbers: boolean;
        warnings: string[];
      };
    };
  };
  error?: string | null;
}

export interface SearchResult {
  chunk_id: number;
  document_id: number;
  content: string;
  similarity: number;
  chunk_type: string;
  page_number?: number;
  section_title?: string;
  clause_number?: string;
  metadata: Record<string, any>;
  document: {
    filename: string;
    document_type?: string;
    company_name?: string;
  };
}

/**
 * 채팅 메시지 전송
 */
export async function sendChatMessage(
  query: string,
  threadId: string = 'default'
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      query,
      thread_id: threadId,
      stream: false,
    } as ChatRequest),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || '채팅 요청 실패');
  }

  return response.json();
}

/**
 * 문서 관리 API
 */

export interface ListDocumentsParams {
  filename?: string;
  document_type?: string;
  company_name?: string;
  status?: string;
  sort_by?: 'created_at' | 'filename';
  sort_order?: 'asc' | 'desc';
  offset?: number;
  limit?: number;
}

export interface DocumentItem {
  id: number;
  filename: string;
  document_type?: string;
  company_name?: string;
  status: string;
  created_at: string;
  total_pages?: number;
  total_chunks?: number;
}

export interface ListDocumentsResponse {
  documents: DocumentItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface DocumentContent {
  type: 'pdf' | 'markdown';
  content?: string;
  url?: string;
  filename: string;
  document_id: number;
  file_size?: number;
  total_pages?: number;
}

/**
 * 문서 목록 조회 (필터링, 정렬, 페이지네이션)
 */
export async function listDocuments(params?: ListDocumentsParams): Promise<ListDocumentsResponse> {
  const queryParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        queryParams.append(key, String(value));
      }
    });
  }
  
  const response = await fetch(`${API_BASE_URL}/api/documents?${queryParams}`);
  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || '문서 목록 조회 실패');
  }
  
  return response.json();
}

/**
 * 문서 삭제
 */
export async function deleteDocument(id: number): Promise<{ success: boolean; message?: string }> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${id}`, {
    method: 'DELETE',
  });
  
  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || '문서 삭제 실패');
  }
  
  return response.json();
}

/**
 * 문서 다운로드 URL 생성
 */
export function getDocumentDownloadUrl(id: number, fileType: 'pdf' | 'markdown'): string {
  return `${API_BASE_URL}/api/documents/${id}/download?file_type=${fileType}`;
}

/**
 * 문서 조회 (뷰어용)
 */
export async function viewDocument(id: number, fileType: 'pdf' | 'markdown'): Promise<DocumentContent> {
  const response = await fetch(`${API_BASE_URL}/api/documents/${id}/view?file_type=${fileType}`);
  
  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || '문서 조회 실패');
  }
  
  const data = await response.json();
  
  // PDF의 경우 상대 경로를 절대 경로로 변환
  if (data.type === 'pdf' && data.url && data.url.startsWith('/')) {
    data.url = `${API_BASE_URL}${data.url}`;
  }
  
  return data;
}

/**
 * ====================================
 * 대화 이력 API
 * ====================================
 */

export interface ChatSession {
  id: number;
  thread_id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  message_metadata?: Record<string, any>;
  created_at: string;
}

export interface ChatSessionsResponse {
  success: boolean;
  sessions: ChatSession[];
  total: number;
  offset: number;
  limit: number;
}

export interface ChatMessagesResponse {
  success: boolean;
  messages: ChatMessage[];
}

/**
 * 대화 세션 목록 조회
 */
export async function listChatSessions(
  userId?: number,
  limit: number = 20,
  offset: number = 0
): Promise<ChatSessionsResponse> {
  const params = new URLSearchParams();
  if (userId) params.append('user_id', userId.toString());
  params.append('limit', limit.toString());
  params.append('offset', offset.toString());
  
  const response = await fetch(`${API_BASE_URL}/api/chat/history/sessions?${params}`);
  
  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || '세션 목록 조회 실패');
  }
  
  return response.json();
}

/**
 * 대화 메시지 조회
 */
export async function getChatMessages(
  threadId: string,
  limit?: number
): Promise<ChatMessagesResponse> {
  const params = new URLSearchParams();
  if (limit) params.append('limit', limit.toString());
  
  const response = await fetch(
    `${API_BASE_URL}/api/chat/history/sessions/${threadId}/messages?${params}`
  );
  
  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || '메시지 조회 실패');
  }
  
  return response.json();
}

/**
 * 대화 세션 제목 업데이트
 */
export async function updateChatSessionTitle(
  threadId: string,
  title: string
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/history/sessions/${threadId}`,
    {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title }),
    }
  );
  
  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || '제목 업데이트 실패');
  }
  
  return response.json();
}

/**
 * 대화 세션 삭제
 */
export async function deleteChatSession(
  threadId: string
): Promise<{ success: boolean; message: string }> {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/history/sessions/${threadId}`,
    {
      method: 'DELETE',
    }
  );
  
  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || '세션 삭제 실패');
  }
  
  return response.json();
}

/**
 * 메시지 저장
 */
export async function saveChatMessage(
  threadId: string,
  role: 'user' | 'assistant' | 'system',
  content: string,
  message_metadata?: Record<string, any>
): Promise<{ success: boolean; message: ChatMessage }> {
  const response = await fetch(
    `${API_BASE_URL}/api/chat/history/messages`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        thread_id: threadId,
        role,
        content,
        message_metadata,
      }),
    }
  );
  
  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || '메시지 저장 실패');
  }
  
  return response.json();
}


