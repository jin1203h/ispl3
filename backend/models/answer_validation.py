"""
답변 검증 결과 모델

답변의 신뢰도를 검증한 결과를 담는 Pydantic 모델입니다.
개별 검증 항목(할루시네이션, 조항 존재, 컨텍스트 일치, 형식)의 결과와
전체 신뢰도 점수를 구조화하여 제공합니다.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class ValidationDetail(BaseModel):
    """
    개별 검증 항목의 상세 결과
    
    각 검증 항목(할루시네이션, 조항 존재 등)의 통과 여부, 점수, 상세 설명을 담습니다.
    """
    check_name: str = Field(..., description="검증 항목명")
    passed: bool = Field(..., description="통과 여부")
    score: float = Field(..., ge=0.0, le=1.0, description="점수 (0.0 ~ 1.0)")
    details: Optional[str] = Field(None, description="상세 설명")
    
    class Config:
        json_schema_extra = {
            "example": {
                "check_name": "할루시네이션 검증",
                "passed": True,
                "score": 0.9,
                "details": "모든 진술이 컨텍스트에 근거함"
            }
        }


class AnswerValidation(BaseModel):
    """
    답변 검증 전체 결과
    
    4가지 검증 항목(할루시네이션, 조항 존재, 컨텍스트 일치, 형식)의 결과를
    종합하여 최종 신뢰도 점수를 산출합니다.
    
    Attributes:
        confidence_score: 전체 신뢰도 점수 (0.0 ~ 1.0)
        is_reliable: 신뢰 가능 여부 (confidence_score >= 0.7)
        hallucination_check: 할루시네이션 검증 결과
        clause_existence_check: 조항 번호 존재 확인 결과
        context_match_check: 컨텍스트 일치 확인 결과
        format_check: 형식 검증 결과
        validation_time: 검증 소요 시간 (초)
        regeneration_count: 재생성 횟수 (0: 최초 생성)
        warnings: 경고 메시지 목록
    """
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="전체 신뢰도 점수 (0.0 ~ 1.0)"
    )
    is_reliable: bool = Field(..., description="신뢰 가능 여부 (>= 0.7)")
    
    # 개별 검증 결과
    hallucination_check: ValidationDetail = Field(
        ..., 
        description="할루시네이션 검증 결과"
    )
    clause_existence_check: ValidationDetail = Field(
        ..., 
        description="조항 번호 존재 확인 결과"
    )
    context_match_check: ValidationDetail = Field(
        ..., 
        description="컨텍스트 일치 확인 결과"
    )
    format_check: ValidationDetail = Field(
        ..., 
        description="형식 검증 결과"
    )
    
    # 메타 정보
    validation_time: float = Field(..., ge=0.0, description="검증 소요 시간 (초)")
    regeneration_count: int = Field(
        default=0, 
        ge=0, 
        description="재생성 횟수 (0: 최초 생성)"
    )
    warnings: List[str] = Field(
        default_factory=list, 
        description="경고 메시지 목록"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "confidence_score": 0.85,
                "is_reliable": True,
                "hallucination_check": {
                    "check_name": "할루시네이션 검증",
                    "passed": True,
                    "score": 0.9,
                    "details": "모든 진술이 컨텍스트에 근거함"
                },
                "clause_existence_check": {
                    "check_name": "조항 존재 확인",
                    "passed": True,
                    "score": 1.0,
                    "details": "제5조, 제15조 모두 존재 확인"
                },
                "context_match_check": {
                    "check_name": "컨텍스트 일치",
                    "passed": True,
                    "score": 0.85,
                    "details": "주요 내용 일치율 85%"
                },
                "format_check": {
                    "check_name": "형식 검증",
                    "passed": True,
                    "score": 1.0,
                    "details": "구조화, 참조, 조항 모두 포함"
                },
                "validation_time": 0.8,
                "regeneration_count": 0,
                "warnings": []
            }
        }
    
    def __repr__(self):
        """문자열 표현"""
        return (
            f"<AnswerValidation("
            f"confidence={self.confidence_score:.2f}, "
            f"reliable={self.is_reliable}, "
            f"regeneration={self.regeneration_count})>"
        )

