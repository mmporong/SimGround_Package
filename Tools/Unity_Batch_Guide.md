# Unity 프로젝트 40개 자동화 가이드

## 문제 상황
- 40개의 Unity 프로젝트가 있음
- 각 프로젝트마다 Editor 스크립트 실행이 필요함
- 일일이 Unity를 열어서 처리하기에는 너무 비효율적

## 해결 방안: Unity CLI 배치 모드 자동화

### 1. 기본 설정

#### Unity 경로 설정
```python
# dannect.unity.toolkit.py 상단에서 설정
UNITY_EDITOR_PATH = r"C:\Program Files\Unity\Hub\Editor\2022.3.45f1\Editor\Unity.exe"
```

#### 프로젝트 목록 설정
```python
project_dirs = [
    r"E:\Project1",
    r"E:\Project2",
    r"E:\Project3",
    # ... 40개 프로젝트 경로
]

# 또는 자동 스캔 사용
project_dirs.extend(get_unity_projects_from_directory(r"E:\UnityProjects"))
```

### 2. 실행 옵션

#### 완전 자동화 (권장)
```bash
python dannect.unity.toolkit.py --full-auto
```
- UTF-8 변환 + 패키지 추가 + Git 작업 + Unity 배치 모드
- 40개 프로젝트 완전 자동 처리

#### Unity 배치 모드만 실행
```bash
python dannect.unity.toolkit.py --unity-batch
```
- Unity 배치 모드만 실행 (다른 작업 건너뜀)

#### 병렬 처리 (빠른 처리)
```bash
python dannect.unity.toolkit.py --full-auto --parallel
```
- 3개 프로젝트를 동시에 처리
- 처리 시간 단축 (메모리 사용량 증가)

### 3. Unity 배치 모드 동작 원리

#### 자동 생성되는 배치 스크립트
각 프로젝트에 `Assets/Editor/BatchScripts/AutoBatchProcessor.cs` 생성:

```csharp
public class AutoBatchProcessor
{
    [MenuItem("Tools/Process Batch")]
    public static void ProcessBatch()
    {
        Debug.Log("=== 배치 처리 시작 ===");
        
        // 패키지 임포트 대기
        AssetDatabase.Refresh();
        
        // PackageAssetCopier가 있다면 실행
        var copierType = System.Type.GetType("PackageAssetCopier");
        if (copierType != null)
        {
            var method = copierType.GetMethod("CopyFilesFromPackage");
            if (method != null)
            {
                method.Invoke(null, null);
            }
        }
        
        AssetDatabase.Refresh();
        AssetDatabase.SaveAssets();
        
        Debug.Log("=== 배치 처리 완료 ===");
    }
}
```

#### Unity CLI 명령어
```bash
Unity.exe -batchmode -quit -projectPath "E:\Project1" -logFile -
```

### 4. 처리 흐름

#### 순차 처리 (기본)
```
프로젝트1 → Unity 실행 → Editor 스크립트 실행 → 종료
프로젝트2 → Unity 실행 → Editor 스크립트 실행 → 종료
...
프로젝트40 → Unity 실행 → Editor 스크립트 실행 → 종료
```

#### 병렬 처리 (--parallel)
```
프로젝트1, 2, 3 → 동시 Unity 실행 → 완료 후 다음 3개
프로젝트4, 5, 6 → 동시 Unity 실행 → 완료 후 다음 3개
...
```

### 5. 예상 처리 시간

#### 순차 처리
- 프로젝트당 평균 2-3분
- 40개 프로젝트: 약 80-120분

#### 병렬 처리
- 3개씩 동시 처리
- 40개 프로젝트: 약 30-40분

### 6. 시스템 요구사항

#### 최소 사양
- RAM: 8GB 이상 (순차 처리)
- RAM: 16GB 이상 (병렬 처리)
- 디스크 여유공간: 각 프로젝트당 1GB 이상

#### 권장 사양
- RAM: 32GB (병렬 처리 최적)
- SSD 스토리지
- 멀티코어 CPU

### 7. 문제 해결

#### Unity 경로를 찾을 수 없는 경우
```python
# 자동 검색 기능 사용
unity_path = find_unity_editor_path()
```

#### 타임아웃 발생 시
```python
# 타임아웃 시간 증가
UNITY_TIMEOUT = 600  # 10분으로 증가
```

#### 메모리 부족 시
```python
# 병렬 처리 수 감소
process_multiple_projects_parallel(project_dirs, max_workers=2)
```

### 8. 로그 확인

#### 성공 예시
```
✅ Project1 처리 완료
✅ Project2 처리 완료
...
=== Unity 배치 모드 결과 ===
성공: 38개
실패: 2개
총 처리: 40개
```

#### 실패 시 확인사항
1. Unity 경로가 올바른지 확인
2. 프로젝트 폴더가 존재하는지 확인
3. Unity 프로젝트가 손상되지 않았는지 확인
4. 디스크 여유공간 확인

### 9. 실제 사용 예시

#### 40개 프로젝트 완전 자동화
```bash
# 1. 프로젝트 목록 설정
# project_dirs에 40개 경로 추가

# 2. 완전 자동화 실행
python dannect.unity.toolkit.py --full-auto --parallel

# 3. 결과 확인
# 성공/실패 개수 확인
# 실패한 프로젝트는 개별 처리
```

이제 **Unity를 일일이 열지 않고도 40개 프로젝트를 자동으로 처리**할 수 있습니다! 