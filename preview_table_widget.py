"""
드래그 앤 드롭을 지원하는 미리보기 테이블 위젯
"""
from PyQt5.QtWidgets import QTableWidget
from PyQt5.QtCore import Qt, pyqtSignal
import os


class PreviewTableWidget(QTableWidget):
    """
    드래그 앤 드롭으로 폴더 선택을 지원하는 테이블 위젯
    """

    # 폴더가 드롭되었을 때 발생하는 시그널
    folder_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # 드래그 앤 드롭 활성화
        self.setAcceptDrops(True)

        # 드래그 중 상태 플래그
        self.is_dragging = False

        # 기본 스타일 저장
        self.default_style = """
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
        """

        # 드래그 중 스타일
        self.dragging_style = """
            QTableWidget {
                gridline-color: #d0d0d0;
                selection-background-color: #0078d4;
                selection-color: white;
                alternate-background-color: #f5f5f5;
                border: 3px dashed #0078d4;
                background-color: #e8f4ff;
            }
            QHeaderView::section {
                background-color: #e9e9e9;
                padding: 8px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
            }
        """

        self.setStyleSheet(self.default_style)

    def dragEnterEvent(self, event):
        """드래그가 위젯 영역에 들어왔을 때"""
        # MIME 데이터 확인
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()

            # 첫 번째 항목이 폴더인지 확인
            if urls and len(urls) > 0:
                path = urls[0].toLocalFile()

                if os.path.isdir(path):
                    # 폴더면 드롭 허용
                    event.acceptProposedAction()
                    self.is_dragging = True
                    self.setStyleSheet(self.dragging_style)
                    return

        # 폴더가 아니면 거부
        event.ignore()

    def dragMoveEvent(self, event):
        """드래그가 위젯 위에서 이동할 때"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """드래그가 위젯 영역을 벗어났을 때"""
        self.is_dragging = False
        self.setStyleSheet(self.default_style)

    def dropEvent(self, event):
        """드롭이 발생했을 때"""
        self.is_dragging = False
        self.setStyleSheet(self.default_style)

        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()

            if urls and len(urls) > 0:
                path = urls[0].toLocalFile()

                # 폴더인 경우에만 시그널 발생
                if os.path.isdir(path):
                    self.folder_dropped.emit(path)
                    event.acceptProposedAction()
                    return

        event.ignore()
