'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import AppLayout from '@/components/AppLayout';
import ChatMessage, { Message } from '@/components/ChatMessage';
import ChatInput from '@/components/ChatInput';
import ReferencePanel from '@/components/ReferencePanel';
import { 
  sendChatMessage, 
  SearchResult, 
  getChatMessages, 
  saveChatMessage 
} from '@/lib/api';

// UUID v4 생성 함수
function generateThreadId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export default function ChatPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [selectedSearchResults, setSelectedSearchResults] = useState<SearchResult[]>([]);
  const [threadId, setThreadId] = useState<string>('');
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 자동 스크롤
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 초기화: thread_id 설정 및 이전 대화 로드
  useEffect(() => {
    const urlThreadId = searchParams?.get('thread_id');
    
    if (urlThreadId) {
      // URL에서 thread_id 로드
      setThreadId(urlThreadId);
      loadChatHistory(urlThreadId);
    } else {
      // 새 세션 생성
      const newThreadId = generateThreadId();
      setThreadId(newThreadId);
    }
  }, [searchParams]);

  // 대화 이력 로드
  const loadChatHistory = async (tid: string) => {
    try {
      setIsLoadingHistory(true);
      const response = await getChatMessages(tid);
      
      if (response.messages && response.messages.length > 0) {
        // DB 메시지를 Message 형식으로 변환
        const loadedMessages: Message[] = response.messages.map((msg) => ({
          id: msg.id.toString(),
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
          timestamp: new Date(msg.created_at),
          searchResults: msg.message_metadata?.search_results,
        }));
        setMessages(loadedMessages);
        
        // 마지막 메시지의 search_results가 있으면 패널 열기
        const lastMsg = loadedMessages[loadedMessages.length - 1];
        if (lastMsg.searchResults && lastMsg.searchResults.length > 0) {
          setSelectedSearchResults(lastMsg.searchResults);
          setIsPanelOpen(true);
        }
      }
    } catch (err) {
      console.error('대화 이력 로드 오류:', err);
      // 로드 실패 시 조용히 처리 (새 대화 시작 가능)
    } finally {
      setIsLoadingHistory(false);
    }
  };

  // 메시지 전송
  const handleSendMessage = async (content: string) => {
    if (!threadId) {
      setError('세션이 초기화되지 않았습니다');
      return;
    }

    // 사용자 메시지 추가
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      // 사용자 메시지 DB 저장 (백그라운드)
      saveChatMessage(threadId, 'user', content).catch((err) =>
        console.error('사용자 메시지 저장 실패:', err)
      );

      // API 호출
      const response = await sendChatMessage(content);

      // AI 응답 메시지 추가 (searchResults 포함)
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        timestamp: new Date(),
        searchResults: response.search_results,
      };
      setMessages((prev) => [...prev, assistantMessage]);

      // AI 응답 메시지 DB 저장 (백그라운드)
      saveChatMessage(threadId, 'assistant', response.answer, {
        search_results: response.search_results,
        preprocessing: response.preprocessing,
        validation: response.validation,
      }).catch((err) => console.error('AI 메시지 저장 실패:', err));

      // 참조 문서 패널 업데이트
      if (response.search_results && response.search_results.length > 0) {
        setSelectedSearchResults(response.search_results);
        setIsPanelOpen(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '오류가 발생했습니다');

      // 오류 메시지도 표시
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `죄송합니다. 오류가 발생했습니다: ${
          err instanceof Error ? err.message : '알 수 없는 오류'
        }`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // 새 대화 시작
  const handleNewChat = () => {
    const newThreadId = generateThreadId();
    setThreadId(newThreadId);
    setMessages([]);
    setSelectedSearchResults([]);
    setIsPanelOpen(false);
    router.push('/chat');
  };

  return (
    <AppLayout>
      <div className="flex h-full">
        {/* 메인 채팅 영역 */}
        <div className="flex-1 flex flex-col">
          {/* 헤더 */}
          <header className="border-b border-gray-200 bg-white shadow-sm">
            <div className="px-6 py-4 flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">AI 채팅</h1>
                <p className="mt-1 text-sm text-gray-600">
                  보험약관에 대해 궁금한 점을 질문해보세요
                </p>
              </div>

              <div className="flex items-center gap-2">
                {/* 새 대화 버튼 */}
                {messages.length > 0 && (
                  <button
                    onClick={handleNewChat}
                    className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                    title="새 대화 시작"
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
                        d="M12 4v16m8-8H4"
                      />
                    </svg>
                    새 대화
                  </button>
                )}

                {/* 참조문서 토글 버튼 */}
                {selectedSearchResults.length > 0 && (
                  <button
                    onClick={() => setIsPanelOpen(!isPanelOpen)}
                    className={`hidden md:flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                      isPanelOpen
                        ? 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                    title={isPanelOpen ? '참조문서 닫기' : '참조문서 열기'}
                  >
                    <span className="text-lg">📚</span>
                    <span className="text-sm font-medium">
                      참조문서 ({selectedSearchResults.length})
                    </span>
                    {isPanelOpen ? (
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
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    ) : (
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
                    )}
                  </button>
                )}
              </div>
            </div>
          </header>

          {/* 메시지 영역 */}
          <div className="flex-1 overflow-y-auto">
            {isLoadingHistory ? (
              // 이력 로딩 중
              <div className="flex h-full items-center justify-center">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                  <p className="text-gray-600">대화 내역을 불러오는 중...</p>
                </div>
              </div>
            ) : (
              <div className="mx-auto max-w-4xl px-2 sm:px-4 py-6">
                {messages.length === 0 ? (
                  // 초기 화면
                  <div className="flex h-full items-center justify-center">
                    <div className="text-center">
                      <div className="mb-4 text-6xl">💬</div>
                      <h2 className="mb-2 text-xl font-semibold text-gray-900">
                        채팅을 시작해보세요
                      </h2>
                      <p className="mb-6 text-gray-600">
                        보험약관에 대한 질문을 입력하시면
                        <br />
                        AI가 정확한 답변을 제공해드립니다
                      </p>
                      {/* <div className="space-y-2 text-left">
                        <div className="rounded-lg bg-blue-50 p-3 text-sm">
                          <p className="font-medium text-blue-900">예시 질문:</p>
                          <ul className="mt-1 space-y-1 text-blue-700">
                            <li>• 암 진단금은 얼마인가요?</li>
                            <li>• 제15조의 내용이 무엇인가요?</li>
                            <li>• 면책기간은 얼마나 되나요?</li>
                          </ul>
                        </div>
                      </div> */}
                    </div>
                  </div>
                ) : (
                  // 메시지 리스트
                  <div className="space-y-4">
                    {messages.map((message) => (
                      <ChatMessage key={message.id} message={message} />
                    ))}

                    {/* 로딩 인디케이터 */}
                    {isLoading && (
                      <div className="flex justify-start">
                        <div className="rounded-lg bg-gray-100 px-4 py-3">
                          <div className="flex items-center space-x-2">
                            <div className="h-2 w-2 animate-bounce rounded-full bg-gray-500" />
                            <div
                              className="h-2 w-2 animate-bounce rounded-full bg-gray-500"
                              style={{ animationDelay: '0.2s' }}
                            />
                            <div
                              className="h-2 w-2 animate-bounce rounded-full bg-gray-500"
                              style={{ animationDelay: '0.4s' }}
                            />
                          </div>
                        </div>
                      </div>
                    )}

                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 오류 표시 */}
          {error && (
            <div className="border-t border-red-200 bg-red-50 px-2 sm:px-4 py-2">
              <div className="mx-auto max-w-4xl">
                <p className="text-sm text-red-600">⚠️ {error}</p>
              </div>
            </div>
          )}

          {/* 입력 영역 */}
          <ChatInput onSend={handleSendMessage} disabled={isLoading || isLoadingHistory} />
        </div>

        {/* 참조 문서 패널 */}
        <ReferencePanel
          searchResults={selectedSearchResults}
          isOpen={isPanelOpen}
          onToggle={() => setIsPanelOpen(!isPanelOpen)}
        />
      </div>
    </AppLayout>
  );
}
