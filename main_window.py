"""
GUI 메인 윈도우
"""
import os
import copy
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QRadioButton, QButtonGroup, QTableWidget, QTableWidgetItem,
    QFileDialog, QLineEdit, QMessageBox, QHeaderView, QSplitter
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import List, Optional

from models import FilePattern, FileInfo
from pattern_analyzer import analyze_files, extract_pattern
from file_renamer import apply_pattern, remove_text, add_text, execute_rename
from file_system import get_files_in_folder, check_conflicts, validate_filename, get_first_archive_file
from cover_image_widget import CoverImageWidget
from image_loader import extract_cover_from_zip


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_infos: List[FileInfo] = []
        self.representative_patterns: List[FilePattern] = []
        self.selected_pattern: Optional[FilePattern] = None
        self.current_folder: str = ""

        # Undo 기능을 위한 히스토리 (이전 상태 저장)
        self.previous_file_infos: Optional[List[FileInfo]] = None

        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("엔쪼 스마트리네임")
        self.setGeometry(100, 100, 1200, 750)  # 너비 1000→1200으로 증가

        # 전체 폰트 설정 (개선 1: 맑은 고딕, 개선 2: 10pt)
        app_font = QFont("맑은 고딕", 10)
        self.setFont(app_font)

        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 메인 레이아웃 (개선 5: 여백 추가)
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)  # 위젯 간 간격 증가
        main_layout.setContentsMargins(20, 20, 20, 20)  # 전체 여백 추가
        central_widget.setLayout(main_layout)

        # 1. 폴더 선택 영역
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(10)  # 개선 5: 버튼과 레이블 간격

        self.folder_button = QPushButton("폴더 선택")
        self.folder_button.setMinimumHeight(35)  # 버튼 높이 증가
        self.folder_button.clicked.connect(self.select_folder)

        self.folder_label = QLabel("폴더를 선택하세요")
        self.folder_label.setFont(QFont("맑은 고딕", 10))  # 폰트 명시 적용
        self.folder_label.setStyleSheet("padding: 8px; background-color: #f0f0f0; border-radius: 3px;")

        folder_layout.addWidget(self.folder_button)
        folder_layout.addWidget(self.folder_label, 1)  # stretch factor
        main_layout.addLayout(folder_layout, 0)  # stretch=0: 고정 크기

        # 2. 이미지 + 컨텐츠 영역 (QSplitter 사용) - 가변 영역
        content_splitter = QSplitter(Qt.Horizontal)

        # 2-1. 왼쪽: 표지 이미지
        self.cover_image_widget = CoverImageWidget()
        content_splitter.addWidget(self.cover_image_widget)

        # 2-2. 오른쪽: 패턴 선택 + 미리보기 테이블
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 패턴 선택 영역 (고정 크기)
        pattern_label = QLabel("검출된 패턴:")
        pattern_label.setFont(QFont("맑은 고딕", 12, QFont.Bold))  # 제목 강조
        right_layout.addWidget(pattern_label, 0)  # stretch=0: 고정

        self.pattern_button_group = QButtonGroup()
        self.pattern_layout = QVBoxLayout()
        right_layout.addLayout(self.pattern_layout, 0)  # stretch=0: 고정

        # 미리보기 테이블 (가변 크기)
        preview_label = QLabel("미리보기:")
        preview_label.setFont(QFont("맑은 고딕", 12, QFont.Bold))  # 제목 강조
        right_layout.addWidget(preview_label, 0)  # stretch=0: 고정

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(2)
        self.preview_table.setHorizontalHeaderLabels(["원본 파일명", "변경될 파일명"])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # 개선 3: 테이블 행 높이 증가
        self.preview_table.verticalHeader().setDefaultSectionSize(35)

        # 개선 4: 색상 대비 개선
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                selection-background-color: #0078d4;
                selection-color: white;
                alternate-background-color: #f5f5f5;
            }
            QHeaderView::section {
                background-color: #e9e9e9;
                padding: 8px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
            }
        """)

        right_layout.addWidget(self.preview_table, 1)  # stretch=1: 가변 크기 (세로 확장)

        right_widget.setLayout(right_layout)
        content_splitter.addWidget(right_widget)

        # Splitter 초기 크기 비율 설정 (1:5 = 이미지:컨텐츠)
        content_splitter.setSizes([200, 1000])

        # Splitter를 메인 레이아웃에 추가 (가변 영역)
        main_layout.addWidget(content_splitter, 1)  # stretch=1: 세로 확장

        # 3. 추가 편집 영역 (고정 크기)
        edit_label = QLabel("추가 편집:")
        edit_label.setFont(QFont("맑은 고딕", 12, QFont.Bold))  # 제목 강조
        main_layout.addWidget(edit_label, 0)  # stretch=0: 고정 크기

        # 3-1. 제거 기능
        remove_layout = QHBoxLayout()
        remove_layout.setSpacing(10)  # 개선 5: 간격

        remove_label = QLabel("제거:")
        remove_label.setMinimumWidth(60)

        self.remove_input = QLineEdit()
        self.remove_input.setPlaceholderText("제거할 텍스트 입력")
        self.remove_input.setMinimumHeight(30)
        self.remove_input.setMaximumHeight(30)  # 최대 높이 고정

        self.remove_button = QPushButton("적용")
        self.remove_button.setMinimumHeight(30)
        self.remove_button.setMaximumHeight(30)  # 최대 높이 고정
        self.remove_button.setMinimumWidth(80)
        self.remove_button.clicked.connect(self.remove_text_action)

        self.remove_undo_button = QPushButton("취소")
        self.remove_undo_button.setMinimumHeight(30)
        self.remove_undo_button.setMaximumHeight(30)  # 최대 높이 고정
        self.remove_undo_button.setMinimumWidth(80)
        self.remove_undo_button.setEnabled(False)  # 초기에는 비활성화
        self.remove_undo_button.clicked.connect(self.undo_action)

        remove_layout.addWidget(remove_label)
        remove_layout.addWidget(self.remove_input, 1)
        remove_layout.addWidget(self.remove_button)
        remove_layout.addWidget(self.remove_undo_button)
        main_layout.addLayout(remove_layout, 0)  # stretch=0: 고정 크기

        # 3-2. 추가 기능
        add_layout = QHBoxLayout()
        add_layout.setSpacing(10)  # 개선 5: 간격

        add_label = QLabel("추가:")
        add_label.setMinimumWidth(60)

        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText("추가할 텍스트 입력")
        self.add_input.setMinimumHeight(30)
        self.add_input.setMaximumHeight(30)  # 최대 높이 고정

        # 앞/뒤 선택
        self.add_front_radio = QRadioButton("앞")
        self.add_back_radio = QRadioButton("뒤")
        self.add_front_radio.setChecked(True)

        self.add_button = QPushButton("적용")
        self.add_button.setMinimumHeight(30)
        self.add_button.setMaximumHeight(30)  # 최대 높이 고정
        self.add_button.setMinimumWidth(80)
        self.add_button.clicked.connect(self.add_text_action)

        self.add_undo_button = QPushButton("취소")
        self.add_undo_button.setMinimumHeight(30)
        self.add_undo_button.setMaximumHeight(30)  # 최대 높이 고정
        self.add_undo_button.setMinimumWidth(80)
        self.add_undo_button.setEnabled(False)  # 초기에는 비활성화
        self.add_undo_button.clicked.connect(self.undo_action)

        add_layout.addWidget(add_label)
        add_layout.addWidget(self.add_input, 1)
        add_layout.addWidget(self.add_front_radio)
        add_layout.addWidget(self.add_back_radio)
        add_layout.addWidget(self.add_button)
        add_layout.addWidget(self.add_undo_button)
        main_layout.addLayout(add_layout, 0)  # stretch=0: 고정 크기

        # 4. 하단 버튼 (고정 크기)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)  # 개선 5: 버튼 간격

        self.execute_button = QPushButton("파일명 변경 실행")
        self.execute_button.setMinimumHeight(40)
        self.execute_button.setMaximumHeight(40)  # 최대 높이 고정
        self.execute_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                font-weight: bold;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cc1;
            }
        """)
        self.execute_button.clicked.connect(self.execute_rename_action)

        button_layout.addWidget(self.execute_button)
        main_layout.addLayout(button_layout, 0)  # stretch=0: 고정 크기

    def select_folder(self):
        """폴더 선택"""
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")

        if folder:
            self.current_folder = folder
            self.folder_label.setText(folder)
            self.load_files(folder)

    def load_files(self, folder_path: str):
        """폴더의 파일 로드 및 패턴 분석"""
        # 파일 목록 가져오기
        file_paths = get_files_in_folder(folder_path)

        if not file_paths:
            QMessageBox.warning(self, "경고", "폴더에 파일이 없습니다.")
            self.cover_image_widget.clear()  # 이미지 제거
            return

        # 파일명만 추출
        filenames = [os.path.basename(path) for path in file_paths]

        # 패턴 분석
        self.file_infos, self.representative_patterns = analyze_files(filenames)

        # 전체 경로 설정
        for i, file_info in enumerate(self.file_infos):
            file_info.original_path = file_paths[i]

        # 패턴이 없으면 경고
        if not self.representative_patterns:
            QMessageBox.warning(self, "경고", "파일명 패턴을 찾을 수 없습니다.")
            self.cover_image_widget.clear()  # 이미지 제거
            return

        # 패턴 라디오 버튼 생성
        self.create_pattern_buttons()

        # 미리보기 업데이트
        self.refresh_preview()

        # 표지 이미지 로드
        self.load_cover_image(file_paths)

    def load_cover_image(self, file_paths: list):
        """
        첫 번째 ZIP 파일에서 표지 이미지 추출 및 표시

        Args:
            file_paths: 파일 경로 목록 (이미 정렬됨)
        """
        # 첫 번째 ZIP 파일 찾기
        first_zip = get_first_archive_file(file_paths)

        if first_zip is None:
            # ZIP 파일이 없으면 빈 공간
            self.cover_image_widget.clear()
            return

        try:
            # ZIP에서 표지 추출
            cover_img = extract_cover_from_zip(first_zip, max_size=(500, 700))

            # 위젯에 표시
            self.cover_image_widget.set_pil_image(cover_img)

        except Exception as e:
            # 오류 발생 시 빈 공간
            print(f"표지 로드 실패: {e}")
            self.cover_image_widget.clear()

    def create_pattern_buttons(self):
        """패턴 선택 라디오 버튼 생성"""
        # 기존 버튼 제거
        for i in reversed(range(self.pattern_layout.count())):
            widget = self.pattern_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 파일 개수에 따른 패딩 자릿수 결정
        total_files = len(self.file_infos)
        padding_width = 3 if total_files >= 100 else 2

        # 새 버튼 생성
        for i, pattern in enumerate(self.representative_patterns):
            # 패턴에 padding_width 설정
            pattern.padding_width = padding_width
            radio = QRadioButton(str(pattern))
            self.pattern_button_group.addButton(radio, i)
            self.pattern_layout.addWidget(radio)

        # 초기에는 아무 패턴도 선택하지 않음
        self.selected_pattern = None

        # 패턴 선택 시 이벤트
        self.pattern_button_group.buttonClicked.connect(self.on_pattern_selected)

    def on_pattern_selected(self, button):
        """패턴 선택 시 호출"""
        selected_id = self.pattern_button_group.id(button)
        self.selected_pattern = self.representative_patterns[selected_id]

        # 선택한 패턴 적용
        self.file_infos = apply_pattern(self.file_infos, self.selected_pattern)

        # 미리보기 업데이트
        self.refresh_preview()

    def refresh_preview(self):
        """미리보기 테이블 업데이트"""
        self.preview_table.setRowCount(len(self.file_infos))

        for i, file_info in enumerate(self.file_infos):
            # 원본 파일명
            original_item = QTableWidgetItem(file_info.original_name)
            self.preview_table.setItem(i, 0, original_item)

            # 변경될 파일명
            new_item = QTableWidgetItem(file_info.new_name)

            # 이름이 바뀌는 경우 색상 변경
            if file_info.original_name != file_info.new_name:
                new_item.setBackground(Qt.yellow)

            self.preview_table.setItem(i, 1, new_item)

    def undo_action(self):
        """마지막 작업 취소"""
        if self.previous_file_infos is None:
            QMessageBox.warning(self, "경고", "취소할 작업이 없습니다.")
            return

        # 이전 상태로 복원
        self.file_infos = self.previous_file_infos
        self.previous_file_infos = None

        # 취소 버튼 비활성화
        self.remove_undo_button.setEnabled(False)
        self.add_undo_button.setEnabled(False)

        # 미리보기 업데이트
        self.refresh_preview()

        QMessageBox.information(self, "완료", "이전 상태로 복원되었습니다.")

    def remove_text_action(self):
        """텍스트 제거"""
        text = self.remove_input.text()

        if not text:
            QMessageBox.warning(self, "경고", "제거할 텍스트를 입력하세요.")
            return

        # 이전 상태 저장
        self.previous_file_infos = copy.deepcopy(self.file_infos)

        # 텍스트 제거 적용
        self.file_infos = remove_text(self.file_infos, text)

        # 취소 버튼 활성화
        self.remove_undo_button.setEnabled(True)
        self.add_undo_button.setEnabled(True)

        # 미리보기 업데이트
        self.refresh_preview()

    def add_text_action(self):
        """텍스트 추가"""
        text = self.add_input.text()

        if not text:
            QMessageBox.warning(self, "경고", "추가할 텍스트를 입력하세요.")
            return

        # 이전 상태 저장
        self.previous_file_infos = copy.deepcopy(self.file_infos)

        # 텍스트 추가 적용
        position = "front" if self.add_front_radio.isChecked() else "back"
        self.file_infos = add_text(self.file_infos, text, position)

        # 취소 버튼 활성화
        self.remove_undo_button.setEnabled(True)
        self.add_undo_button.setEnabled(True)

        # 미리보기 업데이트
        self.refresh_preview()

    def execute_rename_action(self):
        """파일명 변경 실행"""
        if not self.file_infos:
            QMessageBox.warning(self, "경고", "변경할 파일이 없습니다.")
            return

        # 패턴 선택 확인
        if self.selected_pattern is None:
            QMessageBox.warning(self, "경고", "패턴을 먼저 선택해주세요.")
            return

        # 유효성 검사
        for file_info in self.file_infos:
            valid, error_msg = validate_filename(file_info.new_name)
            if not valid:
                QMessageBox.critical(self, "오류", f"잘못된 파일명: {file_info.new_name}\n{error_msg}")
                return

        # 충돌 검사
        no_conflict, conflicts = check_conflicts(self.file_infos)
        if not no_conflict:
            conflict_list = "\n".join(conflicts)
            QMessageBox.critical(self, "오류", f"파일명 충돌이 발생했습니다:\n{conflict_list}")
            return

        # 확인 메시지
        reply = QMessageBox.question(
            self,
            "확인",
            f"{len(self.file_infos)}개 파일의 이름을 변경하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.No:
            return

        # 실행
        results = execute_rename(self.file_infos)

        # 결과 확인
        success_count = sum(1 for success, _, _ in results if success)
        fail_count = len(results) - success_count

        if fail_count == 0:
            QMessageBox.information(self, "완료", f"{success_count}개 파일명 변경 완료!")
            # 폴더 다시 로드
            if self.current_folder:
                self.load_files(self.current_folder)
        else:
            error_messages = "\n".join([f"{name}: {msg}" for success, name, msg in results if not success])
            QMessageBox.warning(
                self,
                "부분 완료",
                f"성공: {success_count}개\n실패: {fail_count}개\n\n실패 내역:\n{error_messages}"
            )
