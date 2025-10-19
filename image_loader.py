"""
ZIP 압축 파일에서 표지 이미지 추출
"""
import zipfile
from io import BytesIO
from PIL import Image
from typing import Optional
import re


def natural_sort_key(filename: str):
    """
    자연스러운 정렬을 위한 키 생성
    예: "001.jpg", "002.jpg", "010.jpg" 순서로 정렬
    """
    parts = re.split(r'(\d+)', filename)
    return [int(part) if part.isdigit() else part.lower() for part in parts]


def is_image_file(filename: str) -> bool:
    """이미지 파일 여부 확인"""
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
    return filename.lower().endswith(image_extensions)


def extract_cover_from_zip(zip_path: str, max_size: tuple = (500, 700)) -> Optional[Image.Image]:
    """
    ZIP 파일에서 첫 번째 이미지 추출 및 썸네일 생성

    Args:
        zip_path: ZIP 파일 경로
        max_size: 최대 크기 (width, height)

    Returns:
        PIL.Image 또는 None (실패 시)
    """
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # 파일 목록 가져오기 및 정렬
            file_list = sorted(zf.namelist(), key=natural_sort_key)

            # 첫 번째 이미지 파일 찾기
            for filename in file_list:
                # 디렉토리 제외
                if filename.endswith('/'):
                    continue

                # 숨김 파일 제외 (맥OS의 __MACOSX 등)
                if '/__MACOSX/' in filename or filename.startswith('.'):
                    continue

                # Thumbs.db 등 시스템 파일 제외
                if 'Thumbs.db' in filename or '.DS_Store' in filename:
                    continue

                # 이미지 파일 확인
                if is_image_file(filename):
                    # 이미지 데이터 읽기
                    img_data = zf.read(filename)

                    # PIL Image 생성
                    img = Image.open(BytesIO(img_data))

                    # RGB 변환 (RGBA, P 모드 등 처리)
                    if img.mode == 'RGBA':
                        # RGBA -> RGB 변환 (투명도 제거)
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])  # Alpha 채널을 마스크로 사용
                        img = background
                    elif img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')

                    # 썸네일 생성 (비율 유지)
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)

                    return img

            # 이미지를 찾지 못함
            return None

    except zipfile.BadZipFile:
        # 손상된 ZIP 파일
        print(f"BadZipFile: {zip_path}")
        return None
    except Exception as e:
        # 기타 오류
        print(f"Error loading image from {zip_path}: {e}")
        return None


def get_first_zip_file(file_paths: list) -> Optional[str]:
    """
    파일 목록에서 첫 번째 ZIP 파일의 경로 반환

    Args:
        file_paths: 파일 경로 목록 (이미 자연스럽게 정렬됨)

    Returns:
        ZIP 파일 전체 경로 또는 None
    """
    for file_path in file_paths:
        if file_path.lower().endswith('.zip'):
            return file_path

    return None
