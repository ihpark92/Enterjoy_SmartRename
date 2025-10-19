# 엔쪼 스마트리네임 (NZZO Smart Rename)

파일명의 패턴을 자동으로 분석하여 일괄 변경할 수 있는 스마트 파일명 변경 프로그램입니다.

## 주요 기능

1. **자동 패턴 인식**: 폴더 내 파일들의 이름 패턴을 자동으로 분석하고 분류
2. **패턴 통일**: 선택한 패턴으로 모든 파일명을 통일
3. **텍스트 제거**: 특정 문자열을 일괄 제거 (예: `[공금]`, `[절공]` 등)
4. **텍스트 추가**: 파일명 앞/뒤에 텍스트 추가
5. **미리보기**: 실제 변경 전 미리보기 제공

## 사용 방법

1. 프로그램 실행
2. "폴더 선택" 버튼 클릭하여 대상 폴더 선택
3. 검출된 패턴 중 원하는 패턴 선택
4. 필요시 추가 편집 기능 사용 (제거/추가)
5. 미리보기 확인 후 "파일명 변경 실행" 클릭

## 설치 방법 (개발자용)

### 필수 요구사항
- Python 3.8 이상

### 의존성 설치
```bash
pip install -r requirements.txt
```

### 실행
```bash
python app.py
```

## 빌드 방법 (단독 실행 파일 생성)

```bash
# Windows
build.bat

# 또는 직접 실행
pyinstaller --onefile --noconsole --name=Enterjoy_SmartRename app.py
```

빌드 완료 후 `dist/Enterjoy_SmartRename.exe` 파일이 생성됩니다.

## 파일 구조

```
FileName_Changer/
├── app.py                    # 메인 진입점
├── main_window.py            # GUI 구현
├── pattern_analyzer.py       # 패턴 분석 엔진
├── file_renamer.py           # 파일명 변경 로직
├── file_system.py            # 파일 시스템 유틸리티
├── models.py                 # 데이터 모델
├── requirements.txt          # 의존성
├── build.bat                 # 빌드 스크립트
└── README.md                 # 이 파일
```

## 예제

### 변경 전
```
사카모토 데이즈 01권.zip
사카모토 데이즈 02권.zip
[공금] 사카모토 데이즈 06권.zip
[공금] 사카모토 데이즈 07권.zip
사카모토 데이즈 09권 [절공].zip
사카모토 데이즈 11.zip
```

### "사카모토 데이즈 01권.zip" 패턴 선택 후
```
사카모토 데이즈 01권.zip
사카모토 데이즈 02권.zip
사카모토 데이즈 06권.zip
사카모토 데이즈 07권.zip
사카모토 데이즈 09권.zip
사카모토 데이즈 11권.zip
```

## 라이선스

MIT License

## 주의사항

- 파일명 변경은 되돌릴 수 없으므로, 미리보기를 충분히 확인하세요
- 중요한 파일은 백업 후 사용하세요
- Windows 파일명 규칙을 위반하는 문자는 사용할 수 없습니다
