'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { SearchResult } from '@/lib/api';

interface ReferencePanelProps {
  searchResults: SearchResult[];
  isOpen: boolean;
  onToggle: () => void;
}

export default function ReferencePanel({
  searchResults,
  isOpen,
  onToggle,
}: ReferencePanelProps) {
  const [selectedChunk, setSelectedChunk] = useState<SearchResult | null>(null);

  // 참조 패널이 닫힌 경우 아무것도 렌더링하지 않음
  if (!isOpen) {
    return null;
  }

  return (
    <>
      {/* Desktop: 우측 패널 */}
      <div className="hidden md:flex md:flex-col md:w-[400px] border-l border-gray-200 bg-white overflow-hidden">
        {/* 헤더 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <span>📚</span>
            <span>참조 문서</span>
          </h2>
          <button
            onClick={onToggle}
            className="text-gray-500 hover:text-gray-700 transition-colors"
            title="패널 닫기"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* 참조 목록 또는 상세 내용 */}
        <div className="flex-1 overflow-y-auto">
          {selectedChunk ? (
            // 상세 내용 표시
            <div className="p-4">
              {/* 뒤로 가기 버튼 */}
              <button
                onClick={() => setSelectedChunk(null)}
                className="flex items-center gap-2 text-blue-600 hover:text-blue-700 mb-4"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 19l-7-7 7-7"
                  />
                </svg>
                <span className="text-sm">목록으로</span>
              </button>

              {/* 메타 정보 */}
              <div className="bg-gray-50 rounded-lg p-3 mb-4">
                <div className="text-sm text-gray-600 space-y-1">
                  <div>
                    <span className="font-medium">문서:</span>{' '}
                    {selectedChunk.document.filename}
                  </div>
                  {selectedChunk.page_number && (
                    <div>
                      <span className="font-medium">페이지:</span>{' '}
                      {selectedChunk.page_number}
                    </div>
                  )}
                  {/* {selectedChunk.clause_number && (
                    <div>
                      <span className="font-medium">조항:</span>{' '}
                      {selectedChunk.clause_number}
                    </div>
                  )}
                  <div>
                    <span className="font-medium">유사도:</span>{' '}
                    {(selectedChunk.similarity * 100).toFixed(1)}%
                  </div> */}
                </div>
              </div>

              {/* 내용 (Markdown) */}
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {selectedChunk.content}
                </ReactMarkdown>
              </div>
            </div>
          ) : (
            // 참조 목록 표시
            <div className="p-4 space-y-3">
              {searchResults.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <p className="text-sm">참조 문서가 없습니다</p>
                </div>
              ) : (
                searchResults.map((result, index) => (
                  <button
                    key={result.chunk_id}
                    onClick={() => setSelectedChunk(result)}
                    className="w-full text-left bg-white border border-gray-200 rounded-lg p-3 hover:border-blue-500 hover:shadow-md transition-all"
                  >
                    {/* 참조 번호 */}
                    <div className="flex items-start gap-2 mb-2">
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold flex-shrink-0">
                        {index + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {result.document.filename}
                        </p>
                      </div>
                    </div>

                    {/* 메타 정보 */}
                    <div className="text-xs text-gray-600 space-y-1 ml-8">
                      {result.page_number && (
                        <div className="flex items-center gap-1">
                          <span className="text-gray-500">📄</span>
                          <span>페이지 {result.page_number}</span>
                        </div>
                      )}
                      {/* {result.clause_number && (
                        <div className="flex items-center gap-1">
                          <span className="text-gray-500">📋</span>
                          <span>{result.clause_number}</span>
                        </div>
                      )}
                      <div className="flex items-center gap-1">
                        <span className="text-gray-500">🎯</span>
                        <span>
                          유사도: {(result.similarity * 100).toFixed(1)}%
                        </span>
                      </div> */}
                    </div>

                    {/* 내용 미리보기 */}
                    <p className="text-xs text-gray-600 mt-2 ml-8 line-clamp-2">
                      {result.content.substring(0, 100)}...
                    </p>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Mobile: 하단 시트 */}
      <div className="md:hidden fixed inset-0 z-50 bg-black bg-opacity-50">
        <div
          className="absolute bottom-0 left-0 right-0 bg-white rounded-t-xl max-h-[70vh] flex flex-col"
          onClick={(e) => e.stopPropagation()}
        >
          {/* 드래그 핸들 */}
          <div className="flex justify-center py-2">
            <div className="w-12 h-1 bg-gray-300 rounded-full" />
          </div>

          {/* 헤더 */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <span>📚</span>
              <span>참조 문서</span>
            </h2>
            <button
              onClick={onToggle}
              className="text-gray-500 hover:text-gray-700"
            >
              <svg
                className="w-6 h-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* 내용 */}
          <div className="flex-1 overflow-y-auto">
            {selectedChunk ? (
              // 상세 내용 (모바일)
              <div className="p-4">
                <button
                  onClick={() => setSelectedChunk(null)}
                  className="flex items-center gap-2 text-blue-600 mb-4"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 19l-7-7 7-7"
                    />
                  </svg>
                  <span className="text-sm">목록으로</span>
                </button>

                <div className="bg-gray-50 rounded-lg p-3 mb-4">
                  <div className="text-sm text-gray-600 space-y-1">
                    <div>
                      <span className="font-medium">문서:</span>{' '}
                      {selectedChunk.document.filename}
                    </div>
                    {selectedChunk.page_number && (
                      <div>
                        <span className="font-medium">페이지:</span>{' '}
                        {selectedChunk.page_number}
                      </div>
                    )}
                    {/* {selectedChunk.clause_number && (
                      <div>
                        <span className="font-medium">조항:</span>{' '}
                        {selectedChunk.clause_number}
                      </div>
                    )}
                    <div>
                      <span className="font-medium">유사도:</span>{' '}
                      {(selectedChunk.similarity * 100).toFixed(1)}%
                    </div> */}
                  </div>
                </div>

                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {selectedChunk.content}
                  </ReactMarkdown>
                </div>
              </div>
            ) : (
              // 참조 목록 (모바일)
              <div className="p-4 space-y-3">
                {searchResults.length === 0 ? (
                  <div className="text-center text-gray-500 py-8">
                    <p className="text-sm">참조 문서가 없습니다</p>
                  </div>
                ) : (
                  searchResults.map((result, index) => (
                    <button
                      key={result.chunk_id}
                      onClick={() => setSelectedChunk(result)}
                      className="w-full text-left bg-white border border-gray-200 rounded-lg p-3 active:border-blue-500"
                    >
                      <div className="flex items-start gap-2 mb-2">
                        <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold flex-shrink-0">
                          {index + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {result.document.filename}
                          </p>
                        </div>
                      </div>

                      <div className="text-xs text-gray-600 space-y-1 ml-8">
                        {result.page_number && (
                          <div>📄 페이지 {result.page_number}</div>
                        )}
                        {/* {result.clause_number && (
                          <div>📋 {result.clause_number}</div>
                        )}
                        <div>
                          🎯 유사도: {(result.similarity * 100).toFixed(1)}%
                        </div> */}
                      </div>

                      <p className="text-xs text-gray-600 mt-2 ml-8 line-clamp-2">
                        {result.content.substring(0, 100)}...
                      </p>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
