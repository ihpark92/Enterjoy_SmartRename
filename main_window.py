"""
GUI 메인 윈도우
"""
import os
import copy
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QRadioButton, QButtonGroup, QTableWidget, QTableWidgetItem,
    QFileDialog, QLineEdit, QMessageBox, QHeaderView, QSplitter, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import List, Optional

from models import FilePattern, FileInfo
from pattern_analyzer import analyze_files, extract_pattern
from file_renamer import apply_pattern, remove_text, add_text, execute_rename, apply_custom_pattern
from file_system import get_files_in_folder, check_conflicts, validate_filename, get_first_archive_file
from cover_image_widget import CoverImageWidget
from image_loader import extract_cover_from_zip
from preview_table_widget import PreviewTableWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.file_infos: List[FileInfo] = []
        self.representative_patterns: List[FilePattern] = []
        self.selected_pattern: Optional[FilePattern] = None
        self.current_folder: str = ""

        # Undo 기능을 위한 히스토리 (이전 상태 저장)
        self.previous_file_infos_remove: Optional[List[FileInfo]] = None
        self.previous_file_infos_add: Optional[List[FileInfo]] = None
        self.previous_file_infos_pattern: Optional[List[FileInfo]] = None
        self.previous_pattern_text: Optional[str] = None  # 패턴 편집 이전 텍스트

        # 이미지 캐시 (파일 경로 -> PIL.Image)
        self.image_cache = {}

        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("Comic SmartRenamer v1.0")
        self.setGeometry(100, 100, 1500, 900)  # 표지 500px 크기에 맞춘 윈도우 크기

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

        # 1. 폴더 선택 영역 (개선된 스타일)
        folder_container = QWidget()
        folder_container.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: none;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(12)
        folder_layout.setContentsMargins(0, 0, 0, 0)

        self.folder_button = QPushButton("📁 폴더 선택")
        self.folder_button.setMinimumHeight(40)
        self.folder_button.setMinimumWidth(120)
        self.folder_button.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        self.folder_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cc1;
            }
        """)
        self.folder_button.clicked.connect(self.select_folder)

        self.folder_label = QLabel("폴더를 선택하세요")
        self.folder_label.setFont(QFont("맑은 고딕", 10))
        self.folder_label.setStyleSheet("""
            QLabel {
                padding: 10px 15px;
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 6px;
                color: #495057;
            }
        """)

        folder_layout.addWidget(self.folder_button)
        folder_layout.addWidget(self.folder_label, 1)
        folder_container.setLayout(folder_layout)
        main_layout.addWidget(folder_container, 0)

        # 2. 표지 미리보기 옵션 (Splitter 위에 배치)
        preview_option_layout = QHBoxLayout()
        preview_option_layout.setSpacing(10)

        self.preview_all_covers_checkbox = QCheckBox("파일 선택 시 표지 미리보기")
        self.preview_all_covers_checkbox.setFont(QFont("맑은 고딕", 10))
        self.preview_all_covers_checkbox.setChecked(True)  # 기본값: 켜짐
        self.preview_all_covers_checkbox.stateChanged.connect(self.on_preview_option_changed)

        preview_option_layout.addWidget(self.preview_all_covers_checkbox)
        preview_option_layout.addStretch()
        main_layout.addLayout(preview_option_layout, 0)  # stretch=0: 고정 크기

        # 3. 이미지 + 컨텐츠 영역 (QSplitter 사용) - 가변 영역
        content_splitter = QSplitter(Qt.Horizontal)

        # 3-1. 왼쪽: 표지 이미지
        self.cover_image_widget = CoverImageWidget()
        content_splitter.addWidget(self.cover_image_widget)

        # 3-2. 오른쪽: 패턴 선택 + 미리보기 테이블
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 패턴 선택 영역 (고정 크기)
        pattern_label = QLabel("검출된 패턴 :")
        pattern_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))  # 제목 강조
        right_layout.addWidget(pattern_label, 0)  # stretch=0: 고정

        # 패턴 박스 컨테이너 (시각적 개선)
        self.pattern_container = QWidget()
        self.pattern_container.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
            }
        """)

        self.pattern_button_group = QButtonGroup()
        self.pattern_layout = QVBoxLayout()
        self.pattern_layout.setSpacing(8)  # 버튼 간격
        self.pattern_layout.setContentsMargins(5, 5, 5, 5)  # 내부 여백
        self.pattern_container.setLayout(self.pattern_layout)

        right_layout.addWidget(self.pattern_container, 0)  # stretch=0: 고정

        # 미리보기 테이블 (가변 크기)
        preview_header_layout = QHBoxLayout()
        preview_header_layout.setSpacing(10)
        preview_header_layout.setContentsMargins(0, 0, 0, 0)

        preview_label = QLabel("미리보기 :")
        preview_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))  # 제목 강조
        preview_header_layout.addWidget(preview_label)
        preview_header_layout.addStretch()

        # 초기화 버튼 추가
        self.reset_button = QPushButton("🔄 초기화")
        self.reset_button.setFont(QFont("맑은 고딕", 10))
        self.reset_button.setMinimumHeight(30)
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #adb5bd;
            }
        """)
        self.reset_button.setEnabled(False)  # 초기에는 비활성화
        self.reset_button.clicked.connect(self.reset_preview)
        preview_header_layout.addWidget(self.reset_button)

        right_layout.addLayout(preview_header_layout, 0)  # stretch=0: 고정

        # 드래그 앤 드롭을 지원하는 커스텀 테이블 위젯 사용
        self.preview_table = PreviewTableWidget()
        self.preview_table.setColumnCount(2)
        self.preview_table.setHorizontalHeaderLabels(["원본 파일명", "변경될 파일명"])
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # 테이블 편집 불가능하도록 설정
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)

        # 개선 3: 테이블 행 높이 증가
        self.preview_table.verticalHeader().setDefaultSectionSize(35)

        # 테이블 선택 이벤트 연결 (마우스 클릭 + 키보드 방향키)
        self.preview_table.itemClicked.connect(self.on_table_item_clicked)
        self.preview_table.currentItemChanged.connect(self.on_table_current_item_changed)

        # 드래그 앤 드롭 이벤트 연결
        self.preview_table.folder_dropped.connect(self.on_folder_dropped)
        self.preview_table.files_dropped.connect(self.on_files_dropped)

        # 개선 4: 색상 대비 개선
        self.preview_table.setAlternatingRowColors(True)

        right_layout.addWidget(self.preview_table, 1)  # stretch=1: 가변 크기 (세로 확장)

        right_widget.setLayout(right_layout)
        content_splitter.addWidget(right_widget)

        # Splitter 초기 크기 비율 설정 (1:2 = 이미지:컨텐츠, 표지 500px 최대 크기)
        content_splitter.setSizes([500, 1000])

        # Splitter를 메인 레이아웃에 추가 (가변 영역)
        main_layout.addWidget(content_splitter, 1)  # stretch=1: 세로 확장

        # 4. 추가 편집 영역 (고정 크기)
        edit_label = QLabel("추가 편집 :")
        edit_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        main_layout.addWidget(edit_label, 0)

        # 편집 영역 전체 컨테이너
        edit_container = QWidget()
        edit_container.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
            }
        """)

        edit_main_layout = QVBoxLayout()
        edit_main_layout.setSpacing(2)
        edit_main_layout.setContentsMargins(0, 0, 0, 0)

        # 4-1. 자릿수 변경 기능 (박스)
        digit_box = QWidget()
        digit_box.setObjectName("digit_box")
        digit_box.setStyleSheet("""
            QWidget#digit_box {
                background-color: white;
                border: none;
                border-radius: 0px;
            }
        """)

        digit_layout = QHBoxLayout()
        digit_layout.setSpacing(8)
        digit_layout.setContentsMargins(12, 0, 12, 0)

        # "자릿수" 라벨과 라디오 버튼을 하나의 컨테이너로 묶기
        digit_input_container = QWidget()
        digit_input_container.setObjectName("digit_input_container")
        digit_input_container.setStyleSheet("""
            QWidget#digit_input_container {
                border: none;
                background-color: transparent;
            }
        """)

        digit_input_inner_layout = QHBoxLayout()
        digit_input_inner_layout.setSpacing(10)
        digit_input_inner_layout.setContentsMargins(0, 0, 8, 0)

        digit_label = QLabel("자릿수 :")
        digit_label.setMinimumWidth(30)
        digit_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        digit_label.setStyleSheet("border: none; background: transparent;")

        # 자릿수 선택 라디오 버튼
        self.digit_button_group = QButtonGroup()
        self.digit_1_radio = QRadioButton("1자리")
        self.digit_2_radio = QRadioButton("2자리")
        self.digit_3_radio = QRadioButton("3자리")

        # 버튼 그룹에 추가
        self.digit_button_group.addButton(self.digit_1_radio, 1)
        self.digit_button_group.addButton(self.digit_2_radio, 2)
        self.digit_button_group.addButton(self.digit_3_radio, 3)

        # 초기에는 아무것도 선택하지 않음 (exclusive를 False로 설정)
        self.digit_button_group.setExclusive(False)
        self.digit_1_radio.setChecked(False)
        self.digit_2_radio.setChecked(False)
        self.digit_3_radio.setChecked(False)
        self.digit_button_group.setExclusive(True)

        # 라디오 버튼 선택 시 즉시 적용
        self.digit_1_radio.toggled.connect(self.on_digit_changed)
        self.digit_2_radio.toggled.connect(self.on_digit_changed)
        self.digit_3_radio.toggled.connect(self.on_digit_changed)

        # 라디오 버튼 폰트 설정
        self.digit_1_radio.setFont(QFont("맑은 고딕", 10))
        self.digit_2_radio.setFont(QFont("맑은 고딕", 10))
        self.digit_3_radio.setFont(QFont("맑은 고딕", 10))

        # 라디오 버튼 스타일 (테두리 없이 체크만 보이도록)
        radio_style = """
            QRadioButton {
                spacing: 5px;
                padding: 8px 12px;
                color: #212529;
                border: none;
                background: transparent;
                min-width: 60px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border: none;
                background: transparent;
                subcontrol-position: left center;
            }
            QRadioButton::indicator:unchecked {
                image: url(none);
                width: 16px;
                height: 16px;
                border: 2px solid #ced4da;
                border-radius: 8px;
                background: white;
            }
            QRadioButton::indicator:checked {
                image: url(none);
                width: 16px;
                height: 16px;
                border: 2px solid #0078d4;
                border-radius: 8px;
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5, stop:0 #0078d4, stop:0.5 #0078d4, stop:0.51 white, stop:1 white);
            }
        """

        self.digit_1_radio.setStyleSheet(radio_style)
        self.digit_2_radio.setStyleSheet(radio_style)
        self.digit_3_radio.setStyleSheet(radio_style)

        digit_input_inner_layout.addWidget(digit_label)
        digit_input_inner_layout.addWidget(self.digit_1_radio)
        digit_input_inner_layout.addWidget(self.digit_2_radio)
        digit_input_inner_layout.addWidget(self.digit_3_radio)
        digit_input_inner_layout.addStretch()
        digit_input_container.setLayout(digit_input_inner_layout)

        digit_layout.addWidget(digit_input_container, 1)

        digit_box.setLayout(digit_layout)
        edit_main_layout.addWidget(digit_box)

        # 4-2. 제거 기능 (박스)
        remove_box = QWidget()
        remove_box.setObjectName("remove_box")
        remove_box.setStyleSheet("""
            QWidget#remove_box {
                background-color: white;
                border: none;
                border-radius: 0px;
            }
        """)

        remove_layout = QHBoxLayout()
        remove_layout.setSpacing(8)
        remove_layout.setContentsMargins(12, 0, 12, 0)

        # "제거" 라벨과 입력창을 하나의 컨테이너로 묶기
        remove_input_container = QWidget()
        remove_input_container.setObjectName("remove_input_container")
        remove_input_container.setStyleSheet("""
            QWidget#remove_input_container {
                border: none;
                background-color: transparent;
            }
        """)

        remove_input_inner_layout = QHBoxLayout()
        remove_input_inner_layout.setSpacing(0)
        remove_input_inner_layout.setContentsMargins(0, 0, 8, 0)

        remove_label = QLabel("제거 :")
        remove_label.setMinimumWidth(30)
        remove_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        remove_label.setStyleSheet("border: none; background: transparent;")

        self.remove_input = QLineEdit()
        self.remove_input.setPlaceholderText("제거할 텍스트 입력")
        self.remove_input.setMinimumHeight(35)
        self.remove_input.setFont(QFont("맑은 고딕", 10))
        self.remove_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: #ffffff;
                color: #212529;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
            }
            QLineEdit::placeholder {
                color: #495057;
            }
        """)

        remove_input_inner_layout.addWidget(remove_label)
        remove_input_inner_layout.addWidget(self.remove_input, 1)
        remove_input_container.setLayout(remove_input_inner_layout)

        # 전체/앞/뒤 선택
        self.remove_all_radio = QRadioButton("전체")
        self.remove_front_radio = QRadioButton("앞")
        self.remove_back_radio = QRadioButton("뒤")
        self.remove_all_radio.setChecked(True)  # 디폴트: 전체 제거
        self.remove_all_radio.setFont(QFont("맑은 고딕", 10))
        self.remove_front_radio.setFont(QFont("맑은 고딕", 10))
        self.remove_back_radio.setFont(QFont("맑은 고딕", 10))
        self.remove_all_radio.setStyleSheet(radio_style)
        self.remove_front_radio.setStyleSheet(radio_style)
        self.remove_back_radio.setStyleSheet(radio_style)

        # 전체/앞/뒤 버튼을 하나의 위젯으로 묶어서 간격 조정
        remove_position_widget = QWidget()
        remove_position_widget.setStyleSheet("""
            QWidget {
                border: none;
                background: transparent;
            }
        """)
        remove_position_layout = QHBoxLayout()
        remove_position_layout.setSpacing(2)
        remove_position_layout.setContentsMargins(0, 0, 0, 0)
        remove_position_layout.addWidget(self.remove_all_radio)
        remove_position_layout.addWidget(self.remove_front_radio)
        remove_position_layout.addWidget(self.remove_back_radio)
        remove_position_widget.setLayout(remove_position_layout)

        self.remove_button = QPushButton("✔️ 적용")
        self.remove_button.setMinimumHeight(35)
        self.remove_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.remove_button.clicked.connect(self.remove_text_action)

        self.remove_undo_button = QPushButton("❌ 취소")
        self.remove_undo_button.setMinimumHeight(35)
        self.remove_undo_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #adb5bd;
            }
        """)
        self.remove_undo_button.setEnabled(False)
        self.remove_undo_button.clicked.connect(self.undo_remove_action)

        remove_layout.addWidget(remove_input_container, 1)
        remove_layout.addWidget(remove_position_widget)
        remove_layout.addWidget(self.remove_button)
        remove_layout.addWidget(self.remove_undo_button)

        remove_box.setLayout(remove_layout)
        edit_main_layout.addWidget(remove_box)

        # 4-3. 추가 기능 (박스)
        add_box = QWidget()
        add_box.setObjectName("add_box")
        add_box.setStyleSheet("""
            QWidget#add_box {
                background-color: white;
                border: none;
                border-radius: 0px;
            }
        """)

        add_layout = QHBoxLayout()
        add_layout.setSpacing(8)
        add_layout.setContentsMargins(12, 0, 12, 0)

        # "추가" 라벨과 입력창을 하나의 컨테이너로 묶기
        add_input_container = QWidget()
        add_input_container.setObjectName("add_input_container")
        add_input_container.setStyleSheet("""
            QWidget#add_input_container {
                border: none;
                background-color: transparent;
            }
        """)

        add_input_inner_layout = QHBoxLayout()
        add_input_inner_layout.setSpacing(0)
        add_input_inner_layout.setContentsMargins(0, 0, 8, 0)

        add_label = QLabel("추가 :")
        add_label.setMinimumWidth(30)
        add_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        add_label.setStyleSheet("border: none; background: transparent;")

        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText("추가할 텍스트 입력")
        self.add_input.setMinimumHeight(35)
        self.add_input.setFont(QFont("맑은 고딕", 10))
        self.add_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: #ffffff;
                color: #212529;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
            }
            QLineEdit::placeholder {
                color: #495057;
            }
        """)

        add_input_inner_layout.addWidget(add_label)
        add_input_inner_layout.addWidget(self.add_input, 1)
        add_input_container.setLayout(add_input_inner_layout)

        # 앞/뒤 선택
        self.add_front_radio = QRadioButton("앞")
        self.add_back_radio = QRadioButton("뒤")
        self.add_front_radio.setChecked(True)
        self.add_front_radio.setFont(QFont("맑은 고딕", 10))
        self.add_back_radio.setFont(QFont("맑은 고딕", 10))
        self.add_front_radio.setStyleSheet(radio_style)
        self.add_back_radio.setStyleSheet(radio_style)

        self.add_button = QPushButton("✔️ 적용")
        self.add_button.setMinimumHeight(35)
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.add_button.clicked.connect(self.add_text_action)

        self.add_undo_button = QPushButton("❌ 취소")
        self.add_undo_button.setMinimumHeight(35)
        self.add_undo_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #adb5bd;
            }
        """)
        self.add_undo_button.setEnabled(False)
        self.add_undo_button.clicked.connect(self.undo_add_action)

        # 앞/뒤 버튼을 하나의 위젯으로 묶어서 간격 조정
        position_widget = QWidget()
        position_widget.setStyleSheet("""
            QWidget {
                border: none;
                background: transparent;
            }
        """)
        position_layout = QHBoxLayout()
        position_layout.setSpacing(2)
        position_layout.setContentsMargins(0, 0, 0, 0)
        position_layout.addWidget(self.add_front_radio)
        position_layout.addWidget(self.add_back_radio)
        position_widget.setLayout(position_layout)

        add_layout.addWidget(add_input_container, 1)
        add_layout.addWidget(position_widget)
        add_layout.addWidget(self.add_button)
        add_layout.addWidget(self.add_undo_button)

        add_box.setLayout(add_layout)
        edit_main_layout.addWidget(add_box)

        # 4-4. 패턴 편집 기능 (박스)
        pattern_edit_box = QWidget()
        pattern_edit_box.setObjectName("pattern_edit_box")
        pattern_edit_box.setStyleSheet("""
            QWidget#pattern_edit_box {
                background-color: white;
                border: none;
                border-radius: 0px;
            }
        """)

        pattern_edit_layout = QHBoxLayout()
        pattern_edit_layout.setSpacing(8)
        pattern_edit_layout.setContentsMargins(12, 0, 12, 0)

        # "패턴" 라벨과 입력창을 하나의 컨테이너로 묶기
        pattern_edit_input_container = QWidget()
        pattern_edit_input_container.setObjectName("pattern_edit_input_container")
        pattern_edit_input_container.setStyleSheet("""
            QWidget#pattern_edit_input_container {
                border: none;
                background-color: transparent;
            }
        """)

        pattern_edit_input_inner_layout = QHBoxLayout()
        pattern_edit_input_inner_layout.setSpacing(0)
        pattern_edit_input_inner_layout.setContentsMargins(0, 0, 8, 0)

        pattern_edit_label = QLabel("패턴 :")
        pattern_edit_label.setMinimumWidth(30)
        pattern_edit_label.setFont(QFont("맑은 고딕", 10, QFont.Bold))
        pattern_edit_label.setStyleSheet("border: none; background: transparent;")

        self.pattern_edit_input = QLineEdit()
        self.pattern_edit_input.setPlaceholderText("패턴 선택 후 편집")
        self.pattern_edit_input.setMinimumHeight(35)
        self.pattern_edit_input.setFont(QFont("맑은 고딕", 10))
        self.pattern_edit_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: #ffffff;
                color: #212529;
            }
            QLineEdit:focus {
                border: 2px solid #0078d4;
            }
            QLineEdit::placeholder {
                color: #495057;
            }
        """)

        pattern_edit_input_inner_layout.addWidget(pattern_edit_label)
        pattern_edit_input_inner_layout.addWidget(self.pattern_edit_input, 1)
        pattern_edit_input_container.setLayout(pattern_edit_input_inner_layout)

        self.pattern_edit_button = QPushButton("✔️ 적용")
        self.pattern_edit_button.setMinimumHeight(35)
        self.pattern_edit_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.pattern_edit_button.clicked.connect(self.apply_pattern_edit_action)

        self.pattern_edit_undo_button = QPushButton("❌ 취소")
        self.pattern_edit_undo_button.setMinimumHeight(35)
        self.pattern_edit_undo_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #adb5bd;
            }
        """)
        self.pattern_edit_undo_button.setEnabled(False)
        self.pattern_edit_undo_button.clicked.connect(self.undo_pattern_edit_action)

        pattern_edit_layout.addWidget(pattern_edit_input_container, 1)
        pattern_edit_layout.addWidget(self.pattern_edit_button)
        pattern_edit_layout.addWidget(self.pattern_edit_undo_button)

        pattern_edit_box.setLayout(pattern_edit_layout)
        edit_main_layout.addWidget(pattern_edit_box)

        # 편집 컨테이너 완성
        edit_container.setLayout(edit_main_layout)
        main_layout.addWidget(edit_container, 0)

        # 5. 하단 실행 버튼 (고정 크기)
        button_container = QWidget()
        button_container.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
            }
        """)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.execute_button = QPushButton("파일명 변경 실행")
        self.execute_button.setMinimumHeight(50)
        self.execute_button.setFont(QFont("맑은 고딕", 11, QFont.Bold))
        self.execute_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px 24px;
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
        button_container.setLayout(button_layout)
        main_layout.addWidget(button_container, 0)

    def select_folder(self):
        """폴더 선택"""
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")

        if folder:
            self.current_folder = folder
            self.folder_label.setText(folder)
            self.load_files(folder)

    def on_folder_dropped(self, folder_path: str):
        """
        드래그 앤 드롭으로 폴더가 선택되었을 때 호출

        Args:
            folder_path: 드롭된 폴더 경로
        """
        self.current_folder = folder_path
        self.folder_label.setText(folder_path)
        self.load_files(folder_path)

    def on_files_dropped(self, file_paths: List[str]):
        """
        드래그 앤 드롭으로 파일 목록이 선택되었을 때 호출

        Args:
            file_paths: 드롭된 파일 경로 리스트
        """
        if not file_paths:
            return

        # 폴더 경로 초기화 (파일 목록 모드)
        self.current_folder = ""
        self.folder_label.setText(f"{len(file_paths)}개 파일 선택됨")

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
            self.cover_image_widget.clear()
            return

        # 패턴 라디오 버튼 생성
        self.create_pattern_buttons()

        # 자릿수 선택 초기화
        self.reset_digit_radio_buttons()

        # 자릿수 선택 제한 적용
        self.update_digit_radio_constraints()

        # 미리보기 업데이트
        self.refresh_preview()

        # 테이블 선택 초기화 (첫 번째 행 선택)
        if self.preview_table.rowCount() > 0:
            self.preview_table.selectRow(0)

        # 표지 이미지 로드
        self.load_cover_image(file_paths)

        # 초기화 버튼 활성화
        self.reset_button.setEnabled(True)

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

        # 자릿수 선택 초기화 (폴더 로드 시 선택 해제)
        self.reset_digit_radio_buttons()

        # 자릿수 선택 제한 적용
        self.update_digit_radio_constraints()

        # 미리보기 업데이트
        self.refresh_preview()

        # 테이블 선택 초기화 (첫 번째 행 선택)
        if self.preview_table.rowCount() > 0:
            self.preview_table.selectRow(0)

        # 표지 이미지 로드
        self.load_cover_image(file_paths)

        # 초기화 버튼 활성화
        self.reset_button.setEnabled(True)

    def reset_digit_radio_buttons(self):
        """자릿수 라디오 버튼 선택 초기화"""
        # exclusive를 False로 하여 모두 해제 가능하게 함
        self.digit_button_group.setExclusive(False)
        self.digit_1_radio.setChecked(False)
        self.digit_2_radio.setChecked(False)
        self.digit_3_radio.setChecked(False)
        self.digit_button_group.setExclusive(True)

    def update_digit_radio_constraints(self):
        """파일 개수와 최대 권수에 따라 자릿수 라디오 버튼 활성화/비활성화"""
        if not self.file_infos:
            return

        # 최대 권수 찾기
        max_volume = 0
        for file_info in self.file_infos:
            if file_info.pattern and file_info.pattern.number:
                if file_info.pattern.number.isdigit():
                    volume = int(file_info.pattern.number)
                    if volume > max_volume:
                        max_volume = volume

        # 최대 권수에 따라 라디오 버튼 활성화/비활성화
        if max_volume >= 100:
            # 100권 이상: 3자리만 가능
            self.digit_1_radio.setEnabled(False)
            self.digit_2_radio.setEnabled(False)
            self.digit_3_radio.setEnabled(True)
        elif max_volume >= 10:
            # 10~99권: 2자리, 3자리 가능
            self.digit_1_radio.setEnabled(False)
            self.digit_2_radio.setEnabled(True)
            self.digit_3_radio.setEnabled(True)
        else:
            # 9권 이하: 모든 자릿수 가능
            self.digit_1_radio.setEnabled(True)
            self.digit_2_radio.setEnabled(True)
            self.digit_3_radio.setEnabled(True)

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

        # 새 버튼 생성
        for i, pattern in enumerate(self.representative_patterns):
            # 패턴의 원래 padding_width 사용 (자동 조정 안 함)
            radio = QRadioButton(str(pattern))
            radio.setFont(QFont("맑은 고딕", 10))

            # 라디오 버튼 스타일 개선
            radio.setStyleSheet("""
                QRadioButton {
                    padding: 8px;
                    spacing: 8px;
                    background-color: white;
                    border-radius: 6px;
                }
                QRadioButton:hover {
                    background-color: #e9ecef;
                }
                QRadioButton:checked {
                    background-color: #d3e5f7;
                    font-weight: bold;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                }
            """)

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

        # 패턴 변경 시 자릿수 선택 초기화
        self.reset_digit_radio_buttons()

        # 자릿수 선택 제한 업데이트
        self.update_digit_radio_constraints()

        # 미리보기 업데이트
        self.refresh_preview()

        # 패턴 편집 입력창에 선택한 패턴 표시
        pattern_string = self.pattern_to_string(self.selected_pattern)
        self.pattern_edit_input.setText(pattern_string)

    def pattern_to_string(self, pattern: FilePattern) -> str:
        """
        FilePattern 객체를 편집 가능한 문자열로 변환
        사용자에게는 제목(prefix + title)만 표시
        공백도 패턴의 일부로 유지

        Args:
            pattern: FilePattern 객체

        Returns:
            제목 문자열 (예: "고래의 아이들은 모래 위에서 노래한다 " - 끝 공백 포함)
        """
        result = ""

        # prefix 추가
        if pattern.prefix:
            result += pattern.prefix

        # title 추가
        if pattern.title:
            result += pattern.title

        # 공백을 포함하여 그대로 반환
        return result

    def apply_pattern_edit_action(self):
        """
        패턴 편집 적용
        사용자 입력(제목)에 자동으로 권수와 확장자를 추가하여 적용
        앞뒤 공백도 패턴의 일부로 유지
        """
        user_input = self.pattern_edit_input.text()

        # 빈 문자열 체크 (공백만 있는 경우도 허용)
        if len(user_input) == 0:
            QMessageBox.warning(self, "경고", "패턴을 입력하세요.")
            return

        # 선택된 패턴이 없으면 경고
        if not self.selected_pattern:
            QMessageBox.warning(self, "경고", "먼저 패턴을 선택해주세요.")
            return

        # 사용자 입력을 기반으로 완전한 패턴 템플릿 생성
        # 1. 사용자가 입력한 제목 사용
        base = user_input

        # 2. 권수 placeholder 추가 (선택된 패턴의 padding_width 사용)
        padding_width = self.selected_pattern.padding_width
        if padding_width == 2:
            number_placeholder = "{number:02d}"
        elif padding_width == 3:
            number_placeholder = "{number:03d}"
        else:
            number_placeholder = "{number}"

        # 3. suffix 추가 (원본 패턴의 suffix 사용)
        suffix = self.selected_pattern.suffix if self.selected_pattern.suffix else ""

        # 4. 확장자 추가 (원본 패턴의 extension 사용)
        extension = self.selected_pattern.extension if self.selected_pattern.extension else ""

        # 완전한 패턴 템플릿 생성
        pattern_template = base + number_placeholder + suffix + extension

        # 이전 상태 저장 (파일 정보와 입력창 텍스트)
        self.previous_file_infos_pattern = copy.deepcopy(self.file_infos)
        self.previous_pattern_text = self.pattern_to_string(self.selected_pattern)

        # 패턴 편집 적용
        self.file_infos = apply_custom_pattern(self.file_infos, pattern_template)

        # 패턴 편집 취소 버튼만 활성화
        self.pattern_edit_undo_button.setEnabled(True)

        # 미리보기 업데이트
        self.refresh_preview()

    def undo_pattern_edit_action(self):
        """패턴 편집 작업 취소"""
        if self.previous_file_infos_pattern is None:
            QMessageBox.warning(self, "경고", "취소할 작업이 없습니다.")
            return

        # 이전 상태로 복원 (파일 정보와 입력창 텍스트)
        self.file_infos = self.previous_file_infos_pattern
        self.previous_file_infos_pattern = None

        # 패턴 편집 입력창도 이전 텍스트로 복원
        if self.previous_pattern_text is not None:
            self.pattern_edit_input.setText(self.previous_pattern_text)
            self.previous_pattern_text = None

        # 패턴 편집 취소 버튼 비활성화
        self.pattern_edit_undo_button.setEnabled(False)

        # 미리보기 업데이트
        self.refresh_preview()

        QMessageBox.information(self, "완료", "이전 상태로 복원되었습니다.")

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

    def undo_remove_action(self):
        """제거 작업 취소"""
        if self.previous_file_infos_remove is None:
            QMessageBox.warning(self, "경고", "취소할 작업이 없습니다.")
            return

        # 이전 상태로 복원
        self.file_infos = self.previous_file_infos_remove
        self.previous_file_infos_remove = None

        # 제거 취소 버튼 비활성화
        self.remove_undo_button.setEnabled(False)

        # 미리보기 업데이트
        self.refresh_preview()

        QMessageBox.information(self, "완료", "이전 상태로 복원되었습니다.")

    def undo_add_action(self):
        """추가 작업 취소"""
        if self.previous_file_infos_add is None:
            QMessageBox.warning(self, "경고", "취소할 작업이 없습니다.")
            return

        # 이전 상태로 복원
        self.file_infos = self.previous_file_infos_add
        self.previous_file_infos_add = None

        # 추가 취소 버튼 비활성화
        self.add_undo_button.setEnabled(False)

        # 미리보기 업데이트
        self.refresh_preview()

        QMessageBox.information(self, "완료", "이전 상태로 복원되었습니다.")

    def on_digit_changed(self, checked):
        """라디오 버튼 선택 시 즉시 적용"""
        if not checked:  # 버튼이 해제될 때는 무시
            return

        if not self.file_infos:
            return

        # 선택한 자릿수 확인
        if self.digit_1_radio.isChecked():
            padding_width = 1
        elif self.digit_2_radio.isChecked():
            padding_width = 2
        else:  # digit_3_radio
            padding_width = 3

        # 자릿수 변경 즉시 적용
        from file_renamer import change_padding_width
        self.file_infos = change_padding_width(self.file_infos, padding_width)

        # 미리보기 업데이트
        self.refresh_preview()

    def remove_text_action(self):
        """텍스트 제거"""
        text = self.remove_input.text()

        if not text:
            QMessageBox.warning(self, "경고", "제거할 텍스트를 입력하세요.")
            return

        # 이전 상태 저장
        self.previous_file_infos_remove = copy.deepcopy(self.file_infos)

        # 위치 선택에 따라 position 결정
        if self.remove_all_radio.isChecked():
            position = "all"
        elif self.remove_front_radio.isChecked():
            position = "front"
        else:  # self.remove_back_radio.isChecked()
            position = "back"

        # 텍스트 제거 적용
        self.file_infos = remove_text(self.file_infos, text, position)

        # 제거 취소 버튼만 활성화
        self.remove_undo_button.setEnabled(True)

        # 미리보기 업데이트
        self.refresh_preview()

    def add_text_action(self):
        """텍스트 추가"""
        text = self.add_input.text()

        if not text:
            QMessageBox.warning(self, "경고", "추가할 텍스트를 입력하세요.")
            return

        # 이전 상태 저장
        self.previous_file_infos_add = copy.deepcopy(self.file_infos)

        # 텍스트 추가 적용
        position = "front" if self.add_front_radio.isChecked() else "back"
        self.file_infos = add_text(self.file_infos, text, position)

        # 추가 취소 버튼만 활성화
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

    def on_preview_option_changed(self, state):
        """표지 미리보기 옵션 변경 시 호출"""
        # 옵션이 꺼지면 첫 번째 파일의 표지로 되돌림
        if state == 0:  # 체크 해제
            if self.file_infos:
                file_paths = [info.original_path for info in self.file_infos]
                self.load_cover_image(file_paths)

    def on_table_item_clicked(self, item):
        """테이블 아이템 클릭 시 호출 (마우스)"""
        if item is None:
            return
        row = item.row()
        self.update_cover_for_row(row)

    def on_table_current_item_changed(self, current, _previous):
        """테이블 현재 아이템 변경 시 호출 (키보드 방향키 포함)"""
        if current is None:
            return
        row = current.row()
        self.update_cover_for_row(row)

    def update_cover_for_row(self, row: int):
        """
        지정된 행의 표지 이미지를 업데이트

        Args:
            row: 테이블 행 번호
        """
        # 옵션이 활성화되어 있지 않으면 무시
        if not self.preview_all_covers_checkbox.isChecked():
            return

        # 행 번호 유효성 검사
        if row < 0 or row >= len(self.file_infos):
            return

        # 파일 정보 가져오기
        file_info = self.file_infos[row]
        file_path = file_info.original_path

        # ZIP 파일이 아니면 무시
        if not file_path.lower().endswith('.zip'):
            return

        # 이미지 로드 (캐시 활용)
        self.load_and_display_cover(file_path)

    def load_and_display_cover(self, file_path: str):
        """
        파일의 표지 이미지를 로드하여 표시 (캐싱 사용)

        Args:
            file_path: ZIP 파일 경로
        """
        # 캐시 확인
        if file_path in self.image_cache:
            # 캐시에 있으면 즉시 표시
            self.cover_image_widget.set_pil_image(self.image_cache[file_path])
            return

        # 캐시에 없으면 로드
        try:
            # 이미지 추출
            img = extract_cover_from_zip(file_path, max_size=(500, 700))

            # 캐시에 저장
            self.image_cache[file_path] = img

            # 표시
            self.cover_image_widget.set_pil_image(img)

        except Exception as e:
            print(f"이미지 로드 실패: {file_path}, {e}")
            # 실패 시 빈 화면
            self.cover_image_widget.clear()

    def reset_preview(self):
        """미리보기 목록 초기화"""
        # 확인 메시지
        if self.file_infos:
            reply = QMessageBox.question(
                self,
                "확인",
                "미리보기 목록을 초기화하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.No:
                return

        # 모든 데이터 초기화
        self.file_infos = []
        self.representative_patterns = []
        self.selected_pattern = None
        self.current_folder = ""
        self.previous_file_infos_remove = None
        self.previous_file_infos_add = None
        self.previous_file_infos_pattern = None
        self.previous_pattern_text = None

        # UI 초기화
        self.folder_label.setText("폴더를 선택하거나 드래그 앤 드롭하세요")

        # 패턴 버튼 제거
        for i in reversed(range(self.pattern_layout.count())):
            widget = self.pattern_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # 테이블 초기화
        self.preview_table.setRowCount(0)

        # 표지 이미지 제거
        self.cover_image_widget.clear()

        # 이미지 캐시 초기화
        self.image_cache.clear()

        # 자릿수 선택 초기화
        self.reset_digit_radio_buttons()

        # 입력창 초기화
        self.remove_input.clear()
        self.add_input.clear()
        self.pattern_edit_input.clear()

        # 취소 버튼 비활성화
        self.remove_undo_button.setEnabled(False)
        self.add_undo_button.setEnabled(False)
        self.pattern_edit_undo_button.setEnabled(False)

        # 초기화 버튼 비활성화
        self.reset_button.setEnabled(False)
