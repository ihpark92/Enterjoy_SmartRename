"""
데이터 모델 정의
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class FilePattern:
    """파일명 패턴 구조"""
    prefix: str = ""           # 접두사: "[공금] "
    title: str = ""            # 제목: "사카모토 데이즈"
    number: str = ""           # 번호: "01"
    suffix: str = ""           # 접미사: "권"
    extension: str = ""        # 확장자: "zip"
    padding_width: int = 2     # 번호 패딩 자릿수 (기본 2자리: 01, 02, ...)

    def to_filename(self) -> str:
        """패턴을 파일명 문자열로 변환"""
        parts = []

        # 접두사 (공백 포함)
        if self.prefix:
            parts.append(self.prefix.strip())

        # 제목 (공백 포함)
        if self.title:
            parts.append(self.title.strip())

        # 번호와 접미사는 공백 없이 붙임
        number_suffix = ""
        if self.number:
            # 숫자인 경우 padding_width만큼 0으로 패딩
            if self.number.isdigit():
                # 숫자 값으로 변환 후 padding_width만큼 패딩 (항상 적용)
                number_value = int(self.number)
                number_suffix = str(number_value).zfill(self.padding_width)
            else:
                number_suffix = self.number
        if self.suffix:
            number_suffix += self.suffix.strip()

        if number_suffix:
            parts.append(number_suffix)

        filename = " ".join(parts)

        if self.extension:
            filename += f".{self.extension}"

        return filename

    def __str__(self):
        return self.to_filename()


@dataclass
class FileInfo:
    """파일 정보"""
    original_path: str                  # 원본 전체 경로
    original_name: str                  # 원본 파일명
    new_name: str = ""                  # 변경될 파일명
    pattern: Optional[FilePattern] = None  # 추출된 패턴

    @property
    def new_path(self) -> str:
        """새 파일 경로 반환"""
        import os
        directory = os.path.dirname(self.original_path)
        return os.path.join(directory, self.new_name)
