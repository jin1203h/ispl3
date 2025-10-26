"""
PreprocessedQuery 모델

질의 전처리 결과를 담는 데이터 모델입니다.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class PreprocessedQuery(BaseModel):
    """
    질의 전처리 결과 모델
    
    Attributes:
        original: 원본 사용자 질의
        normalized: 공백, 특수문자가 정규화된 질의
        standardized: 전문용어가 표준화된 질의
        expanded_terms: 동의어 확장 결과 리스트
        clause_number: 추출된 조항 번호 (예: "제15조")
        is_complete: 질의 완전성 여부
        suggestions: 불완전 질의 시 사용자에게 제공할 제안사항 리스트
    """
    
    original: str = Field(..., description="원본 사용자 질의")
    normalized: str = Field(..., description="공백, 특수문자가 정규화된 질의")
    standardized: str = Field(..., description="전문용어가 표준화된 질의")
    expanded_terms: List[str] = Field(default_factory=list, description="동의어 확장 결과")
    clause_number: Optional[str] = Field(None, description="추출된 조항 번호 (예: 제15조)")
    is_complete: bool = Field(..., description="질의 완전성 여부")
    suggestions: List[str] = Field(default_factory=list, description="불완전 질의 시 제안사항")
    
    class Config:
        """Pydantic 설정"""
        json_schema_extra = {
            "example": {
                "original": "암진단비 얼마인가요?",
                "normalized": "암진단비 얼마인가요?",
                "standardized": "암 진단비 얼마인가요?",
                "expanded_terms": [
                    "암 진단비 얼마인가요?",
                    "악성신생물 진단비 얼마인가요?"
                ],
                "clause_number": None,
                "is_complete": True,
                "suggestions": []
            }
        }
    
    def __repr__(self):
        """문자열 표현"""
        return (
            f"<PreprocessedQuery("
            f"original='{self.original[:30]}...', "
            f"standardized='{self.standardized[:30]}...', "
            f"is_complete={self.is_complete}"
            f")>"
        )

