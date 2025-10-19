"""
반응형 표지 이미지 위젯
"""
from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt
from PIL import Image
import io


class CoverImageWidget(QLabel):
    """
    반응형 표지 이미지 표시 위젯
    윈도우 크기 변경 시 자동으로 이미지 리스케일
    """

    def __init__(self):
        super().__init__()

        # 원본 QPixmap 저장 (고품질 리스케일을 위해)
        self.original_pixmap = None

        # 초기 설정
        self.setMinimumSize(150, 200)  # 최소 크기
        self.setMaximumWidth(400)  # 최대 너비 (너무 커지지 않게)
        self.setAlignment(Qt.AlignCenter)

        # 스타일 설정
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #d0d0d0;
                background-color: #f9f9f9;
                border-radius: 5px;
            }
        """)

        # 초기 빈 상태
        self.clear()

    def set_pil_image(self, pil_img):
        """
        PIL Image를 표시

        Args:
            pil_img: PIL.Image 객체 또는 None
        """
        if pil_img is None:
            self.clear()
            return

        # PIL Image → QPixmap 변환
        buffer = io.BytesIO()
        pil_img.save(buffer, format='PNG')
        buffer.seek(0)

        qimg = QImage.fromData(buffer.read())
        self.original_pixmap = QPixmap.fromImage(qimg)

        # 현재 크기에 맞게 표시
        self.update_display()

    def update_display(self):
        """현재 위젯 크기에 맞게 이미지 스케일링"""
        if self.original_pixmap is None or self.original_pixmap.isNull():
            return

        # 위젯 크기에 맞게 스케일 (비율 유지)
        scaled_pixmap = self.original_pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """윈도우 크기 변경 시 자동 호출"""
        super().resizeEvent(event)
        self.update_display()

    def clear(self):
        """이미지 제거 (빈 공간)"""
        super().clear()
        self.original_pixmap = None
        # 텍스트 표시하지 않음 (요구사항: 빈 공간)
