'use client';

/**
 * PDF 문서 업로드 컴포넌트
 * 드래그 앤 드롭, 파일 검증, 업로드 진행률 표시
 */

import { useState, useRef, DragEvent, ChangeEvent } from 'react';
import { uploadPDF, UploadResponse } from '@/lib/api';

interface DocumentUploadProps {
  onUploadComplete?: (response: UploadResponse) => void;
}

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

export default function DocumentUpload({ onUploadComplete }: DocumentUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [method, setMethod] = useState<'pymupdf' | 'vision' | 'both'>('pymupdf');
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 파일 검증
  const validateFile = (file: File): string | null => {
    if (!file.type.includes('pdf')) {
      return 'PDF 파일만 업로드 가능합니다.';
    }
    if (file.size > MAX_FILE_SIZE) {
      return `파일 크기는 ${MAX_FILE_SIZE / 1024 / 1024}MB 이하여야 합니다.`;
    }
    return null;
  };

  // 파일 선택 처리
  const handleFileSelect = (file: File) => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      setSelectedFile(null);
      return;
    }

    setError(null);
    setSelectedFile(file);
    setSuccess(false);
  };

  // 드래그 앤 드롭 이벤트
  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  // 파일 입력 변경
  const handleFileInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  // 파일 선택 버튼 클릭
  const handleSelectClick = () => {
    fileInputRef.current?.click();
  };

  // 업로드 실행
  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setProgress(0);
    setError(null);

    try {
      // 진행률 시뮬레이션 (실제 업로드 진행률 추적은 복잡하므로)
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 10, 90));
      }, 200);

      const response = await uploadPDF(selectedFile, method, true);

      clearInterval(progressInterval);
      setProgress(100);
      setSuccess(true);
      
      if (onUploadComplete) {
        onUploadComplete(response);
      }

      // 3초 후 리셋
      setTimeout(() => {
        setSelectedFile(null);
        setProgress(0);
        setSuccess(false);
        setUploading(false);
      }, 3000);

    } catch (err) {
      setError(err instanceof Error ? err.message : '업로드 실패');
      setUploading(false);
      setProgress(0);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 space-y-6">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-gray-900">PDF 문서 업로드</h2>
        <p className="text-gray-600 mt-2">보험 약관 PDF 파일을 업로드하세요</p>
      </div>

      {/* 드래그 앤 드롭 영역 */}
      <div
        onDragEnter={handleDragEnter}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-lg p-12
          transition-colors duration-200 cursor-pointer
          ${isDragging 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
        `}
        onClick={handleSelectClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileInputChange}
          className="hidden"
        />

        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p className="mt-4 text-sm text-gray-600">
            <span className="font-semibold text-blue-600">파일 선택</span> 또는 드래그 앤 드롭
          </p>
          <p className="mt-2 text-xs text-gray-500">PDF 파일, 최대 50MB</p>
        </div>
      </div>

      {/* 선택된 파일 정보 */}
      {selectedFile && (
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <svg className="h-8 w-8 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
              </svg>
              <div>
                <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-xs text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setSelectedFile(null);
                setError(null);
              }}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* 처리 옵션 */}
      {selectedFile && !uploading && !success && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              처리 방법
            </label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value as typeof method)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="pymupdf">PyMuPDF (빠름)</option>
              <option value="vision">GPT-4 Vision (정확, 비용 발생)</option>
              <option value="both">하이브리드 (가장 정확, 비용 발생)</option>
            </select>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-sm text-blue-800">
              ✅ 청킹 및 임베딩이 자동으로 활성화됩니다
            </p>
            <p className="text-xs text-blue-600 mt-1">
              업로드된 문서는 검색 가능한 상태로 저장됩니다
            </p>
          </div>
        </div>
      )}

      {/* 업로드 진행률 */}
      {uploading && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-gray-600">
            <span>업로드 중...</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* 에러 메시지 */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <svg className="h-5 w-5 text-red-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <p className="text-sm text-red-800">{error}</p>
          </div>
        </div>
      )}

      {/* 성공 메시지 */}
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center">
            <svg className="h-5 w-5 text-green-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <p className="text-sm text-green-800">업로드 완료!</p>
          </div>
        </div>
      )}

      {/* 업로드 버튼 */}
      {selectedFile && !uploading && !success && (
        <button
          onClick={handleUpload}
          className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          업로드 시작
        </button>
      )}
    </div>
  );
}

