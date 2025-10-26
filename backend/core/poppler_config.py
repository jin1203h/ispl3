"""
Poppler 설정
Windows에서 pdf2image 사용을 위한 Poppler 경로 설정
"""
import os
from pathlib import Path
import platform


def get_poppler_path():
    """
    Poppler 실행 파일 경로 반환
    
    Returns:
        Poppler bin 경로 또는 None (시스템 PATH 사용)
    """
    # Windows인 경우만 처리
    if platform.system() != "Windows":
        return None
    
    # 환경 변수로 POPPLER_PATH 설정 확인
    env_poppler = os.getenv("POPPLER_PATH")
    if env_poppler and Path(env_poppler).exists():
        return env_poppler
    
    # 일반적인 설치 경로 확인
    possible_paths = [
        r"C:\poppler\Library\bin",
        r"C:\poppler\bin",
        r"C:\Program Files\poppler\bin",
        Path.cwd() / "poppler" / "Library" / "bin",
        Path.cwd().parent / "poppler" / "Library" / "bin",
    ]
    
    for path in possible_paths:
        path = Path(path)
        if path.exists() and (path / "pdftoppm.exe").exists():
            return str(path)
    
    # 찾지 못하면 None 반환 (시스템 PATH 의존)
    return None


# 전역 변수로 설정
POPPLER_PATH = get_poppler_path()

