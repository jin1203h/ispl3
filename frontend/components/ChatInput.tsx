'use client';

import { useState, KeyboardEvent } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({ 
  onSend, 
  disabled = false,
  placeholder = "보험약관에 대해 질문해보세요..." 
}: ChatInputProps) {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSend(message.trim());
      setMessage('');
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      <div className="mx-auto max-w-4xl">
        <div className="flex gap-3">
          <textarea
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 
                     focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 
                     disabled:bg-gray-100 disabled:cursor-not-allowed
                     min-h-[52px] max-h-[200px]"
            style={{
              fieldSizing: 'content'
            }}
          />
          <button
            onClick={handleSend}
            disabled={disabled || !message.trim()}
            className="rounded-lg bg-blue-600 px-6 py-3 font-medium text-white 
                     hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 
                     disabled:bg-gray-300 disabled:cursor-not-allowed
                     transition-colors duration-200"
          >
            전송
          </button>
        </div>
        <p className="mt-2 text-xs text-gray-500">
          Enter로 전송, Shift+Enter로 줄바꿈
        </p>
      </div>
    </div>
  );
}

