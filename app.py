"""
파일명 일괄 변경 프로그램
메인 애플리케이션 진입점
Version: 0.9
"""
import sys
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow

__version__ = "0.9"


def main():
    """메인 함수"""
    app = QApplication(sys.argv)

    # 메인 윈도우 생성 및 표시
    window = MainWindow()
    window.show()

    # 이벤트 루프 시작
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
