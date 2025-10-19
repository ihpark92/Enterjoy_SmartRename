@echo off
echo ====================================
echo 엔쪼 스마트리네임 빌드 시작
echo ====================================
echo.

REM 의존성 설치
echo 의존성 설치 중...
pip install -r requirements.txt

echo.
echo ====================================
echo PyInstaller 빌드 중...
echo ====================================
echo.

REM PyInstaller로 단독 실행 파일 생성
pyinstaller --onefile --noconsole --name=Enterjoy_SmartRename app.py

echo.
echo ====================================
echo 빌드 완료!
echo ====================================
echo.
echo 실행 파일 위치: dist\Enterjoy_SmartRename.exe
echo.
pause
