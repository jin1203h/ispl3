'use client';

import { useState, useEffect } from 'react';
import {
  ChatSession,
  listChatSessions,
  deleteChatSession,
  updateChatSessionTitle,
} from '@/lib/api';

interface ChatHistoryProps {
  onSelectSession?: (threadId: string) => void;
  selectedThreadId?: string;
}

export default function ChatHistory({
  onSelectSession,
  selectedThreadId,
}: ChatHistoryProps) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  // 세션 목록 로드
  const loadSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await listChatSessions();
      setSessions(response.sessions);
    } catch (err) {
      setError(err instanceof Error ? err.message : '세션 목록 로드 실패');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  // 세션 선택
  const handleSelectSession = (threadId: string) => {
    if (onSelectSession) {
      onSelectSession(threadId);
    }
  };

  // 제목 수정 시작
  const handleStartEdit = (session: ChatSession) => {
    setEditingId(session.thread_id);
    setEditTitle(session.title);
  };

  // 제목 수정 저장
  const handleSaveEdit = async (threadId: string) => {
    if (!editTitle.trim()) {
      return;
    }

    try {
      await updateChatSessionTitle(threadId, editTitle.trim());
      await loadSessions();
      setEditingId(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : '제목 수정 실패');
    }
  };

  // 제목 수정 취소
  const handleCancelEdit = () => {
    setEditingId(null);
    setEditTitle('');
  };

  // 세션 삭제 확인
  const handleDeleteClick = (threadId: string) => {
    setDeleteConfirm(threadId);
  };

  // 세션 삭제 실행
  const handleDeleteConfirm = async () => {
    if (!deleteConfirm) return;

    try {
      await deleteChatSession(deleteConfirm);
      await loadSessions();
      setDeleteConfirm(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : '세션 삭제 실패');
    }
  };

  // 날짜 포맷팅
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return `오늘 ${date.toLocaleTimeString('ko-KR', {
        hour: '2-digit',
        minute: '2-digit',
      })}`;
    } else if (diffDays === 1) {
      return `어제 ${date.toLocaleTimeString('ko-KR', {
        hour: '2-digit',
        minute: '2-digit',
      })}`;
    } else if (diffDays < 7) {
      return `${diffDays}일 전`;
    } else {
      return date.toLocaleDateString('ko-KR', {
        month: 'short',
        day: 'numeric',
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">로딩 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-700 text-sm">{error}</p>
          <button
            onClick={loadSessions}
            className="mt-2 text-sm text-red-600 hover:text-red-800 font-medium"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center px-4">
          <div className="text-5xl mb-3">💬</div>
          <p className="text-gray-600 text-sm">저장된 대화가 없습니다</p>
          <p className="text-gray-500 text-xs mt-1">
            AI 채팅을 시작해보세요
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* 헤더 */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">대화 이력</h2>
          <button
            onClick={loadSessions}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
            title="새로고침"
          >
            <svg
              className="w-4 h-4 text-gray-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          총 {sessions.length}개의 대화
        </p>
      </div>

      {/* 세션 목록 */}
      <div className="flex-1 overflow-y-auto">
        <ul className="divide-y divide-gray-200">
          {sessions.map((session) => (
            <li key={session.thread_id} className="relative">
              {/* 세션 항목 */}
              <div
                className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                  selectedThreadId === session.thread_id ? 'bg-blue-50' : ''
                }`}
                onClick={() =>
                  editingId !== session.thread_id &&
                  handleSelectSession(session.thread_id)
                }
              >
                {/* 편집 모드 */}
                {editingId === session.thread_id ? (
                  <div className="space-y-2">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          handleSaveEdit(session.thread_id);
                        } else if (e.key === 'Escape') {
                          handleCancelEdit();
                        }
                      }}
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleSaveEdit(session.thread_id)}
                        className="flex-1 px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                      >
                        저장
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="flex-1 px-3 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                      >
                        취소
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    {/* 제목 */}
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <h3 className="font-medium text-sm text-gray-900 line-clamp-2 flex-1">
                        {session.title}
                      </h3>
                      {/* 액션 버튼 */}
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStartEdit(session);
                          }}
                          className="p-1 hover:bg-gray-200 rounded"
                          title="제목 수정"
                        >
                          <svg
                            className="w-3.5 h-3.5 text-gray-600"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                            />
                          </svg>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteClick(session.thread_id);
                          }}
                          className="p-1 hover:bg-red-100 rounded"
                          title="삭제"
                        >
                          <svg
                            className="w-3.5 h-3.5 text-red-600"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                            />
                          </svg>
                        </button>
                      </div>
                    </div>

                    {/* 메타 정보 */}
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span className="flex items-center gap-1">
                        <svg
                          className="w-3.5 h-3.5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                          />
                        </svg>
                        {session.message_count}개
                      </span>
                      <span>{formatDate(session.updated_at)}</span>
                    </div>
                  </>
                )}
              </div>

              {/* 삭제 확인 모달 (인라인) */}
              {deleteConfirm === session.thread_id && (
                <div className="absolute inset-0 bg-white border-t border-b border-gray-200 flex items-center justify-center z-10">
                  <div className="text-center px-4">
                    <p className="text-sm text-gray-900 mb-3">
                      이 대화를 삭제하시겠습니까?
                    </p>
                    <div className="flex gap-2 justify-center">
                      <button
                        onClick={handleDeleteConfirm}
                        className="px-4 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
                      >
                        삭제
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(null)}
                        className="px-4 py-1.5 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                      >
                        취소
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

