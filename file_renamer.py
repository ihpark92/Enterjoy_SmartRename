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
    """
    updated_infos = []

    for file_info in file_infos:
        new_info = copy.deepcopy(file_info)

        if file_info.pattern:
            # 새 패턴 생성 (번호만 기존 것 유지)
            new_pattern = FilePattern(
                prefix=template_pattern.prefix,
                title=template_pattern.title,
                number=file_info.pattern.number,  # 기존 번호 유지
                suffix=template_pattern.suffix,
                extension=template_pattern.extension,
                padding_width=template_pattern.padding_width  # 템플릿의 패딩 유지
            )

            new_info.pattern = new_pattern
            new_info.new_name = new_pattern.to_filename()

        updated_infos.append(new_info)

    return updated_infos


def remove_text(file_infos: List[FileInfo], text_to_remove: str, position: str = "all") -> List[FileInfo]:
    """
    모든 파일명에서 특정 텍스트 제거
    사용자가 입력한 공백도 포함하여 정확히 제거

    Args:
        file_infos: 파일 정보 리스트
        text_to_remove: 제거할 텍스트
        position: "all" (모든 문구), "front" (첫 번째만), "back" (마지막만)
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

        # 위치에 따라 텍스트 제거
        if position == "front":
            # 첫 번째 문구만 제거
            name_part = name_part.replace(text_to_remove, "", 1)
        elif position == "back":
            # 마지막 문구만 제거
            parts = name_part.rsplit(text_to_remove, 1)
            name_part = "".join(parts)
        else:  # "all"
            # 모든 문구 제거 (기존 동작)
            name_part = name_part.replace(text_to_remove, "")

        # 중복 공백 제거 (연속된 공백을 하나로)
        import re
        name_part = re.sub(r'\s+', ' ', name_part).strip()

        # 파일명 재결합
        if ext_part:
            new_info.new_name = f"{name_part}.{ext_part}"
        else:
            new_info.new_name = name_part

        # 패턴도 업데이트 (position에 따라)
        if new_info.pattern:
            if position == "front":
                new_info.pattern.prefix = new_info.pattern.prefix.replace(text_to_remove, "", 1)
                new_info.pattern.title = new_info.pattern.title.replace(text_to_remove, "", 1)
                new_info.pattern.suffix = new_info.pattern.suffix.replace(text_to_remove, "", 1)
            elif position == "back":
                new_info.pattern.prefix = "".join(new_info.pattern.prefix.rsplit(text_to_remove, 1))
                new_info.pattern.title = "".join(new_info.pattern.title.rsplit(text_to_remove, 1))
                new_info.pattern.suffix = "".join(new_info.pattern.suffix.rsplit(text_to_remove, 1))
            else:  # "all"
                new_info.pattern.prefix = new_info.pattern.prefix.replace(text_to_remove, "")
                new_info.pattern.title = new_info.pattern.title.replace(text_to_remove, "")
                new_info.pattern.suffix = new_info.pattern.suffix.replace(text_to_remove, "")

        updated_infos.append(new_info)

    return updated_infos


def apply_custom_pattern(file_infos: List[FileInfo], pattern_template: str) -> List[FileInfo]:
    """
    사용자 정의 패턴을 모든 파일에 적용

    Args:
        file_infos: 파일 정보 리스트
        pattern_template: 패턴 템플릿 (예: "제목_{number}화.zip")
                         {number}: 권수
                         {number:02d}: 2자리 패딩 권수
                         {number:03d}: 3자리 패딩 권수

    Returns:
        업데이트된 파일 정보 리스트
    """
    import re

    if not pattern_template:
        return file_infos

    # {number} 또는 {number:XXd} 패턴 찾기
    number_pattern = re.compile(r'\{number(?::0(\d)d)?\}')

    updated_infos = []

    for file_info in file_infos:
        new_info = copy.deepcopy(file_info)

        # 권수 추출
        if new_info.pattern and new_info.pattern.number:
            number_str = new_info.pattern.number
        else:
            # 패턴이 없으면 스킵
            updated_infos.append(new_info)
            continue

        # 패턴 템플릿에서 {number} 치환
        def replace_number(match):
            padding = match.group(1)
            if padding:
                # {number:02d} 형식
                return number_str.zfill(int(padding))
            else:
                # {number} 형식
                return number_str

        new_name = number_pattern.sub(replace_number, pattern_template)
        new_info.new_name = new_name

        updated_infos.append(new_info)

    return updated_infos


def change_padding_width(file_infos: List[FileInfo], padding_width: int) -> List[FileInfo]:
    """
    모든 파일의 권수 자릿수를 변경
    padding_width: 1, 2, 3 (예: 1 → "1", 2 → "01", 3 → "001")
    """
    if padding_width not in [1, 2, 3]:
        return file_infos

    updated_infos = []

    for file_info in file_infos:
        new_info = copy.deepcopy(file_info)

        # 패턴이 있고 숫자가 있는 경우에만 적용
        if new_info.pattern and new_info.pattern.number:
            # 패딩 자릿수 변경
            new_info.pattern.padding_width = padding_width
            # 새 파일명 생성
            new_info.new_name = new_info.pattern.to_filename()

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
