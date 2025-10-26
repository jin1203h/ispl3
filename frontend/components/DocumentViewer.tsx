'use client';

import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { viewDocument, DocumentContent } from '@/lib/api';

interface Props {
  isOpen: boolean;
  documentId: number;
  fileType: 'pdf' | 'markdown';
  onClose: () => void;
}

export default function DocumentViewer({ isOpen, documentId, fileType, onClose }: Props) {
  const [content, setContent] = useState<DocumentContent | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadDocument();
    }
  }, [isOpen, documentId, fileType]);

  const loadDocument = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await viewDocument(documentId, fileType);
      setContent(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '문서 로드 실패');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="w-full max-w-4xl h-[90vh] rounded-lg bg-white shadow-xl flex flex-col">
        {/* 헤더 */}
        <div className="flex items-center justify-between border-b p-4">
          <h2 className="text-lg font-bold text-gray-900">
            {content?.filename || '문서 보기'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
            aria-label="닫기"
          >
            ✕
          </button>
        </div>

        {/* 콘텐츠 */}
        <div className={`flex-1 ${content?.type === 'pdf' && !isLoading && !error ? 'p-0' : 'p-6 overflow-auto'}`}>
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
              <span className="ml-3 text-gray-600">로딩 중...</span>
            </div>
          )}

          {error && !isLoading && (
            <div className="rounded-lg bg-red-50 p-4">
              <p className="text-red-600">⚠️ {error}</p>
            </div>
          )}

          {content && content.type === 'markdown' && !isLoading && !error && (
            <ReactMarkdown remarkPlugins={[remarkGfm]} className="prose max-w-none">
              {content.content || ''}
            </ReactMarkdown>
          )}

          {content && content.type === 'pdf' && !isLoading && !error && (
            <iframe
              src={content.url}
              className="w-full h-full border-0"
              title="PDF Viewer"
            />
          )}
        </div>
      </div>
    </div>
  );
}

