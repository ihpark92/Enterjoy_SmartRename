"""
파일명 변경 로직
"""
from typing import List
from models import FilePattern, FileInfo
import copy


def apply_pattern(file_infos: List[FileInfo], template_pattern: FilePattern) -> List[FileInfo]:
    """
    선택한 패턴을 모든 파일에 적용
    각 파일의 번호는 유지하고, 나머지(prefix, title, suffix, extension)는 템플릿 것으로 대체
    파일 개수가 100개 이상이면 3자리(001, 002, ...), 미만이면 2자리(01, 02, ...)로 패딩
    """
    # 파일 개수에 따라 패딩 자릿수 결정
    total_files = len(file_infos)
    if total_files >= 100:
        padding_width = 3
    else:
        padding_width = 2

    updated_infos = []

    for file_info in file_infos:
        new_info = copy.deepcopy(file_info)

        if file_info.pattern:
            # 새 패턴 생성 (번호만 기존 것 유지, padding_width 적용)
            new_pattern = FilePattern(
                prefix=template_pattern.prefix,
                title=template_pattern.title,
                number=file_info.pattern.number,  # 기존 번호 유지
                suffix=template_pattern.suffix,
                extension=template_pattern.extension,
                padding_width=padding_width  # 파일 개수에 따른 패딩
            )

            new_info.pattern = new_pattern
            new_info.new_name = new_pattern.to_filename()

        updated_infos.append(new_info)

    return updated_infos


def remove_text(file_infos: List[FileInfo], text_to_remove: str) -> List[FileInfo]:
    """
    모든 파일명에서 특정 텍스트 제거
    사용자가 입력한 공백도 포함하여 정확히 제거
    """
    if not text_to_remove:
        return file_infos

    updated_infos = []

    for file_info in file_infos:
        new_info = copy.deepcopy(file_info)

        # 확장자 분리
        if '.' in new_info.new_name:
            name_part, ext_part = new_info.new_name.rsplit('.', 1)
        else:
            name_part = new_info.new_name
            ext_part = ""

        # new_name에서 텍스트 제거 (사용자 입력 공백 포함)
        name_part = name_part.replace(text_to_remove, "")

        # 중복 공백 제거 (연속된 공백을 하나로)
        import re
        name_part = re.sub(r'\s+', ' ', name_part).strip()

        # 파일명 재결합
        if ext_part:
            new_info.new_name = f"{name_part}.{ext_part}"
        else:
            new_info.new_name = name_part

        # 패턴도 업데이트
        if new_info.pattern:
            new_info.pattern.prefix = new_info.pattern.prefix.replace(text_to_remove, "")
            new_info.pattern.title = new_info.pattern.title.replace(text_to_remove, "")
            new_info.pattern.suffix = new_info.pattern.suffix.replace(text_to_remove, "")

        updated_infos.append(new_info)

    return updated_infos


def add_text(file_infos: List[FileInfo], text_to_add: str, position: str = "front") -> List[FileInfo]:
    """
    모든 파일명에 텍스트 추가
    position: "front" 또는 "back"
    사용자가 입력한 텍스트를 공백 포함하여 그대로 추가
    """
    if not text_to_add:
        return file_infos

    updated_infos = []

    for file_info in file_infos:
        new_info = copy.deepcopy(file_info)

        # 확장자 분리
        if '.' in new_info.new_name:
            name_part, ext_part = new_info.new_name.rsplit('.', 1)
        else:
            name_part = new_info.new_name
            ext_part = ""

        # 텍스트 추가 (사용자 입력을 그대로 사용)
        if position == "front":
            name_part = f"{text_to_add}{name_part}"
        else:  # back
            name_part = f"{name_part}{text_to_add}"

        # 중복 공백 제거 (연속된 공백을 하나로)
        import re
        name_part = re.sub(r'\s+', ' ', name_part).strip()

        # 파일명 재결합
        if ext_part:
            new_info.new_name = f"{name_part}.{ext_part}"
        else:
            new_info.new_name = name_part

        # 패턴도 업데이트
        if new_info.pattern:
            if position == "front":
                if new_info.pattern.prefix:
                    new_info.pattern.prefix = f"{text_to_add}{new_info.pattern.prefix}"
                else:
                    new_info.pattern.prefix = text_to_add
            else:  # back
                if new_info.pattern.suffix:
                    new_info.pattern.suffix = f"{new_info.pattern.suffix}{text_to_add}"
                else:
                    new_info.pattern.suffix = text_to_add

        updated_infos.append(new_info)

    return updated_infos


def execute_rename(file_infos: List[FileInfo]) -> List[tuple[bool, str, str]]:
    """
    실제 파일명 변경 실행
    Returns: List of (성공 여부, 원본 파일명, 에러 메시지)
    """
    from file_system import rename_file

    results = []

    for file_info in file_infos:
        # 원본과 새 이름이 같으면 스킵
        if file_info.original_name == file_info.new_name:
            results.append((True, file_info.original_name, "변경 불필요"))
            continue

        success, error_msg = rename_file(file_info.original_path, file_info.new_path)
        results.append((success, file_info.original_name, error_msg))

    return results
