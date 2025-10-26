"""
문서 구조 분석기
다양한 항목 패턴을 인식하고 구조적 완결성을 판단합니다.
"""
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class DocumentStructureAnalyzer:
    """
    문서 구조 분석기
    
    법령, 보험약관 등의 다양한 항목 형식을 인식하고
    구조적 완결성을 판단합니다.
    """
    
    # 계층 구조 패턴 정의
    STRUCTURE_PATTERNS = {
        # 레벨 1: 조항/장/절
        "article": {
            "patterns": [
                r'제\s*(\d+)\s*조',           # 제28조
                r'제\s*(\d+)\s*장',           # 제1장
                r'제\s*(\d+)\s*절',           # 제1절
            ],
            "level": 1,
            "name": "조항"
        },
        
        # 레벨 2: 호 (가나다, ㄱㄴㄷ)
        "ho": {
            "patterns": [
                r'^\s*([가-힣])\.\s',         # 가. 나. 다.
                r'^\s*\(([가-힣])\)',         # (가) (나) (다)
                r'^\s*([ㄱ-ㅎ])\.\s',         # ㄱ. ㄴ. ㄷ.
            ],
            "level": 2,
            "name": "호"
        },
        
        # 레벨 3: 목 (1.2.3., (1)(2)(3), 1)2)3))
        "mok": {
            "patterns": [
                r'^\s*(\d+)\.\s',             # 1. 2. 3.
                r'^\s*\((\d+)\)',             # (1) (2) (3)
                r'^\s*(\d+)\)\s',             # 1) 2) 3)
            ],
            "level": 3,
            "name": "목"
        },
        
        # 레벨 4: 세목 (①②③, ㉠㉡㉢)
        "item": {
            "patterns": [
                r'^\s*([①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮])',  # ①②③
                r'^\s*([㉠㉡㉢㉣㉤㉥㉦㉧㉨㉩])',      # ㉠㉡㉢
            ],
            "level": 4,
            "name": "세목"
        },
        
        # 레벨 5: 세세목 (a.b.c., (a)(b)(c))
        "subitem": {
            "patterns": [
                r'^\s*([a-z])\.\s',           # a. b. c.
                r'^\s*\(([a-z])\)',           # (a) (b) (c)
                r'^\s*([a-z])\)\s',           # a) b) c)
            ],
            "level": 5,
            "name": "세세목"
        }
    }
    
    # 원형 숫자 맵핑
    CIRCLE_NUMBER_MAP = {
        '①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5,
        '⑥': 6, '⑦': 7, '⑧': 8, '⑨': 9, '⑩': 10,
        '⑪': 11, '⑫': 12, '⑬': 13, '⑭': 14, '⑮': 15
    }
    
    # 한글 순서 맵핑
    HANGUL_ORDER_MAP = {
        '가': 1, '나': 2, '다': 3, '라': 4, '마': 5,
        '바': 6, '사': 7, '아': 8, '자': 9, '차': 10
    }
    
    def detect_structure_elements(self, content: str) -> Dict[str, Any]:
        """
        문서 내용에서 구조 요소를 모두 감지합니다.
        
        Args:
            content: 청크 내용
        
        Returns:
            구조 요소 정보
        """
        detected = {
            "article": [],
            "ho": [],
            "mok": [],
            "item": [],
            "subitem": [],
            "highest_level": None,
            "lowest_level": None,
        }
        
        lines = content.strip().split('\n')
        
        for line_num, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 각 계층별로 패턴 매칭
            for struct_type, struct_info in self.STRUCTURE_PATTERNS.items():
                matched = False
                for pattern in struct_info["patterns"]:
                    match = re.match(pattern, line_stripped)
                    if match:
                        detected[struct_type].append({
                            "text": match.group(0).strip(),
                            "value": match.group(1) if match.groups() else match.group(0),
                            "line": line_stripped,
                            "line_num": line_num,
                            "level": struct_info["level"]
                        })
                        matched = True
                        break
                
                if matched:
                    break
        
        # 계층 범위 결정
        all_levels = []
        for struct_type in ["article", "ho", "mok", "item", "subitem"]:
            if detected[struct_type]:
                all_levels.append(self.STRUCTURE_PATTERNS[struct_type]["level"])
        
        if all_levels:
            detected["highest_level"] = min(all_levels)
            detected["lowest_level"] = max(all_levels)
        
        return detected
    
    def check_sequence_continuity(
        self,
        items: List[Dict[str, Any]],
        struct_type: str
    ) -> Dict[str, Any]:
        """
        항목 순서의 연속성을 체크합니다.
        
        Args:
            items: 항목 리스트
            struct_type: 구조 타입 (mok, item 등)
        
        Returns:
            연속성 정보
        """
        if not items:
            return {"continuous": True, "issues": []}
        
        numbers = []
        issues = []
        
        for item in items:
            value = item["value"]
            num = None
            
            if struct_type == "item":
                # 원형 숫자
                num = self.CIRCLE_NUMBER_MAP.get(value)
            elif struct_type == "ho":
                # 한글
                num = self.HANGUL_ORDER_MAP.get(value)
            elif struct_type in ["mok", "subitem"]:
                # 일반 숫자
                try:
                    num = int(value)
                except:
                    pass
            
            if num:
                numbers.append((num, item))
        
        if not numbers:
            return {"continuous": True, "issues": []}
        
        # 정렬
        numbers.sort(key=lambda x: x[0])
        
        # 1부터 시작하지 않음
        if numbers[0][0] != 1:
            issues.append({
                "type": "not_start_from_one",
                "first_number": numbers[0][0],
                "message": f"{struct_type}이(가) {numbers[0][0]}부터 시작 (1이 아님)"
            })
        
        # 연속되지 않음
        for i in range(len(numbers) - 1):
            current_num = numbers[i][0]
            next_num = numbers[i + 1][0]
            
            if next_num - current_num > 1:
                missing = list(range(current_num + 1, next_num))
                issues.append({
                    "type": "gap",
                    "from": current_num,
                    "to": next_num,
                    "missing": missing,
                    "message": f"{struct_type} 순서 불연속: {current_num} → {next_num} (중간 빠짐: {missing})"
                })
        
        return {
            "continuous": len(issues) == 0,
            "issues": issues
        }
    
    def check_completeness_with_structure(
        self,
        content: str
    ) -> Dict[str, Any]:
        """
        구조 기반 완결성 체크
        
        Args:
            content: 청크 내용
        
        Returns:
            완결성 정보 (front_issues, back_issues 포함)
        """
        structure = self.detect_structure_elements(content)
        
        start_truncated = False
        end_truncated = False
        reasons = []
        front_issues = []  # ⭐ 앞부분 문제들
        back_issues = []   # ⭐ 뒷부분 문제들
        
        content_stripped = content.strip()
        
        # ===== 앞부분 잘림 체크 =====
        
        # 1. 기본 불완전 시작 패턴
        incomplete_start_patterns = [
            (r'^\.{2,}', '...로 시작'),
            (r'^[)\]}"\'"]', '닫는 기호로 시작'),
            (r'^(한다|하여|된다|되어|있다|없다|이다)', '동사 어미로 시작'),
            (r'^[을를의에게는이가와과도]\s', '조사로 시작'),
            (r'^\)[와과를을의에]', '괄호+조사로 시작'),
        ]
        
        for pattern, reason in incomplete_start_patterns:
            if re.match(pattern, content_stripped):
                start_truncated = True
                reasons.append(reason)
                front_issues.append(reason)  # ⭐ 앞부분 이슈 기록
                break
        
        # 2. ⭐ 조항 제목 없이 항목으로 시작 (개선)
        # 조항이 없으면 불완전
        if not structure["article"]:
            # 어떤 하위 항목이라도 있으면 앞이 잘림
            if structure["ho"] or structure["mok"] or structure["item"] or structure["subitem"]:
                start_truncated = True
                reason = "조항 제목 없이 항목으로 시작"
                reasons.append(reason)
                front_issues.append(reason)  # ⭐ 앞부분 이슈 기록
        
        # 3. 항목 순서 체크 - 중간부터 시작
        for struct_type in ["ho", "mok", "item"]:
            items = structure[struct_type]
            if items:
                continuity = self.check_sequence_continuity(items, struct_type)
                if not continuity["continuous"]:
                    for issue in continuity["issues"]:
                        if issue["type"] == "not_start_from_one":
                            start_truncated = True
                            reasons.append(issue["message"])
                            front_issues.append(issue["message"])  # ⭐ 앞부분 이슈 기록
        
        # ===== 뒷부분 잘림 체크 =====
        
        # 1. 문장 종결 부호 없음
        if not re.search(r'[.!?。]$', content_stripped):
            end_truncated = True
            reason = "문장 종결 부호 없음"
            reasons.append(reason)
            back_issues.append(reason)  # ⭐ 뒷부분 이슈 기록
        
        # 2. 불완전한 종료 패턴
        incomplete_end_patterns = [
            r'는\s*$', r'을\s*$', r'를\s*$', r'가\s*$', r'이\s*$',
            r'에\s*$', r'하\s*$', r'된\s*$', r'하여\s*$',
            r'[^\s가-힣]{1,2}\s*$',  # 1-2글자로 끝남
        ]
        
        for pattern in incomplete_end_patterns:
            if re.search(pattern, content_stripped):
                end_truncated = True
                reason = "불완전한 종료 (조사/어미)"
                reasons.append(reason)
                back_issues.append(reason)  # ⭐ 뒷부분 이슈 기록
                break
        
        # 3. 괄호/인용부호 미완성
        open_count = content.count('(') + content.count('[') + content.count('{')
        close_count = content.count(')') + content.count(']') + content.count('}')
        if open_count > close_count:
            end_truncated = True
            reason = "괄호 미완성"
            reasons.append(reason)
            back_issues.append(reason)  # ⭐ 뒷부분 이슈 기록
        
        # 4. 항목 순서 불연속 (중간 빠짐)
        for struct_type in ["ho", "mok", "item"]:
            items = structure[struct_type]
            if items:
                continuity = self.check_sequence_continuity(items, struct_type)
                if not continuity["continuous"]:
                    for issue in continuity["issues"]:
                        if issue["type"] == "gap":
                            end_truncated = True
                            reasons.append(issue["message"])
                            back_issues.append(issue["message"])  # ⭐ 뒷부분 이슈 기록
        
        # 확장 방향 결정
        if start_truncated and end_truncated:
            direction = "both"
        elif start_truncated:
            direction = "prev"
        elif end_truncated:
            direction = "next"
        else:
            direction = "none"
        
        result = {
            "is_complete": not (start_truncated or end_truncated),
            "start_truncated": start_truncated,
            "end_truncated": end_truncated,
            "direction": direction,
            "structure": structure,
            "reasons": reasons,
            "front_issues": front_issues,  # ⭐ 앞부분 이슈 목록
            "back_issues": back_issues      # ⭐ 뒷부분 이슈 목록
        }
        
        logger.debug(
            f"구조 기반 완결성 체크: "
            f"complete={result['is_complete']}, "
            f"direction={direction}, "
            f"front_issues={front_issues}, "
            f"back_issues={back_issues}"
        )
        
        return result

