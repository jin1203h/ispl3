"""
서비스 컨테이너
싱글톤 패턴으로 서비스 인스턴스를 관리합니다.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ServiceContainer:
    """서비스 인스턴스를 싱글톤으로 관리하는 컨테이너"""
    
    _instance: Optional['ServiceContainer'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """서비스 컨테이너 초기화 (한 번만 실행)"""
        if self._initialized:
            return
        
        # 서비스 인스턴스 저장소
        self._embedding_service = None
        self._vector_search_service = None
        self._hybrid_search_service = None
        self._query_preprocessor = None
        self._text_chunker = None
        self._pdf_processor = None
        self._openai_client = None
        self._answer_validator = None
        
        self._initialized = True
        logger.info("ServiceContainer 초기화 완료")
    
    def get_embedding_service(self):
        """EmbeddingService 싱글톤 인스턴스 반환"""
        if self._embedding_service is None:
            from services.embedding_service import EmbeddingService
            self._embedding_service = EmbeddingService()
            logger.info("EmbeddingService 싱글톤 인스턴스 생성")
        return self._embedding_service
    
    def get_vector_search_service(self):
        """VectorSearchService 싱글톤 인스턴스 반환"""
        if self._vector_search_service is None:
            from services.vector_search import VectorSearchService
            # embedding_service를 주입
            embedding_service = self.get_embedding_service()
            self._vector_search_service = VectorSearchService(embedding_service)
            logger.info("VectorSearchService 싱글톤 인스턴스 생성")
        return self._vector_search_service
    
    def get_hybrid_search_service(self):
        """HybridSearchService 싱글톤 인스턴스 반환"""
        if self._hybrid_search_service is None:
            from services.hybrid_search import HybridSearchService
            # vector_search_service를 주입
            vector_search_service = self.get_vector_search_service()
            self._hybrid_search_service = HybridSearchService(vector_search_service)
            logger.info("HybridSearchService 싱글톤 인스턴스 생성")
        return self._hybrid_search_service
    
    def get_query_preprocessor(self):
        """QueryPreprocessor 싱글톤 인스턴스 반환"""
        if self._query_preprocessor is None:
            from services.query_preprocessor import QueryPreprocessor
            self._query_preprocessor = QueryPreprocessor()
            logger.info("QueryPreprocessor 싱글톤 인스턴스 생성")
        return self._query_preprocessor
    
    def get_text_chunker(self):
        """TextChunker 싱글톤 인스턴스 반환"""
        if self._text_chunker is None:
            from services.chunker import TextChunker
            self._text_chunker = TextChunker(chunk_size=1000, overlap=100)
            logger.info("TextChunker 싱글톤 인스턴스 생성")
        return self._text_chunker
    
    def get_pdf_processor(self):
        """PDFProcessor 싱글톤 인스턴스 반환"""
        if self._pdf_processor is None:
            from services.pdf_processor import PDFProcessor
            # embedding_service와 text_chunker를 주입
            embedding_service = self.get_embedding_service()
            text_chunker = self.get_text_chunker()
            self._pdf_processor = PDFProcessor(
                embedding_service=embedding_service,
                text_chunker=text_chunker
            )
            logger.info("PDFProcessor 싱글톤 인스턴스 생성")
        return self._pdf_processor
    
    def get_openai_client(self):
        """AsyncOpenAI 싱글톤 인스턴스 반환"""
        if self._openai_client is None:
            from openai import AsyncOpenAI
            from core.config import settings
            self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("AsyncOpenAI 싱글톤 인스턴스 생성")
        return self._openai_client
    
    def get_answer_validator(self):
        """AnswerValidator 싱글톤 인스턴스 반환"""
        if self._answer_validator is None:
            from services.answer_validator import AnswerValidator
            # openai_client를 주입
            openai_client = self.get_openai_client()
            self._answer_validator = AnswerValidator(openai_client)
            logger.info("AnswerValidator 싱글톤 인스턴스 생성")
        return self._answer_validator


# 전역 서비스 컨테이너 인스턴스
service_container = ServiceContainer()


def get_embedding_service():
    """EmbeddingService 인스턴스 가져오기"""
    return service_container.get_embedding_service()


def get_vector_search_service():
    """VectorSearchService 인스턴스 가져오기"""
    return service_container.get_vector_search_service()


def get_hybrid_search_service():
    """HybridSearchService 인스턴스 가져오기"""
    return service_container.get_hybrid_search_service()


def get_query_preprocessor():
    """QueryPreprocessor 인스턴스 가져오기"""
    return service_container.get_query_preprocessor()


def get_text_chunker():
    """TextChunker 인스턴스 가져오기"""
    return service_container.get_text_chunker()


def get_pdf_processor():
    """PDFProcessor 인스턴스 가져오기"""
    return service_container.get_pdf_processor()


def get_openai_client():
    """AsyncOpenAI 인스턴스 가져오기"""
    return service_container.get_openai_client()


def get_answer_validator():
    """AnswerValidator 인스턴스 가져오기"""
    return service_container.get_answer_validator()

