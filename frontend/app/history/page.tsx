'use client';

import { useRouter } from 'next/navigation';
import AppLayout from '@/components/AppLayout';
import ChatHistory from '@/components/ChatHistory';

export default function HistoryPage() {
  const router = useRouter();

  const handleSelectSession = (threadId: string) => {
    // 선택한 대화로 이동
    router.push(`/chat?thread_id=${threadId}`);
  };

  return (
    <AppLayout>
      <div className="flex h-full flex-col">
        {/* 헤더 */}
        <header className="border-b border-gray-200 bg-white shadow-sm">
          <div className="px-6 py-4">
            <h1 className="text-2xl font-bold text-gray-900">최근 대화</h1>
            <p className="mt-1 text-sm text-gray-600">
              이전 대화 이력을 확인하고 관리합니다
            </p>
          </div>
        </header>

        {/* 대화 이력 컴포넌트 */}
        <div className="flex-1 overflow-hidden">
          <ChatHistory onSelectSession={handleSelectSession} />
        </div>
      </div>
    </AppLayout>
  );
}

