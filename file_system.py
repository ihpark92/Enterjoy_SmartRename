"""
파일 시스템 유틸리티
"""
import os
import re
from typing import List, Tuple, Optional
from models import FileInfo


def natural_sort_key(path: str) -> List:
    """
    자연스러운 정렬을 위한 키 생성 함수
    예: "file1.txt", "file2.txt", "file10.txt" 순서로 정렬
    """
    filename = os.path.basename(path)
    # 숫자와 비숫자 부분으로 분리
    parts = re.split(r'(\d+)', filename)
    # 숫자 부분은 정수로 변환, 나머지는 소문자로
    return [int(part) if part.isdigit() else part.lower() for part in parts]


def get_files_in_folder(folder_path: str) -> List[str]:
    """
    폴더 내의 모든 파일 목록 반환 (서브 폴더 제외)
    자연스러운 숫자 정렬 적용 (1, 2, 3, ..., 10, 11, 12)
    """
    if not os.path.exists(folder_path):
        return []

    if not os.path.isdir(folder_path):
        return []

    files = []
    try:
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path):
                files.append(item_path)
    except PermissionError:
        pass

    # 자연스러운 정렬 적용
    files.sort(key=natural_sort_key)

    return files


def validate_filename(filename: str) -> Tuple[bool, str]:
    """
    Windows 파일명 유효성 검사
    Returns: (유효 여부, 에러 메시지)
    """
    # Windows 금지 문자
    invalid_chars = r'[<>:"/\\|?*]'

    if re.search(invalid_chars, filename):
        return False, "파일명에 사용할 수 없는 문자가 포함되어 있습니다: < > : \" / \\ | ? *"

    # 예약어 검사
    reserved_names = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]

    name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
    if name_without_ext.upper() in reserved_names:
        return False, f"'{name_without_ext}'는 Windows 예약어입니다."

    # 파일명 길이 검사 (너무 길면 경고)
    if len(filename) > 200:
        return False, "파일명이 너무 깁니다 (200자 초과)."

    return True, ""


def check_conflicts(file_infos: List[FileInfo]) -> Tuple[bool, List[str]]:
    """
    파일명 충돌 검사
    Returns: (충돌 없음 여부, 충돌 파일명 리스트)
    """
    new_names = {}
    conflicts = []

    for file_info in file_infos:
        new_name_lower = file_info.new_name.lower()

        if new_name_lower in new_names:
            # 충돌 발견
            if new_name_lower not in conflicts:
                conflicts.append(file_info.new_name)
        else:
            new_names[new_name_lower] = file_info

    return len(conflicts) == 0, conflicts


def get_first_archive_file(file_paths: List[str]) -> Optional[str]:
    """
    파일 목록에서 첫 번째 압축 파일 경로 반환

    Args:
        file_paths: 파일 경로 목록 (이미 자연스럽게 정렬됨)

    Returns:
        첫 번째 ZIP 파일 경로 또는 None
    """
    for file_path in file_paths:
        if file_path.lower().endswith('.zip'):
            return file_path

    return None


def rename_file(old_path: str, new_path: str) -> Tuple[bool, str]:
    """
    실제 파일명 변경
    Returns: (성공 여부, 에러 메시지)
    """
    try:
        if not os.path.exists(old_path):
            return False, f"파일을 찾을 수 없습니다: {old_path}"

        if os.path.exists(new_path):
            return False, f"대상 파일이 이미 존재합니다: {new_path}"

        os.rename(old_path, new_path)
        return True, ""

    except PermissionError:
        return False, "파일 접근 권한이 없습니다."
    except Exception as e:
        return False, f"파일명 변경 실패: {str(e)}"
