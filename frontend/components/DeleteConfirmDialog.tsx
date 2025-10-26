'use client';

interface Props {
  isOpen: boolean;
  filename: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting?: boolean;
}

export default function DeleteConfirmDialog({
  isOpen,
  filename,
  onConfirm,
  onCancel,
  isDeleting = false,
}: Props) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        {/* 제목 */}
        <h2 className="text-xl font-bold text-gray-900">문서 삭제 확인</h2>

        {/* 설명 */}
        <p className="mt-2 text-sm text-gray-600">
          다음 문서를 삭제하시겠습니까?
        </p>

        {/* 파일명 */}
        <p className="mt-2 font-medium text-gray-900">{filename}</p>

        {/* 경고 */}
        <p className="mt-2 text-xs text-red-600">
          ⚠️ 삭제된 문서는 복구할 수 없습니다.
        </p>

        {/* 버튼 */}
        <div className="mt-6 flex gap-3 justify-end">
          <button
            onClick={onCancel}
            disabled={isDeleting}
            className="px-4 py-2 rounded-lg border border-gray-300 text-gray-700 
                     hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            취소
          </button>
          <button
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 rounded-lg bg-red-600 text-white 
                     hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDeleting ? '삭제 중...' : '삭제'}
          </button>
        </div>
      </div>
    </div>
  );
}

