"""
이미지 전처리 유틸리티
OpenCV 기반 이미지 품질 개선
"""
import cv2
import numpy as np
from PIL import Image
from typing import Union
import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """이미지 전처리기"""
    
    def __init__(self):
        """초기화"""
        self.default_dpi = 300
    
    def preprocess(
        self,
        image: Union[Image.Image, np.ndarray],
        apply_grayscale: bool = True,
        apply_noise_removal: bool = True,
        apply_deskew: bool = False
    ) -> np.ndarray:
        """
        이미지 전처리 파이프라인
        
        Args:
            image: PIL Image 또는 numpy array
            apply_grayscale: 그레이스케일 변환 여부
            apply_noise_removal: 노이즈 제거 여부
            apply_deskew: 기울기 보정 여부
            
        Returns:
            전처리된 이미지 (numpy array)
        """
        # PIL Image를 numpy array로 변환
        if isinstance(image, Image.Image):
            img = np.array(image)
        else:
            img = image.copy()
        
        # 1. 그레이스케일 변환
        if apply_grayscale and len(img.shape) == 3:
            img = self.convert_to_grayscale(img)
        
        # 2. 노이즈 제거
        if apply_noise_removal:
            img = self.remove_noise(img)
        
        # 3. 기울기 보정
        if apply_deskew:
            img = self.deskew(img)
        
        return img
    
    def convert_to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """
        그레이스케일 변환
        
        Args:
            image: 컬러 이미지
            
        Returns:
            그레이스케일 이미지
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            logger.debug("그레이스케일 변환 완료")
            return gray
        return image
    
    def remove_noise(self, image: np.ndarray) -> np.ndarray:
        """
        노이즈 제거 (미디언 블러)
        
        Args:
            image: 입력 이미지
            
        Returns:
            노이즈 제거된 이미지
        """
        # 미디언 블러 적용 (3x3 커널)
        denoised = cv2.medianBlur(image, 3)
        logger.debug("노이즈 제거 완료")
        return denoised
    
    def apply_adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """
        적응적 이진화
        
        Args:
            image: 그레이스케일 이미지
            
        Returns:
            이진화된 이미지
        """
        # 그레이스케일 확인
        if len(image.shape) == 3:
            image = self.convert_to_grayscale(image)
        
        # 적응적 이진화
        binary = cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )
        logger.debug("적응적 이진화 완료")
        return binary
    
    def deskew(self, image: np.ndarray) -> np.ndarray:
        """
        기울기 보정
        
        Args:
            image: 입력 이미지
            
        Returns:
            기울기 보정된 이미지
        """
        # 그레이스케일 확인
        if len(image.shape) == 3:
            gray = self.convert_to_grayscale(image)
        else:
            gray = image
        
        # 이진화
        thresh = cv2.threshold(
            gray, 0, 255,
            cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )[1]
        
        # 기울기 각도 계산
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) == 0:
            return image
        
        angle = cv2.minAreaRect(coords)[-1]
        
        # 각도 조정
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # 회전이 거의 없으면 원본 반환
        if abs(angle) < 0.5:
            return image
        
        # 이미지 회전
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        
        logger.debug(f"기울기 보정 완료: {angle:.2f}도")
        return rotated
    
    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        대비 향상 (CLAHE)
        
        Args:
            image: 그레이스케일 이미지
            
        Returns:
            대비 향상된 이미지
        """
        # 그레이스케일 확인
        if len(image.shape) == 3:
            image = self.convert_to_grayscale(image)
        
        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)
        logger.debug("대비 향상 완료")
        return enhanced
    
    def pil_to_numpy(self, pil_image: Image.Image) -> np.ndarray:
        """PIL Image를 numpy array로 변환"""
        return np.array(pil_image)
    
    def numpy_to_pil(self, np_image: np.ndarray) -> Image.Image:
        """numpy array를 PIL Image로 변환"""
        return Image.fromarray(np_image)

