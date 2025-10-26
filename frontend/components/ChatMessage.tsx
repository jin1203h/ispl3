'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { SearchResult } from '@/lib/api';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  searchResults?: SearchResult[];
}

interface ChatMessageProps {
  message: Message;
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        {/* 메시지 내용 */}
        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        ) : (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                // 링크 스타일링
                a: ({ node, ...props }) => (
                  <a
                    {...props}
                    className="text-blue-600 hover:underline"
                    target="_blank"
                    rel="noopener noreferrer"
                  />
                ),
                // 코드 블록 스타일링
                code: ({ node, inline, ...props }: any) =>
                  inline ? (
                    <code
                      {...props}
                      className="rounded bg-gray-200 px-1 py-0.5 font-mono text-sm"
                    />
                  ) : (
                    <code
                      {...props}
                      className="block rounded bg-gray-200 p-2 font-mono text-sm"
                    />
                  ),
                // 리스트 스타일링
                ul: ({ node, ...props }) => (
                  <ul {...props} className="list-disc pl-5 space-y-1" />
                ),
                ol: ({ node, ...props }) => (
                  <ol {...props} className="list-decimal pl-5 space-y-1" />
                ),
                // 제목 스타일링
                h1: ({ node, ...props }) => (
                  <h1 {...props} className="text-xl font-bold mt-4 mb-2" />
                ),
                h2: ({ node, ...props }) => (
                  <h2 {...props} className="text-lg font-bold mt-3 mb-2" />
                ),
                h3: ({ node, ...props }) => (
                  <h3 {...props} className="text-base font-bold mt-2 mb-1" />
                ),
                // 단락 스타일링
                p: ({ node, ...props }) => (
                  <p {...props} className="mb-2 last:mb-0" />
                ),
                // 강조 텍스트
                strong: ({ node, ...props }) => (
                  <strong {...props} className="font-bold" />
                ),
                // 인용구
                blockquote: ({ node, ...props }) => (
                  <blockquote
                    {...props}
                    className="border-l-4 border-gray-300 pl-4 italic"
                  />
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* 타임스탬프 */}
        <p
          className={`mt-1 text-xs ${
            isUser ? 'text-blue-100' : 'text-gray-500'
          }`}
        >
          {message.timestamp.toLocaleTimeString('ko-KR', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </p>
      </div>
    </div>
  );
}

