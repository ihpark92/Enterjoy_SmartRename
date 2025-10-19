"""
파일명 패턴 분석 엔진
"""
import re
from typing import List, Dict
from collections import defaultdict
from models import FilePattern, FileInfo


def extract_pattern(filename: str) -> FilePattern:
    """
    파일명에서 패턴 추출
    예: "[공금] 사카모토 데이즈 06권.zip"
    → prefix="[공금]", title="사카모토 데이즈", number="06", suffix="권", ext="zip"

    개선된 로직:
    - 끝의 대괄호를 먼저 제거하여 선택적 부분으로 처리
    - 마지막 숫자를 권수/화수로 인식 (제목 내 숫자와 구분)
    - suffix는 숫자 바로 뒤의 텍스트만 (권, 화 등)
    """
    # 확장자 분리
    name_without_ext = filename
    extension = ""
    if '.' in filename:
        parts = filename.rsplit('.', 1)
        name_without_ext = parts[0]
        extension = parts[1]

    # 접두사 추출 (대괄호로 시작)
    prefix = ""
    prefix_match = re.match(r'^(\[.*?\])\s*', name_without_ext)
    if prefix_match:
        prefix = prefix_match.group(1)
        name_without_ext = name_without_ext[len(prefix):].strip()

    # 끝의 대괄호 추출 (suffix에 포함시킬 선택적 부분)
    suffix_bracket = ""
    has_space_before_bracket = False
    suffix_match = re.search(r'(\s*)(\[.*?\])$', name_without_ext)
    if suffix_match:
        space_before = suffix_match.group(1)  # 대괄호 앞의 공백
        suffix_bracket = suffix_match.group(2)  # 대괄호 부분만
        has_space_before_bracket = len(space_before) > 0  # 공백이 있었는지 기록
        # 대괄호와 앞의 공백을 모두 제거
        name_without_bracket = name_without_ext[:suffix_match.start()].strip()
    else:
        name_without_bracket = name_without_ext

    # 모든 숫자 찾기 (마지막 숫자를 권수로 사용)
    number_matches = list(re.finditer(r'(\d+)', name_without_bracket))

    number = ""
    title = ""
    suffix = ""

    if number_matches:
        # 마지막 숫자를 권수/화수로 간주
        last_number_match = number_matches[-1]
        number = last_number_match.group(1)
        number_pos = last_number_match.start()
        number_end = last_number_match.end()

        # 제목: 마지막 숫자 이전까지
        title = name_without_bracket[:number_pos].strip()

        # 접미사: 마지막 숫자 바로 뒤의 텍스트 + 대괄호
        suffix_text = name_without_bracket[number_end:].strip()

        # suffix는 텍스트 + 대괄호 결합 (원본의 공백 여부 유지)
        if suffix_text and suffix_bracket:
            # 원본에 공백이 있었다면 공백 포함, 없었다면 공백 없이
            if has_space_before_bracket:
                suffix = suffix_text + " " + suffix_bracket
            else:
                suffix = suffix_text + suffix_bracket
        elif suffix_text:
            suffix = suffix_text
        elif suffix_bracket:
            suffix = suffix_bracket
    else:
        # 숫자가 없는 경우
        title = name_without_bracket.strip()
        suffix = suffix_bracket if suffix_bracket else ""

    return FilePattern(
        prefix=prefix,
        title=title,
        number=number,
        suffix=suffix,
        extension=extension
    )


def group_patterns(file_infos: List[FileInfo]) -> Dict[str, List[FileInfo]]:
    """
    유사한 패턴끼리 그룹화
    그룹 키: prefix + title + suffix + extension
    """
    groups = defaultdict(list)

    for file_info in file_infos:
        pattern = file_info.pattern
        if pattern:
            # 번호를 제외한 나머지로 그룹 키 생성
            group_key = f"{pattern.prefix}|{pattern.title}|{pattern.suffix}|{pattern.extension}"
            groups[group_key].append(file_info)

    return dict(groups)


def get_representative_patterns(groups: Dict[str, List[FileInfo]]) -> List[FilePattern]:
    """
    각 그룹의 대표 패턴 반환 (첫 번째 파일의 패턴)
    """
    representatives = []

    for group_files in groups.values():
        if group_files and group_files[0].pattern:
            representatives.append(group_files[0].pattern)

    return representatives


def analyze_files(filenames: List[str]) -> tuple[List[FileInfo], List[FilePattern]]:
    """
    파일명 리스트를 분석하여 FileInfo와 대표 패턴 반환
    """
    file_infos = []

    # 각 파일명에서 패턴 추출
    for filename in filenames:
        pattern = extract_pattern(filename)
        file_info = FileInfo(
            original_path="",  # 나중에 설정
            original_name=filename,
            new_name=filename,
            pattern=pattern
        )
        file_infos.append(file_info)

    # 패턴 그룹화
    groups = group_patterns(file_infos)

    # 대표 패턴 추출
    representative_patterns = get_representative_patterns(groups)

    return file_infos, representative_patterns
