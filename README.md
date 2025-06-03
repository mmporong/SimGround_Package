# Unity 프로젝트 자동화 도구 (dannect.unity.toolkit.py)

Unity 프로젝트의 UTF-8 변환, 패키지 관리, Git 자동화를 위한 통합 도구입니다.

## 🚀 주요 기능

### 1. C# 파일 UTF-8 변환
- 프로젝트 내 모든 C# 파일을 UTF-8 인코딩으로 자동 변환
- 이미 UTF-8인 파일은 건너뛰어 효율성 확보
- 인코딩 감지 및 안전한 변환 처리

### 2. Unity 패키지 자동 관리
- Git 패키지를 manifest.json에 자동 추가
- 중복 패키지 설치 방지
- 패키지 버전 관리 및 업데이트

### 3. Git 자동화
- 변경사항 자동 감지 및 커밋
- 스마트 브랜치 전략 적용
- 자동 푸시 및 원격 저장소 관리

## 📋 시스템 요구사항

- Python 3.6 이상
- Git 설치 및 PATH 설정
- 필요한 Python 패키지:
  ```bash
  pip install chardet
  ```

## 🔧 설정

### 프로젝트 디렉토리 설정
`dannect.unity.toolkit.py` 파일의 상단에서 프로젝트 경로를 설정합니다:

```python
project_dirs = [
    r"E:\3.1.2.2_ClassifyAnimals",
    r"E:\3.1.2.3_AroundAnimals",
    r"E:\3.1.2.5_UnderWaterAnimals",
    # 새 프로젝트 추가 시 여기에 경로 추가
]
```

### Git 패키지 설정
추가할 Git 패키지를 설정합니다:

```python
git_packages = {
    "com.boxqkrtm.ide.cursor": "https://github.com/boxqkrtm/com.unity.ide.cursor.git",
    "com.dannect.toolkit": "https://github.com/Dannect/SimGround_Package.git"
    # 필요한 패키지 추가
}
```

### Git 리포지토리 설정
기본 GitHub 조직 URL을 설정합니다:

```python
GIT_BASE_URL = "https://github.com/Dannect/"
```

## 💻 사용법

### 기본 실행
모든 작업(UTF-8 변환, 패키지 추가, Git 커밋/푸시)을 순차적으로 실행합니다:

```bash
python dannect.unity.toolkit.py
```

### 옵션별 실행

#### Git 작업만 실행
UTF-8 변환과 패키지 추가를 건너뛰고 Git 작업만 수행합니다:

```bash
python dannect.unity.toolkit.py --git-only
```

#### Git 작업 건너뛰기
UTF-8 변환과 패키지 추가만 수행하고 Git 작업은 건너뜁니다:

```bash
python dannect.unity.toolkit.py --skip-git
```

#### 도움말 보기
사용법과 옵션을 확인합니다:

```bash
python dannect.unity.toolkit.py --help
```

## 🌿 Git 브랜치 전략

도구는 다음과 같은 스마트 브랜치 전략을 사용합니다:

### 1. 계층구조 최하위 브랜치 우선
- 브랜치 계층구조에서 가장 깊은(아래) 브랜치를 우선 사용
- 커밋 수가 많은 브랜치를 우선 선택
- 커밋 수가 같으면 최근에 작업된 브랜치 선택
- `main` 브랜치는 제외

### 2. dev 브랜치 보조 사용
- 다른 브랜치가 없으면 `dev` 브랜치 사용

### 3. dev 브랜치 자동 생성
- `dev` 브랜치도 없으면 `dev` 브랜치를 새로 생성

### 브랜치 선택 예시
```
브랜치 분석:
  main: 10개 커밋
  feature-base: 15개 커밋
  feature-ui: 20개 커밋 (feature-base에서 파생)
  feature-ui-detail: 25개 커밋 (feature-ui에서 파생)
→ feature-ui-detail 브랜치 선택 (가장 깊은 계층)

브랜치 목록: main, dev
→ dev 브랜치 선택

브랜치 목록: main
→ dev 브랜치 새로 생성
```

## 🌐 리포지토리 URL 자동 생성

프로젝트 폴더명을 기반으로 GitHub 리포지토리 URL을 자동 생성합니다:

| 프로젝트 경로 | 생성되는 리포지토리 URL |
|---------------|------------------------|
| `E:\3.1.2.2_ClassifyAnimals` | `https://github.com/Dannect/3.1.2.2_ClassifyAnimals` |
| `E:\3.1.2.3_AroundAnimals` | `https://github.com/Dannect/3.1.2.3_AroundAnimals` |
| `E:\3.1.2.5_UnderWaterAnimals` | `https://github.com/Dannect/3.1.2.5_UnderWaterAnimals` |

## 📁 프로젝트 구조

```
SimGround_Package/
├── Tools/
│   ├── dannect.unity.toolkit.py    # 메인 스크립트
│   └── README.md                   # 이 파일
└── ...
```

## 🔍 작업 흐름

### 1. UTF-8 변환 단계
```
프로젝트 폴더 스캔
    ↓
Assets 폴더 내 .cs 파일 검색
    ↓
인코딩 감지 및 UTF-8 변환
    ↓
변환 결과 출력
```

### 2. 패키지 추가 단계
```
manifest.json 파일 확인
    ↓
기존 패키지와 비교
    ↓
새 패키지 추가/업데이트
    ↓
manifest.json 저장
```

### 3. Git 자동화 단계
```
Git 리포지토리 확인/초기화
    ↓
변경사항 감지
    ↓
대상 브랜치 결정
    ↓
브랜치 체크아웃/생성
    ↓
스테이징 → 커밋 → 푸시
```

## 🛡️ 안전성 기능

### 에러 처리
- 각 Git 명령어의 성공/실패 체크
- 파일 인코딩 변환 시 예외 처리
- 존재하지 않는 폴더 건너뛰기

### 중복 작업 방지
- 이미 UTF-8인 파일 변환 건너뛰기
- 기존 패키지 중복 설치 방지
- 변경사항이 없는 경우 커밋 건너뛰기

### 자동 초기화
- Git 리포지토리 자동 초기화
- 원격 저장소 자동 설정
- 브랜치 자동 생성

## 📝 로그 출력 예시

```
=== Unity 프로젝트 자동화 도구 시작 ===

1. C# 파일 UTF-8 변환 작업 시작...

--- 3.1.2.2_ClassifyAnimals UTF-8 변환 ---
  AnimalController.cs 변환 완료
  GameManager.cs 이미 UTF-8, 변환 생략

2. Unity 패키지 추가 작업 시작...

--- 3.1.2.2_ClassifyAnimals 패키지 추가 ---
E:\3.1.2.2_ClassifyAnimals\Packages\manifest.json에 패키지들 추가/수정 완료!

3. Git 커밋 및 푸시 작업 시작...

=== 3.1.2.2_ClassifyAnimals Git 작업 시작 ===
변경사항 발견: 3.1.2.2_ClassifyAnimals
브랜치 계층 분석 중...
  feature-base: 15개 커밋, 최근 커밋: 1703123456
  feature-ui: 20개 커밋, 최근 커밋: 1703125678
  feature-ui-detail: 25개 커밋, 최근 커밋: 1703127890
계층구조에서 가장 깊은 브랜치 사용: feature-ui-detail
브랜치 체크아웃: feature-ui-detail
브랜치 'feature-ui-detail'로 체크아웃 완료
커밋 완료: 3.1.2.2_ClassifyAnimals
푸시 완료: 3.1.2.2_ClassifyAnimals -> feature-ui-detail
=== 3.1.2.2_ClassifyAnimals Git 작업 완료 ===

=== 모든 작업 완료 ===
```

## 🚨 주의사항

1. **Git 인증**: GitHub에 대한 적절한 인증 설정이 필요합니다 (SSH 키 또는 Personal Access Token)
2. **권한**: 대상 리포지토리에 대한 푸시 권한이 있어야 합니다
3. **백업**: 중요한 변경사항이 있는 경우 수동 백업을 권장합니다
4. **네트워크**: 인터넷 연결이 필요합니다 (Git 푸시 작업)

## 🔧 문제 해결

### Git 인증 오류
```bash
# SSH 키 설정 확인
ssh -T git@github.com

# 또는 HTTPS 인증 설정
git config --global credential.helper store
```

### 인코딩 감지 오류
```bash
# chardet 패키지 재설치
pip uninstall chardet
pip install chardet
```

### 권한 오류
- 프로젝트 폴더에 대한 읽기/쓰기 권한 확인
- Git 리포지토리에 대한 푸시 권한 확인

## 📞 지원

문제가 발생하거나 기능 요청이 있는 경우:
1. GitHub Issues를 통해 문의
2. 로그 출력 내용과 함께 상세한 오류 상황 제공

## 📄 라이선스

이 도구는 교육 목적으로 개발되었습니다.

---

**개발자**: 임주영  
**버전**: 1.0.0  
**최종 업데이트**: 2025년 
