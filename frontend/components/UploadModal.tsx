'use client';

import { useState } from 'react';
import { uploadPDF } from '@/lib/api';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function UploadModal({ isOpen, onClose, onSuccess }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [method, setMethod] = useState<'pymupdf' | 'vision' | 'both'>('pymupdf');
  const [documentType, setDocumentType] = useState<string>('policy');
  const [insuranceType, setInsuranceType] = useState<string>('health');
  const [companyName, setCompanyName] = useState<string>('');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('파일을 선택해주세요');
      return;
    }

    if (!companyName.trim()) {
      setError('보험사명을 입력해주세요');
      return;
    }

    setIsUploading(true);
    setError(null);
    setProgress(0);

    try {
      await uploadPDF(
        file, 
        method, 
        true, 
        (prog) => {
          setProgress(prog);
        },
        documentType,
        insuranceType,
        companyName.trim()
      );

      // 성공
      onSuccess();
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '업로드 실패');
    } finally {
      setIsUploading(false);
    }
  };

  const handleClose = () => {
    if (!isUploading) {
      setFile(null);
      setDocumentType('policy');
      setInsuranceType('health');
      setCompanyName('');
      setError(null);
      setProgress(0);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        {/* 헤더 */}
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">약관 업로드</h2>
          <button
            onClick={handleClose}
            disabled={isUploading}
            className="text-gray-400 hover:text-gray-600 disabled:cursor-not-allowed"
          >
            ✕
          </button>
        </div>

        {/* 파일 선택 */}
        <div className="mb-4">
          <label className="mb-2 block text-sm font-medium text-gray-700">
            PDF 파일
          </label>
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            disabled={isUploading}
            className="w-full rounded-lg border border-gray-300 p-2 text-sm
                     file:mr-4 file:rounded file:border-0 file:bg-blue-50 
                     file:px-4 file:py-2 file:text-sm file:font-semibold 
                     file:text-blue-700 hover:file:bg-blue-100
                     disabled:cursor-not-allowed disabled:bg-gray-100"
          />
          {file && (
            <p className="mt-1 text-xs text-gray-600">
              선택된 파일: {file.name}
            </p>
          )}
        </div>

        {/* 문서 타입 */}
        <div className="mb-4">
          <label className="mb-2 block text-sm font-medium text-gray-700">
            문서 타입
          </label>
          <select
            value={documentType}
            onChange={(e) => setDocumentType(e.target.value)}
            disabled={isUploading}
            className="w-full rounded-lg border border-gray-300 p-2 text-sm
                     focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                     disabled:cursor-not-allowed disabled:bg-gray-100"
          >
            <option value="policy">약관</option>
            <option value="terms">약관 조항</option>
            <option value="guide">안내서</option>
            <option value="contract">계약서</option>
          </select>
        </div>

        {/* 보험 타입 */}
        <div className="mb-4">
          <label className="mb-2 block text-sm font-medium text-gray-700">
            보험 타입
          </label>
          <select
            value={insuranceType}
            onChange={(e) => setInsuranceType(e.target.value)}
            disabled={isUploading}
            className="w-full rounded-lg border border-gray-300 p-2 text-sm
                     focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                     disabled:cursor-not-allowed disabled:bg-gray-100"
          >
            <option value="health">건강보험</option>
            <option value="life">생명보험</option>
            <option value="car">자동차보험</option>
            <option value="fire">화재보험</option>
            <option value="accident">상해보험</option>
            <option value="travel">여행보험</option>
            <option value="pension">연금보험</option>
            <option value="other">기타</option>
          </select>
        </div>

        {/* 보험사명 */}
        <div className="mb-4">
          <label className="mb-2 block text-sm font-medium text-gray-700">
            보험사명 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            disabled={isUploading}
            placeholder="예: 삼성생명"
            className="w-full rounded-lg border border-gray-300 p-2 text-sm
                     focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                     disabled:cursor-not-allowed disabled:bg-gray-100"
          />
        </div>

        {/* 추출 방법 선택 */}
        <div className="mb-4">
          <label className="mb-2 block text-sm font-medium text-gray-700">
            추출 방법
          </label>
          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="radio"
                value="pymupdf"
                checked={method === 'pymupdf'}
                onChange={(e) => setMethod(e.target.value as 'pymupdf')}
                disabled={isUploading}
                className="mr-2"
              />
              <span className="text-sm text-gray-700">
                PyMuPDF (빠름, 일반 문서)
              </span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="vision"
                checked={method === 'vision'}
                onChange={(e) => setMethod(e.target.value as 'vision')}
                disabled={isUploading}
                className="mr-2"
              />
              <span className="text-sm text-gray-700">
                Vision API (느림, 표/이미지 많은 문서)
              </span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                value="both"
                checked={method === 'both'}
                onChange={(e) => setMethod(e.target.value as 'both')}
                disabled={isUploading}
                className="mr-2"
              />
              <span className="text-sm text-gray-700">
                하이브리드 (가장 정확, 가장 느림)
              </span>
            </label>
          </div>
        </div>

        {/* 진행률 */}
        {isUploading && progress > 0 && (
          <div className="mb-4">
            <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-full bg-blue-600 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-gray-600 text-center">
              업로드 중... {progress}%
            </p>
          </div>
        )}

        {/* 오류 메시지 */}
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 p-3">
            <p className="text-sm text-red-600">⚠️ {error}</p>
          </div>
        )}

        {/* 버튼 */}
        <div className="flex justify-end gap-3">
          <button
            onClick={handleClose}
            disabled={isUploading}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm 
                     font-medium text-gray-700 hover:bg-gray-50
                     disabled:cursor-not-allowed disabled:bg-gray-100"
          >
            취소
          </button>
          <button
            onClick={handleUpload}
            disabled={!file || isUploading}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium 
                     text-white hover:bg-blue-700 disabled:cursor-not-allowed 
                     disabled:bg-gray-300"
          >
            {isUploading ? '업로드 중...' : '업로드'}
          </button>
        </div>
      </div>
    </div>
  );
}

