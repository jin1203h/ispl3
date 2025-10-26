'use client';

import { useState, useEffect, useCallback } from 'react';
import AppLayout from '@/components/AppLayout';
import UploadModal from '@/components/UploadModal';
import DeleteConfirmDialog from '@/components/DeleteConfirmDialog';
import DocumentViewer from '@/components/DocumentViewer';
import { listDocuments, deleteDocument, DocumentItem } from '@/lib/api';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 필터 및 정렬 상태
  const [filters, setFilters] = useState({
    filename: '',
    document_type: '',
    company_name: '',
  });
  const [sortBy, setSortBy] = useState<'created_at' | 'filename'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  // 페이지네이션 상태
  const [offset, setOffset] = useState(0);
  const [limit] = useState(20);
  const [total, setTotal] = useState(0);
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);

  // 뷰어 상태
  const [viewerOpen, setViewerOpen] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [viewerFileType, setViewerFileType] = useState<'pdf' | 'markdown'>('pdf');

  // 삭제 다이얼로그 상태
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; filename: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // 문서 목록 조회
  const fetchDocuments = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const params = {
        filename: filters.filename || undefined,
        document_type: filters.document_type || undefined,
        company_name: filters.company_name || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        offset,
        limit,
      };
      const data = await listDocuments(params);
      setDocuments(data.documents || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : '오류가 발생했습니다');
      setDocuments([]);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, [filters, sortBy, sortOrder, offset, limit]);

  useEffect(() => {
    fetchDocuments();
  }, [sortBy, sortOrder, offset]); // 정렬, 페이지 변경 시 자동 조회 (필터는 검색 버튼으로)

  // 업로드 성공 후
  const handleUploadSuccess = () => {
    fetchDocuments();
  };

  // 보기
  const handleView = (docId: number, fileType: 'pdf' | 'markdown') => {
    setSelectedDocId(docId);
    setViewerFileType(fileType);
    setViewerOpen(true);
  };

  // 삭제 (다이얼로그 열기)
  const handleDeleteClick = (doc: DocumentItem) => {
    setDeleteTarget({ id: doc.id, filename: doc.filename });
    setDeleteDialogOpen(true);
  };

  // 삭제 확인
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;

    setIsDeleting(true);
    let deleteSuccess = false;
    
    try {
      await deleteDocument(deleteTarget.id);
      deleteSuccess = true;
    } catch (err) {
      alert(err instanceof Error ? err.message : '삭제 중 오류 발생');
    } finally {
      // 성공/실패 관계없이 팝업 닫기
      setIsDeleting(false);
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      
      // 삭제 성공 시 목록 재조회
      if (deleteSuccess) {
        await fetchDocuments();
      }
    }
  };

  // 삭제 취소
  const handleDeleteCancel = () => {
    setDeleteDialogOpen(false);
    setDeleteTarget(null);
  };

  return (
    <AppLayout>
      <div className="flex h-full flex-col">
        {/* 헤더 */}
        <header className="border-b border-gray-200 bg-white shadow-sm">
          <div className="flex items-center justify-between px-6 py-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">약관 관리</h1>
              <p className="mt-1 text-sm text-gray-600">
                등록된 보험약관을 관리합니다
              </p>
            </div>
            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium 
                       text-white hover:bg-blue-700 focus:outline-none 
                       focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              📄 약관 업로드
            </button>
          </div>
        </header>

        {/* 콘텐츠 */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-7xl">
            {/* 로딩 */}
            {isLoading && (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
                <span className="ml-3 text-gray-600">로딩 중...</span>
              </div>
            )}

            {/* 오류 */}
            {error && !isLoading && (
              <div className="rounded-lg bg-red-50 p-4">
                <p className="text-red-600">⚠️ {error}</p>
              </div>
            )}

            {/* 빈 상태 */}
            {!isLoading && !error && documents.length === 0 && (
              <div className="text-center py-12">
                <div className="text-6xl mb-4">📄</div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  등록된 약관이 없습니다
                </h2>
                <p className="text-gray-600 mb-6">
                  상단의 "약관 업로드" 버튼을 클릭하여<br />
                  보험약관 PDF를 업로드해주세요
                </p>
                <button
                  onClick={() => setIsUploadModalOpen(true)}
                  className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 
                           text-sm font-medium text-white hover:bg-blue-700"
                >
                  📄 약관 업로드
                </button>
              </div>
            )}

            {/* 필터 및 정렬 */}
            {!isLoading && !error && (
              <div className="mb-6 bg-white rounded-lg shadow p-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                  <input
                    type="text"
                    placeholder="파일명 검색"
                    value={filters.filename}
                    onChange={(e) => setFilters({ ...filters, filename: e.target.value })}
                    className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <input
                    type="text"
                    placeholder="문서 타입"
                    value={filters.document_type}
                    onChange={(e) => setFilters({ ...filters, document_type: e.target.value })}
                    className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <input
                    type="text"
                    placeholder="회사명 검색"
                    value={filters.company_name}
                    onChange={(e) => setFilters({ ...filters, company_name: e.target.value })}
                    className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <button
                    onClick={() => {
                      setOffset(0); // 검색 시 첫 페이지로
                      fetchDocuments();
                    }}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
                  >
                    🔍 검색
                  </button>
                </div>

                <div className="flex gap-3 items-center">
                  <label className="text-sm font-medium text-gray-700">정렬:</label>
                  <select
                    value={sortBy}
                    onChange={(e) => {
                      setSortBy(e.target.value as 'created_at' | 'filename');
                      setOffset(0); // 정렬 변경 시 첫 페이지로
                    }}
                    className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="created_at">등록일</option>
                    <option value="filename">파일명</option>
                  </select>
                  <select
                    value={sortOrder}
                    onChange={(e) => {
                      setSortOrder(e.target.value as 'asc' | 'desc');
                      setOffset(0); // 정렬 변경 시 첫 페이지로
                    }}
                    className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="desc">내림차순</option>
                    <option value="asc">오름차순</option>
                  </select>
                </div>
              </div>
            )}

            {/* 테이블 */}
            {!isLoading && !error && documents.length > 0 && (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        파일명
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        문서 타입
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        회사명
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        페이지
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        청크
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        등록일
                      </th>
                      <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                        액션
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {documents.map((doc) => (
                      <tr key={doc.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">
                            {doc.filename}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                            {doc.document_type || '-'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {doc.company_name || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-center">
                          {doc.total_pages || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-center">
                          {doc.total_chunks || '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {new Date(doc.created_at).toLocaleDateString('ko-KR')}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-center text-sm font-medium">
                          <div className="flex gap-1 justify-center">
                            <button
                              onClick={() => handleView(doc.id, 'pdf')}
                              className="p-1 hover:bg-gray-100 rounded text-base transition-colors"
                              title="PDF 보기"
                            >
                              📄
                            </button>
                            <button
                              onClick={() => handleView(doc.id, 'markdown')}
                              className="p-1 hover:bg-gray-100 rounded text-base transition-colors"
                              title="Markdown 보기"
                            >
                              📝
                            </button>
                            <button
                              onClick={() => handleDeleteClick(doc)}
                              className="p-1 hover:bg-gray-100 rounded text-base transition-colors"
                              title="삭제"
                            >
                              🗑️
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>

                {/* 페이지네이션 */}
                <div className="px-4 sm:px-6 py-4 border-t border-gray-200 flex flex-col sm:flex-row items-center justify-between gap-3">
                  <div className="text-xs sm:text-sm text-gray-700">
                    전체 <span className="font-medium">{total}</span>개 중{' '}
                    <span className="font-medium">{total > 0 ? offset + 1 : 0}</span>-
                    <span className="font-medium">{Math.min(offset + limit, total)}</span>개 표시
                  </div>
                  <div className="flex gap-2 items-center">
                    <button
                      disabled={currentPage <= 1 || total === 0}
                      onClick={() => {
                        setOffset(Math.max(0, offset - limit));
                      }}
                      className="px-2 sm:px-3 py-1 rounded-lg border border-gray-300 text-gray-700 text-xs sm:text-sm
                               hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      이전
                    </button>
                    <span className="px-2 sm:px-3 py-1 text-xs sm:text-sm text-gray-700">
                      <span className="font-medium">{totalPages > 0 ? currentPage : 0}</span> / {totalPages}
                    </span>
                    <button
                      disabled={currentPage >= totalPages || total === 0}
                      onClick={() => {
                        setOffset(offset + limit);
                      }}
                      className="px-2 sm:px-3 py-1 rounded-lg border border-gray-300 text-gray-700 text-xs sm:text-sm
                               hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      다음
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 업로드 모달 */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccess={handleUploadSuccess}
      />

      {/* 삭제 확인 다이얼로그 */}
      <DeleteConfirmDialog
        isOpen={deleteDialogOpen}
        filename={deleteTarget?.filename || ''}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
        isDeleting={isDeleting}
      />

      {/* 문서 뷰어 */}
      {selectedDocId && (
        <DocumentViewer
          isOpen={viewerOpen}
          documentId={selectedDocId}
          fileType={viewerFileType}
          onClose={() => setViewerOpen(false)}
        />
      )}
    </AppLayout>
  );
}
