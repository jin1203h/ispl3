'use client';

import { usePathname } from 'next/navigation';
import Link from 'next/link';

export default function Sidebar() {
  const pathname = usePathname();

  const menuItems = [
    {
      name: 'AI 채팅',
      icon: '💬',
      path: '/chat',
      description: '보험약관 질문하기',
    },
    {
      name: '최근 대화',
      icon: '📋',
      path: '/history',
      description: '대화 이력 보기',
    },
    {
      name: '약관 관리',
      icon: '📄',
      path: '/documents',
      description: '약관 업로드 및 관리',
    },
  ];

  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col">
      {/* 로고/헤더 */}
      <div className="p-6 border-b border-gray-700">
        <Link href="/" className="block">
          <h1 className="text-xl font-bold">🏥 ISPL</h1>
          <p className="text-xs text-gray-400 mt-1">보험약관 AI 시스템</p>
        </Link>
      </div>

      {/* 메뉴 */}
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {menuItems.map((item) => {
            const isActive = pathname === item.path;
            return (
              <li key={item.path}>
                <Link
                  href={item.path}
                  className={`flex items-start p-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  }`}
                >
                  <span className="text-2xl mr-3">{item.icon}</span>
                  <div className="flex-1">
                    <div className="font-medium">{item.name}</div>
                    <div className="text-xs opacity-75 mt-0.5">
                      {item.description}
                    </div>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* 하단 정보 */}
      <div className="p-4 border-t border-gray-700">
        <div className="text-xs text-gray-400">
          <p className="mb-1">Version 1.0.0</p>
          <p>© 2025 ISPL</p>
        </div>
      </div>
    </aside>
  );
}

