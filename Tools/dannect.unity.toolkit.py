import os
import json
import chardet
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# =========================
# #region 프로젝트 폴더 및 패키지 정보 (최상단에 위치)
# =========================
project_dirs = [

    r"E:\5.1.3.2_SolubilityObservation",
    r"E:\5.1.3.3_SolubilityWeight",
    # ... 필요시 추가
]

def get_unity_projects_from_directory(base_dir):
    """지정된 디렉토리에서 Unity 프로젝트들을 자동으로 찾습니다."""
    unity_projects = []
    
    if not os.path.exists(base_dir):
        print(f"기본 디렉토리가 존재하지 않습니다: {base_dir}")
        return unity_projects
    
    try:
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path):
                # Unity 프로젝트인지 확인 (ProjectSettings 폴더 존재 여부)
                project_settings = os.path.join(item_path, "ProjectSettings")
                assets_folder = os.path.join(item_path, "Assets")
                
                if os.path.exists(project_settings) and os.path.exists(assets_folder):
                    unity_projects.append(item_path)
                    print(f"Unity 프로젝트 발견: {item}")
    
    except Exception as e:
        print(f"디렉토리 스캔 오류: {e}")
    
    return unity_projects

# 자동 스캔을 사용하려면 아래 주석을 해제하고 경로를 수정하세요
# project_dirs.extend(get_unity_projects_from_directory(r"E:\UnityProjects"))

git_packages = {
    "com.boxqkrtm.ide.cursor": "https://github.com/boxqkrtm/com.unity.ide.cursor.git",
    "com.dannect.toolkit": "https://github.com/mmporong/SimGround_Package.git"
    
    # 필요시 추가
}

# Git 설정
GIT_BASE_URL = "https://github.com/mmporong/"
DEFAULT_BRANCH = "main"
DEV_BRANCH = "dev"

# Unity CLI 설정
UNITY_EDITOR_PATH = r"D:\Unity\6000.0.30f1\Editor\Unity.exe"  # Unity 설치 경로
UNITY_TIMEOUT = 300  # Unity 실행 타임아웃 (초)
UNITY_LOG_LEVEL = "info"  # Unity 로그 레벨 (debug, info, warning, error)

# Unity WebGL 빌드 설정
BUILD_TARGET = "WebGL"  # WebGL 전용
DEFAULT_BUILD_TARGET = "webgl"
BUILD_OUTPUT_DIR = "Builds"  # 프로젝트 내 빌드 출력 폴더
BUILD_TIMEOUT = 1800  # WebGL 빌드 타임아웃 (30분)
# endregion

# =========================
# #region Git 유틸리티 함수들
# =========================
def run_git_command(command, cwd):
    """Git 명령어를 실행하고 결과를 반환합니다."""
    try:
        result = subprocess.run(
            command, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            shell=True,
            encoding='utf-8'
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def get_project_name_from_path(project_path):
    """프로젝트 경로에서 프로젝트명을 추출합니다."""
    return os.path.basename(project_path.rstrip(os.sep))

def get_repository_url(project_path):
    """프로젝트 경로를 기반으로 Git 리포지토리 URL을 생성합니다."""
    project_name = get_project_name_from_path(project_path)
    return f"{GIT_BASE_URL}{project_name}"

def is_git_repository(project_path):
    """해당 경로가 Git 리포지토리인지 확인합니다."""
    git_dir = os.path.join(project_path, ".git")
    return os.path.exists(git_dir)

def initialize_git_repository(project_path):
    """Git 리포지토리를 초기화하고 원격 저장소를 설정합니다."""
    print(f"Git 리포지토리 초기화 중: {project_path}")
    
    # Git 초기화
    success, stdout, stderr = run_git_command("git init", project_path)
    if not success:
        print(f"Git 초기화 실패: {stderr}")
        return False
    
    # 원격 저장소 추가
    repo_url = get_repository_url(project_path)
    success, stdout, stderr = run_git_command(f"git remote add origin {repo_url}", project_path)
    if not success and "already exists" not in stderr:
        print(f"원격 저장소 추가 실패: {stderr}")
        return False
    
    print(f"Git 리포지토리 초기화 완료: {repo_url}")
    return True

def get_current_branch(project_path):
    """현재 브랜치명을 가져옵니다."""
    success, stdout, stderr = run_git_command("git branch --show-current", project_path)
    if success:
        return stdout.strip()
    return None

def get_all_branches(project_path):
    """모든 브랜치 목록을 가져옵니다."""
    success, stdout, stderr = run_git_command("git branch -a", project_path)
    if success:
        branches = []
        for line in stdout.split('\n'):
            line = line.strip()
            if line and not line.startswith('*'):
                # 원격 브랜치 정보 제거
                branch = line.replace('remotes/origin/', '').strip()
                if branch and branch not in branches:
                    branches.append(branch)
        return branches
    return []

def get_branch_hierarchy_info(project_path, branch_name):
    """브랜치의 계층 정보를 가져옵니다 (커밋 수와 최근 커밋 시간)."""
    # 브랜치의 커밋 수 가져오기
    success, commit_count, stderr = run_git_command(f"git rev-list --count {branch_name}", project_path)
    if not success:
        return 0, 0
    
    # 브랜치의 최근 커밋 시간 가져오기 (Unix timestamp) 
    success, last_commit_time, stderr = run_git_command(f"git log -1 --format=%ct {branch_name}", project_path)
    if not success:
        return int(commit_count) if commit_count.isdigit() else 0, 0
    
    return (
        int(commit_count) if commit_count.isdigit() else 0,
        int(last_commit_time) if last_commit_time.isdigit() else 0
    )

def find_deepest_branch(project_path, branches):
    """브랜치 계층구조에서 가장 깊은(아래) 브랜치를 찾습니다."""
    if not branches:
        return None
    
    # main 브랜치 제외
    filtered_branches = [b for b in branches if b != DEFAULT_BRANCH]
    if not filtered_branches:
        return None
    
    deepest_branch = None
    max_commits = 0
    latest_time = 0
    
    print("브랜치 계층 분석 중...")
    
    for branch in filtered_branches:
        commit_count, last_commit_time = get_branch_hierarchy_info(project_path, branch)
        print(f"  {branch}: {commit_count}개 커밋, 최근 커밋: {last_commit_time}")
        
        # 커밋 수가 더 많거나, 커밋 수가 같으면 더 최근 브랜치 선택
        if (commit_count > max_commits or 
            (commit_count == max_commits and last_commit_time > latest_time)):
            max_commits = commit_count
            latest_time = last_commit_time
            deepest_branch = branch
    
    return deepest_branch

def branch_exists(project_path, branch_name):
    """특정 브랜치가 존재하는지 확인합니다."""
    success, stdout, stderr = run_git_command(f"git show-ref --verify --quiet refs/heads/{branch_name}", project_path)
    return success

def create_and_checkout_branch(project_path, branch_name):
    """새 브랜치를 생성하고 체크아웃합니다."""
    print(f"브랜치 생성 및 체크아웃: {branch_name}")
    success, stdout, stderr = run_git_command(f"git checkout -b {branch_name}", project_path)
    if success:
        print(f"브랜치 '{branch_name}' 생성 완료")
        return True
    else:
        print(f"브랜치 생성 실패: {stderr}")
        return False

def checkout_branch(project_path, branch_name):
    """기존 브랜치로 체크아웃합니다."""
    print(f"브랜치 체크아웃: {branch_name}")
    success, stdout, stderr = run_git_command(f"git checkout {branch_name}", project_path)
    if success:
        print(f"브랜치 '{branch_name}'로 체크아웃 완료")
        return True
    else:
        print(f"브랜치 체크아웃 실패: {stderr}")
        # 다양한 Git 문제 처리
        if ("index" in stderr.lower() or "resolve" in stderr.lower() or 
            "untracked working tree files" in stderr.lower() or 
            "would be overwritten" in stderr.lower()):
            print("Git 상태 문제 감지, 정리 후 체크아웃 재시도...")
            if reset_git_index(project_path):
                success, stdout, stderr = run_git_command(f"git checkout {branch_name}", project_path)
                if success:
                    print(f"브랜치 '{branch_name}'로 체크아웃 완료 (재시도)")
                    return True
                else:
                    print(f"브랜치 체크아웃 재시도 실패: {stderr}")
                    # 강제 체크아웃 시도
                    print("강제 체크아웃 시도...")
                    success, stdout, stderr = run_git_command(f"git checkout -f {branch_name}", project_path)
                    if success:
                        print(f"브랜치 '{branch_name}'로 강제 체크아웃 완료")
                        return True
                    else:
                        print(f"강제 체크아웃도 실패: {stderr}")
                        return False
            else:
                return False
        else:
            return False

def get_target_branch(project_path):
    """커밋할 대상 브랜치를 결정합니다."""
    branches = get_all_branches(project_path)
    
    # 1. 브랜치 계층구조에서 가장 깊은(아래) 브랜치 찾기
    deepest_branch = find_deepest_branch(project_path, branches)
    if deepest_branch:
        print(f"계층구조에서 가장 깊은 브랜치 사용: {deepest_branch}")
        return deepest_branch
    
    # 2. 다른 브랜치가 없으면 dev 브랜치 확인
    if DEV_BRANCH in branches:
        print(f"dev 브랜치 사용")
        return DEV_BRANCH
    
    # 3. dev 브랜치도 없으면 dev 브랜치 생성
    print(f"적절한 브랜치가 없어 dev 브랜치를 새로 생성합니다")
    return DEV_BRANCH

def check_git_status(project_path):
    """Git 상태를 자세히 확인합니다."""
    print("Git 상태 상세 확인 중...")
    
    # 기본 상태 확인
    success, stdout, stderr = run_git_command("git status", project_path)
    if success:
        print("Git 상태:")
        for line in stdout.split('\n')[:10]:  # 처음 10줄만 출력
            if line.strip():
                print(f"  {line}")
    
    # 병합 상태 확인
    success, stdout, stderr = run_git_command("git status --porcelain", project_path)
    if success:
        conflict_files = [line for line in stdout.split('\n') if line.startswith('UU') or line.startswith('AA')]
        if conflict_files:
            print(f"충돌 파일 발견: {len(conflict_files)}개")
            return "conflict"
    
    return "normal"

def clean_untracked_files(project_path):
    """Untracked 파일들을 정리합니다."""
    print("Untracked 파일 정리 중...")
    
    # 먼저 어떤 파일들이 있는지 확인
    success, stdout, stderr = run_git_command("git clean -n", project_path)
    if success and stdout.strip():
        print("정리될 파일들:")
        for line in stdout.split('\n')[:10]:  # 처음 10개만 표시
            if line.strip():
                print(f"  {line}")
    
    # Untracked 파일들 제거 (디렉토리 포함)
    success, stdout, stderr = run_git_command("git clean -fd", project_path)
    if success:
        print("Untracked 파일 정리 완료")
        return True
    else:
        print(f"Untracked 파일 정리 실패: {stderr}")
        return False

def reset_git_index(project_path):
    """Git 인덱스 상태를 리셋합니다."""
    print("Git 인덱스 상태 리셋 중...")
    
    # 상세 상태 확인
    status = check_git_status(project_path)
    
    if status == "conflict":
        print("병합 충돌 감지, 자동 해결 시도...")
        # 병합 중단
        run_git_command("git merge --abort", project_path)
        # rebase 중단도 시도
        run_git_command("git rebase --abort", project_path)
    
    # Untracked 파일들 정리
    clean_untracked_files(project_path)
    
    # 인덱스 리셋
    success, stdout, stderr = run_git_command("git reset", project_path)
    if success:
        print("Git 인덱스 리셋 완료")
        return True
    else:
        print(f"Git 인덱스 리셋 실패: {stderr}")
        # 강제 리셋 시도
        print("강제 리셋 시도...")
        success, stdout, stderr = run_git_command("git reset --hard HEAD", project_path)
        if success:
            print("강제 리셋 완료")
            # 강제 리셋 후에도 untracked 파일 정리
            clean_untracked_files(project_path)
            return True
        else:
            print(f"강제 리셋도 실패: {stderr}")
            return False

def commit_and_push_changes(project_path, commit_message="Auto commit: Unity project updates"):
    """변경사항을 커밋하고 푸시합니다."""
    project_name = get_project_name_from_path(project_path)
    print(f"\n=== {project_name} Git 작업 시작 ===")
    
    # Git 리포지토리 확인 및 초기화
    if not is_git_repository(project_path):
        if not initialize_git_repository(project_path):
            print(f"Git 리포지토리 초기화 실패: {project_path}")
            return False
    
    # Git 상태 확인 및 문제 해결
    success, stdout, stderr = run_git_command("git status --porcelain", project_path)
    if not success:
        print(f"Git 상태 확인 실패: {stderr}")
        # 인덱스 문제일 가능성이 있으므로 리셋 시도
        if not reset_git_index(project_path):
            return False
        # 다시 상태 확인
        success, stdout, stderr = run_git_command("git status --porcelain", project_path)
        if not success:
            print(f"Git 상태 확인 재시도 실패: {stderr}")
            return False
    
    if not stdout.strip():
        print(f"변경사항 없음: {project_name}")
        return True
    
    print(f"변경사항 발견: {project_name}")
    
    # 대상 브랜치 결정
    target_branch = get_target_branch(project_path)
    
    # 브랜치 존재 여부 확인 및 체크아웃
    if branch_exists(project_path, target_branch):
        if not checkout_branch(project_path, target_branch):
            return False
    else:
        if not create_and_checkout_branch(project_path, target_branch):
            return False
    
    # 변경사항 스테이징
    success, stdout, stderr = run_git_command("git add .", project_path)
    if not success:
        print(f"Git add 실패: {stderr}")
        # 인덱스 문제일 가능성이 있으므로 리셋 후 재시도
        if "index" in stderr.lower() or "resolve" in stderr.lower():
            print("인덱스 문제 감지, 리셋 후 재시도...")
            if reset_git_index(project_path):
                success, stdout, stderr = run_git_command("git add .", project_path)
                if not success:
                    print(f"Git add 재시도 실패: {stderr}")
                    return False
            else:
                return False
        else:
            return False
    
    # 커밋
    success, stdout, stderr = run_git_command(f'git commit -m "{commit_message}"', project_path)
    if not success:
        print(f"Git commit 실패: {stderr}")
        return False
    
    print(f"커밋 완료: {project_name}")
    
    # 푸시
    success, stdout, stderr = run_git_command(f"git push -u origin {target_branch}", project_path)
    if not success:
        print(f"Git push 실패: {stderr}")
        return False
    
    print(f"푸시 완료: {project_name} -> {target_branch}")
    print(f"=== {project_name} Git 작업 완료 ===\n")
    return True
# endregion

# =========================
# #region Unity CLI 자동화 함수들
# =========================
def find_unity_editor_path():
    """Unity Editor 경로를 자동으로 찾습니다."""
    # 일반적인 Unity 설치 경로들
    common_paths = [
        r"C:\Program Files\Unity\Hub\Editor",
        r"C:\Program Files\Unity\Editor",
        r"C:\Program Files (x86)\Unity\Hub\Editor",
        r"C:\Program Files (x86)\Unity\Editor"
    ]
    
    for base_path in common_paths:
        if os.path.exists(base_path):
            # 버전 폴더들을 찾아서 가장 최신 버전 선택
            try:
                versions = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
                if versions:
                    # 버전 정렬 (최신 버전 우선)
                    versions.sort(reverse=True)
                    unity_exe = os.path.join(base_path, versions[0], "Editor", "Unity.exe")
                    if os.path.exists(unity_exe):
                        return unity_exe
            except:
                continue
    
    return None

def run_unity_batch_mode(project_path, method_name=None, timeout=UNITY_TIMEOUT):
    """Unity를 배치 모드로 실행하여 Editor 스크립트를 실행합니다."""
    unity_path = UNITY_EDITOR_PATH
    
    # Unity 경로가 존재하지 않으면 자동 검색
    if not os.path.exists(unity_path):
        print(f"Unity 경로를 찾을 수 없습니다: {unity_path}")
        print("Unity 경로 자동 검색 중...")
        unity_path = find_unity_editor_path()
        if not unity_path:
            print("Unity Editor를 찾을 수 없습니다. UNITY_EDITOR_PATH를 확인해주세요.")
            return False
        print(f"Unity 경로 발견: {unity_path}")
    
    project_name = get_project_name_from_path(project_path)
    print(f"Unity 배치 모드 실행 중: {project_name}")
    
    # Unity 명령어 구성
    cmd = [
        unity_path,
        "-batchmode",           # 배치 모드
        "-quit",               # 완료 후 종료
        "-projectPath", project_path,  # 프로젝트 경로
        "-logFile", "-",       # 로그를 콘솔에 출력
    ]
    
    # 특정 메서드 실행이 지정된 경우
    if method_name:
        cmd.extend(["-executeMethod", method_name])
    
    try:
        print(f"Unity 명령어: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8'
        )
        
        # Unity 로그 출력
        if result.stdout:
            print("=== Unity 출력 ===")
            print(result.stdout)
        
        if result.stderr:
            print("=== Unity 오류 ===")
            print(result.stderr)
        
        # Unity는 성공해도 exit code가 0이 아닐 수 있음
        if result.returncode == 0:
            print(f"Unity 배치 모드 완료: {project_name}")
            return True
        else:
            print(f"Unity 배치 모드 경고 (exit code: {result.returncode}): {project_name}")
            # 로그에서 실제 오류 확인
            if "error" in result.stdout.lower() or "exception" in result.stdout.lower():
                print("실제 오류 발견, 실패로 처리")
                return False
            else:
                print("경고이지만 정상 처리된 것으로 판단")
                return True
                
    except subprocess.TimeoutExpired:
        print(f"Unity 실행 타임아웃 ({timeout}초): {project_name}")
        return False
    except Exception as e:
        print(f"Unity 실행 오류: {e}")
        return False

def process_unity_project_batch(project_path):
    """Unity 프로젝트를 배치 모드로 처리합니다."""
    project_name = get_project_name_from_path(project_path)
    
    if not os.path.exists(project_path):
        print(f"프로젝트 폴더가 존재하지 않습니다: {project_path}")
        return False
    
    # Unity 프로젝트인지 확인
    project_settings = os.path.join(project_path, "ProjectSettings", "ProjectSettings.asset")
    if not os.path.exists(project_settings):
        print(f"Unity 프로젝트가 아닙니다: {project_path}")
        return False
    
    print(f"\n=== {project_name} Unity 배치 처리 시작 ===")
    
    # Unity 배치 모드 실행 (패키지 임포트 및 Editor 스크립트 실행)
    success = run_unity_batch_mode(project_path)
    
    if success:
        print(f"=== {project_name} Unity 배치 처리 완료 ===")
        return True
    else:
        print(f"=== {project_name} Unity 배치 처리 실패 ===")
        return False

def create_unity_batch_script(project_path):
    """Unity Editor에서 실행할 배치 스크립트를 생성합니다."""
    script_dir = os.path.join(project_path, "Assets", "Editor", "BatchScripts")
    os.makedirs(script_dir, exist_ok=True)
    
    script_path = os.path.join(script_dir, "AutoBatchProcessor.cs")
    
    script_content = '''using UnityEngine;
using UnityEditor;
using System.IO;

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
            var method = copierType.GetMethod("CopyFilesFromPackage", 
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
            if (method != null)
            {
                Debug.Log("PackageAssetCopier.CopyFilesFromPackage 실행");
                method.Invoke(null, null);
            }
        }
        
        // 최종 Asset Database 갱신
        AssetDatabase.Refresh();
        AssetDatabase.SaveAssets();
        
        Debug.Log("=== 배치 처리 완료 ===");
    }
}
'''
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        print(f"배치 스크립트 생성 완료: {script_path}")
        return True
    except Exception as e:
        print(f"배치 스크립트 생성 실패: {e}")
        return False

def process_multiple_projects_parallel(project_dirs, max_workers=3):
    """여러 Unity 프로젝트를 병렬로 처리합니다."""
    print(f"\n=== 병렬 처리 시작 (최대 {max_workers}개 동시 실행) ===")
    
    success_count = 0
    fail_count = 0
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 모든 프로젝트를 병렬로 제출
        future_to_project = {
            executor.submit(process_unity_project_batch, project_dir): project_dir 
            for project_dir in project_dirs if os.path.exists(project_dir)
        }
        
        # 완료된 작업들을 처리
        for future in as_completed(future_to_project):
            project_dir = future_to_project[future]
            project_name = get_project_name_from_path(project_dir)
            
            try:
                result = future.result()
                if result:
                    success_count += 1
                    print(f"✅ {project_name} 병렬 처리 완료")
                else:
                    fail_count += 1
                    print(f"❌ {project_name} 병렬 처리 실패")
                results.append((project_name, result))
            except Exception as e:
                fail_count += 1
                print(f"❌ {project_name} 병렬 처리 예외: {e}")
                results.append((project_name, False))
    
    print(f"\n=== 병렬 처리 결과 ===")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"총 처리: {success_count + fail_count}개")
    
    return results
# endregion

# =========================
# #region UTF-8 변환 및 Unity 6 API 호환성 함수
# =========================
def convert_to_utf8(filepath):
    # 파일의 원래 인코딩 감지
    with open(filepath, 'rb') as f:
        raw = f.read()
        result = chardet.detect(raw)
        encoding = result['encoding']
    # 이미 UTF-8이면 변환하지 않음
    if encoding and encoding.lower().replace('-', '') == 'utf8':
        return False  # 변환하지 않음
    # 감지된 인코딩으로 읽어서 UTF-8로 저장
    with open(filepath, 'r', encoding=encoding, errors='ignore') as f:
        content = f.read()
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return True  # 변환함

def fix_unity6_deprecated_apis(filepath):
    """Unity 6에서 deprecated된 API들을 최신 API로 교체합니다."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Unity 6 API 교체 규칙들
        api_replacements = [
            # FindObjectOfType -> FindFirstObjectByType
            (r'FindObjectOfType<([^>]+)>\(\)', r'FindFirstObjectByType<\1>()'),
            (r'GameObject\.FindObjectOfType<([^>]+)>\(\)', r'FindFirstObjectByType<\1>()'),
            (r'Object\.FindObjectOfType<([^>]+)>\(\)', r'FindFirstObjectByType<\1>()'),
            
            # FindObjectsOfType -> FindObjectsByType
            (r'FindObjectsOfType<([^>]+)>\(\)', r'FindObjectsByType<\1>(FindObjectsSortMode.None)'),
            (r'GameObject\.FindObjectsOfType<([^>]+)>\(\)', r'FindObjectsByType<\1>(FindObjectsSortMode.None)'),
            (r'Object\.FindObjectsOfType<([^>]+)>\(\)', r'FindObjectsByType<\1>(FindObjectsSortMode.None)'),
            
            # Unity 6 WebGL API 호환성 수정
            (r'PlayerSettings\.WebGL\.debugSymbols\s*=\s*false', r'PlayerSettings.WebGL.debugSymbolMode = WebGLDebugSymbolMode.Off'),
            (r'PlayerSettings\.WebGL\.debugSymbols\s*=\s*true', r'PlayerSettings.WebGL.debugSymbolMode = WebGLDebugSymbolMode.External'),
            (r'PlayerSettings\.WebGL\.wasmStreaming\s*=\s*[^;]+;', r'// Unity 6에서 wasmStreaming 제거됨 (decompressionFallback에 따라 자동 결정)'),
            (r'PlayerSettings\.SplashScreen\.logoAnimationMode[^;]+;', r'// Unity 6에서 logoAnimationMode 제거됨'),
            (r'PlayerSettings\.GetIconsForTargetGroup\(BuildTargetGroup\.([^)]+)\)', 
             r'PlayerSettings.GetIcons(NamedBuildTarget.\1, IconKind.Application)'),
            
            # Camera.main -> Camera.current (일부 상황에서)
            # 주의: 이 교체는 상황에 따라 다를 수 있으므로 주석으로 남겨둠
            # (r'Camera\.main', r'Camera.current'),
        ]
        
        # 각 교체 규칙 적용
        import re
        for old_pattern, new_pattern in api_replacements:
            matches = re.findall(old_pattern, content)
            if matches:
                content = re.sub(old_pattern, new_pattern, content)
                changes_made.append(f"'{old_pattern}' -> '{new_pattern}' ({len(matches)}개 교체)")
        
        # 변경사항이 있으면 파일 저장
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, changes_made
        else:
            return False, []
            
    except Exception as e:
        print(f"Unity 6 API 교체 실패 ({filepath}): {e}")
        return False, []

def process_unity6_compatibility(project_dirs):
    """모든 프로젝트에서 Unity 6 호환성 문제를 수정합니다."""
    print("\n=== Unity 6 API 호환성 수정 시작 ===")
    
    total_files_processed = 0
    total_files_changed = 0
    total_changes = 0
    
    for project_dir in project_dirs:
        if not os.path.exists(project_dir):
            continue
            
        project_name = get_project_name_from_path(project_dir)
        print(f"\n--- {project_name} Unity 6 호환성 수정 ---")
        
        assets_dir = os.path.join(project_dir, "Assets")
        if not os.path.exists(assets_dir):
            print(f"Assets 폴더 없음: {project_dir}")
            continue
        
        files_processed = 0
        files_changed = 0
        project_changes = 0
        
        # Assets 폴더의 모든 C# 파일 처리
        for root, dirs, files in os.walk(assets_dir):
            # Library, Temp 등 불필요한 폴더 제외
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['Library', 'Temp', 'Logs']]
            
            for file in files:
                if file.endswith('.cs'):
                    filepath = os.path.join(root, file)
                    files_processed += 1
                    
                    # Unity 6 API 호환성 수정
                    changed, changes = fix_unity6_deprecated_apis(filepath)
                    if changed:
                        files_changed += 1
                        project_changes += len(changes)
                        print(f"  ✅ {file}: {len(changes)}개 API 교체")
                        for change in changes:
                            print(f"    - {change}")
                    else:
                        print(f"  ⚪ {file}: 변경 없음")
        
        print(f"  📊 {project_name} 결과: {files_processed}개 파일 중 {files_changed}개 수정, 총 {project_changes}개 API 교체")
        
        total_files_processed += files_processed
        total_files_changed += files_changed
        total_changes += project_changes
    
    print(f"\n=== Unity 6 API 호환성 수정 완료 ===")
    print(f"📊 전체 결과: {total_files_processed}개 파일 중 {total_files_changed}개 수정")
    print(f"🔧 총 {total_changes}개 deprecated API 교체 완료")
    
    return total_files_changed > 0

def create_unity6_compatibility_report(project_dirs):
    """Unity 6 호환성 보고서를 생성합니다."""
    print("\n=== Unity 6 호환성 검사 보고서 생성 ===")
    
    deprecated_patterns = [
        r'FindObjectOfType<[^>]+>\(\)',
        r'FindObjectsOfType<[^>]+>\(\)',
        r'PlayerSettings\.WebGL\.debugSymbols',  # Unity 6에서 debugSymbolMode로 변경
        r'PlayerSettings\.WebGL\.wasmStreaming',  # Unity 6에서 제거됨
        r'PlayerSettings\.SplashScreen\.logoAnimationMode',  # Unity 6에서 제거됨
        r'PlayerSettings\.GetIconsForTargetGroup\(',  # Unity 6에서 GetIcons로 변경
        r'Camera\.main(?!\w)',  # Camera.main (단어 경계 확인)
        r'\.SetActive\(true\).*\.SetActive\(false\)',  # 비효율적인 SetActive 패턴
    ]
    
    report_lines = []
    report_lines.append("# Unity 6 호환성 검사 보고서")
    report_lines.append(f"생성 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    for project_dir in project_dirs:
        if not os.path.exists(project_dir):
            continue
            
        project_name = get_project_name_from_path(project_dir)
        report_lines.append(f"## 프로젝트: {project_name}")
        
        assets_dir = os.path.join(project_dir, "Assets")
        if not os.path.exists(assets_dir):
            report_lines.append("❌ Assets 폴더 없음")
            continue
        
        project_issues = []
        
        for root, dirs, files in os.walk(assets_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['Library', 'Temp', 'Logs']]
            
            for file in files:
                if file.endswith('.cs'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        import re
                        for pattern in deprecated_patterns:
                            matches = re.findall(pattern, content)
                            if matches:
                                relative_path = os.path.relpath(filepath, project_dir)
                                project_issues.append(f"  - {relative_path}: {pattern} ({len(matches)}개)")
                    except Exception as e:
                        continue
        
        if project_issues:
            report_lines.append("⚠️ 발견된 호환성 문제:")
            report_lines.extend(project_issues)
        else:
            report_lines.append("✅ 호환성 문제 없음")
        
        report_lines.append("")
    
    # 보고서 파일 저장
    report_path = os.path.join(os.path.dirname(__file__), "unity6_compatibility_report.md")
    try:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        print(f"📋 호환성 보고서 생성 완료: {report_path}")
    except Exception as e:
        print(f"❌ 보고서 생성 실패: {e}")
# endregion

# =========================
# #region Git 패키지 추가 함수
# =========================
def add_git_packages_to_manifest(project_dir, git_packages):
    manifest_path = os.path.join(project_dir, "Packages", "manifest.json")
    if not os.path.exists(manifest_path):
        print(f"{manifest_path} 없음")
        return

    # manifest.json 파일 열기
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    changed = False  # 변경 여부 플래그

    # 모든 Git 패키지 추가/수정
    for name, url in git_packages.items():
        # 이미 동일한 값이 있으면 건너뜀
        if name in manifest["dependencies"] and manifest["dependencies"][name] == url:
            print(f"{name} 이미 설치됨, 생략")
            continue
        manifest["dependencies"][name] = url
        changed = True

    # 변경된 경우에만 저장
    if changed:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4, ensure_ascii=False)
        print(f"{manifest_path}에 패키지들 추가/수정 완료!")
    else:
        print(f"{manifest_path} 변경 없음 (모든 패키지 이미 설치됨)")
# endregion

# =========================
# #region Unity 빌드 자동화 함수들 (Player Settings 완전 반영)
# =========================
def create_unity_webgl_build_script(project_path, output_path=None, auto_configure=True):
    """Unity WebGL 빌드를 위한 Editor 스크립트를 생성합니다. (Player Settings 자동 설정 포함)"""
    editor_dir = os.path.join(project_path, "Assets", "Editor")
    if not os.path.exists(editor_dir):
        os.makedirs(editor_dir)
    
    script_path = os.path.join(editor_dir, "AutoWebGLBuildScript.cs")
    
    if output_path is None:
        output_path = os.path.join(project_path, BUILD_OUTPUT_DIR, "WebGL")
    
    output_path_formatted = output_path.replace(os.sep, '/')
    
    # WebGL 전용 Player Settings를 자동 설정하고 빌드하는 스크립트 (Unity 6 호환)
    script_content = f"""using UnityEngine;
using UnityEditor;
using UnityEditor.Build;
using System.IO;

public class AutoWebGLBuildScript
{{
    [MenuItem("Build/Auto Build WebGL (Player Settings)")]
    public static void BuildWebGLWithPlayerSettings()
    {{
        Debug.Log("=== WebGL Player Settings 자동 설정 및 빌드 시작 ===");
        
        // WebGL Player Settings 자동 설정
        ConfigureWebGLPlayerSettings();
        
        // 설정된 Player Settings 정보 출력
        LogCurrentPlayerSettings();
        
        // 빌드 출력 경로 설정 (Product Name 기반)
        string buildPath = @"{output_path_formatted}";
        
        // Product Name이 설정되어 있다면 경로에 반영
        if (!string.IsNullOrEmpty(PlayerSettings.productName))
        {{
            string safeName = PlayerSettings.productName.Replace(" ", "_");
            // 특수문자 제거
            safeName = System.Text.RegularExpressions.Regex.Replace(safeName, @"[^\\w\\-_]", "");
            buildPath = Path.Combine(Path.GetDirectoryName(buildPath), safeName);
        }}
        
        // 출력 디렉토리 생성
        if (!Directory.Exists(buildPath))
        {{
            Directory.CreateDirectory(buildPath);
            Debug.Log($"빌드 출력 디렉토리 생성: {{buildPath}}");
        }}
        
        // 빌드할 씬들 가져오기 (Build Settings에서 활성화된 씬만)
        string[] scenes = GetBuildScenes();
        if (scenes.Length == 0)
        {{
            Debug.LogError("빌드할 씬이 없습니다. Build Settings에서 씬을 추가하세요.");
            return;
        }}
        
        // WebGL 빌드 옵션 설정 (Player Settings 완전 반영)
        BuildPlayerOptions buildPlayerOptions = new BuildPlayerOptions();
        buildPlayerOptions.scenes = scenes;
        buildPlayerOptions.locationPathName = buildPath;
        buildPlayerOptions.target = BuildTarget.WebGL;
        
        // 빌드 옵션을 Player Settings에 따라 설정
        buildPlayerOptions.options = GetBuildOptionsFromPlayerSettings();
        
        // WebGL 특수 설정 적용
        ApplyWebGLSettings();
        
        Debug.Log($"🌐 WebGL 빌드 시작");
        Debug.Log($"📁 빌드 경로: {{buildPlayerOptions.locationPathName}}");
        Debug.Log($"🎮 제품명: {{PlayerSettings.productName}}");
        Debug.Log($"🏢 회사명: {{PlayerSettings.companyName}}");
        Debug.Log($"📋 버전: {{PlayerSettings.bundleVersion}}");
        
        // WebGL 빌드 실행
        var report = BuildPipeline.BuildPlayer(buildPlayerOptions);
        
        // 빌드 결과 확인
        if (report.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded)
        {{
            Debug.Log($"✅ WebGL 빌드 성공!");
            Debug.Log($"📦 빌드 크기: {{FormatBytes(report.summary.totalSize)}}");
            Debug.Log($"⏱️ 빌드 시간: {{report.summary.totalTime}}");
            Debug.Log($"📁 빌드 경로: {{buildPath}}");
            Debug.Log($"🌐 WebGL 빌드 완료!");
        }}
        else
        {{
            Debug.LogError($"❌ WebGL 빌드 실패: {{report.summary.result}}");
            if (report.summary.totalErrors > 0)
            {{
                Debug.LogError($"에러 수: {{report.summary.totalErrors}}");
            }}
            if (report.summary.totalWarnings > 0)
            {{
                Debug.LogWarning($"경고 수: {{report.summary.totalWarnings}}");
            }}
        }}
        
        Debug.Log("=== WebGL Player Settings 반영 빌드 완료 ===");
    }}
    
    private static void ConfigureWebGLPlayerSettings()
    {{
        Debug.Log("🔧 WebGL Player Settings 이미지 기반 고정 설정 적용 중...");
        
        // 기본 제품 정보 설정 (비어있는 경우에만)
        if (string.IsNullOrEmpty(PlayerSettings.productName))
        {{
            PlayerSettings.productName = "Science Experiment Simulation";
            Debug.Log("✅ 제품명 설정: Science Experiment Simulation");
        }}
        
        if (string.IsNullOrEmpty(PlayerSettings.companyName))
        {{
            PlayerSettings.companyName = "Educational Software";
            Debug.Log("✅ 회사명 설정: Educational Software");
        }}
        
        if (string.IsNullOrEmpty(PlayerSettings.bundleVersion))
        {{
            PlayerSettings.bundleVersion = "1.0.0";
            Debug.Log("✅ 버전 설정: 1.0.0");
        }}
        
        // === 이미지 기반 고정 설정 적용 ===
        
        // Resolution and Presentation 설정 (이미지 기반)
        PlayerSettings.defaultWebScreenWidth = 1655;
        PlayerSettings.defaultWebScreenHeight = 892;
        PlayerSettings.runInBackground = true;
        Debug.Log("✅ 해상도 설정: 1655x892, Run In Background 활성화");
        
        // WebGL Template 설정 (이미지 기반: Minimal)
        PlayerSettings.WebGL.template = "APPLICATION:Minimal";
        Debug.Log("✅ WebGL 템플릿 설정: Minimal");
        
        // Publishing Settings (이미지 기반)
        PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Disabled;
        PlayerSettings.WebGL.nameFilesAsHashes = true;
        PlayerSettings.WebGL.dataCaching = true;
        // Unity 6에서 debugSymbols -> debugSymbolMode로 변경
        PlayerSettings.WebGL.debugSymbolMode = WebGLDebugSymbolMode.Off;
        PlayerSettings.WebGL.showDiagnostics = false;
        PlayerSettings.WebGL.decompressionFallback = false;
        Debug.Log("✅ Publishing Settings: 압축 비활성화, 파일명 해시화, 데이터 캐싱 활성화");
        
        // WebAssembly Language Features (이미지 기반)
        PlayerSettings.WebGL.exceptionSupport = WebGLExceptionSupport.ExplicitlyThrownExceptionsOnly;
        PlayerSettings.WebGL.threadsSupport = false;
        // Unity 6에서 wasmStreaming 제거됨 (decompressionFallback에 따라 자동 결정)
        Debug.Log("✅ WebAssembly 설정: 명시적 예외만, 멀티스레딩 비활성화, 스트리밍 자동");
        
        // Memory Settings (이미지 기반)
        PlayerSettings.WebGL.memorySize = 32;  // Initial Memory Size
        PlayerSettings.WebGL.memoryGrowthMode = WebGLMemoryGrowthMode.Geometric;
        PlayerSettings.WebGL.maximumMemorySize = 2048;
        Debug.Log("✅ 메모리 설정: 초기 32MB, 최대 2048MB, Geometric 증가");
        
        // Splash Screen 설정 (이미지 기반)
        PlayerSettings.SplashScreen.show = true;
        PlayerSettings.SplashScreen.showUnityLogo = false;
        PlayerSettings.SplashScreen.animationMode = PlayerSettings.SplashScreen.AnimationMode.Dolly;
        // Unity 6에서 logoAnimationMode 제거됨
        PlayerSettings.SplashScreen.overlayOpacity = 0.0f;
        PlayerSettings.SplashScreen.blurBackgroundImage = true;
        Debug.Log("✅ 스플래시 화면: Unity 로고 숨김, Dolly 애니메이션, 오버레이 투명");
        
        // WebGL 링커 타겟 설정 (Unity 6 최적화)
        PlayerSettings.WebGL.linkerTarget = WebGLLinkerTarget.Wasm;
        Debug.Log("✅ WebGL 링커 타겟 설정: WebAssembly (Unity 6 최적화)");
        
        Debug.Log("🔧 WebGL Player Settings 이미지 기반 고정 설정 완료");
    }}
    
    private static void LogCurrentPlayerSettings()
    {{
        Debug.Log("=== 현재 WebGL Player Settings ===");
        Debug.Log($"🎮 제품명: {{PlayerSettings.productName}}");
        Debug.Log($"🏢 회사명: {{PlayerSettings.companyName}}");
        Debug.Log($"📋 버전: {{PlayerSettings.bundleVersion}}");
        
        // Unity 6 호환성: 아이콘 API 확인 (Unity 버전에 따라 다름)
        try
        {{
            // Unity 6에서는 NamedBuildTarget과 IconKind 사용
            var icons = PlayerSettings.GetIcons(NamedBuildTarget.WebGL, IconKind.Application);
            Debug.Log($"🖼️ 기본 아이콘: {{(icons != null && icons.Length > 0 ? "설정됨" : "없음")}}");
        }}
        catch
        {{
            Debug.Log($"🖼️ 기본 아이콘: 확인 불가 (Unity 버전 호환성 문제)");
        }}
        
        // WebGL 전용 설정들
        Debug.Log($"🌐 WebGL 템플릿: {{PlayerSettings.WebGL.template}}");
        Debug.Log($"💾 WebGL 메모리 크기: {{PlayerSettings.WebGL.memorySize}}MB");
        Debug.Log($"📦 WebGL 압축 포맷: {{PlayerSettings.WebGL.compressionFormat}}");
        Debug.Log($"⚠️ WebGL 예외 지원: {{PlayerSettings.WebGL.exceptionSupport}}");
        Debug.Log($"💽 WebGL 데이터 캐싱: {{PlayerSettings.WebGL.dataCaching}}");
        Debug.Log($"🔧 WebGL 링커 타겟: {{PlayerSettings.WebGL.linkerTarget}}");
        Debug.Log($"🎯 WebGL 최적화: Unity 6에서 자동 관리");
        Debug.Log("=====================================");
    }}
    
    private static BuildOptions GetBuildOptionsFromPlayerSettings()
    {{
        BuildOptions options = BuildOptions.None;
        
        // Development Build 설정 확인
        if (EditorUserBuildSettings.development)
        {{
            options |= BuildOptions.Development;
            Debug.Log("✅ Development Build 모드 활성화");
        }}
        
        // Script Debugging 설정 확인
        if (EditorUserBuildSettings.allowDebugging)
        {{
            options |= BuildOptions.AllowDebugging;
            Debug.Log("✅ Script Debugging 활성화");
        }}
        
        // Profiler 설정 확인
        if (EditorUserBuildSettings.connectProfiler)
        {{
            options |= BuildOptions.ConnectWithProfiler;
            Debug.Log("✅ Profiler 연결 활성화");
        }}
        
        // Deep Profiling 설정 확인
        if (EditorUserBuildSettings.buildWithDeepProfilingSupport)
        {{
            options |= BuildOptions.EnableDeepProfilingSupport;
            Debug.Log("✅ Deep Profiling 지원 활성화");
        }}
        
        // Unity 6에서 autoRunPlayer 제거됨
        // WebGL은 브라우저에서 실행되므로 AutoRunPlayer 옵션 불필요
        Debug.Log("ℹ️ WebGL 빌드는 브라우저에서 수동 실행");
        
        return options;
    }}
    
    private static void ApplyWebGLSettings()
    {{
        Debug.Log("🌐 WebGL 특수 설정 적용 및 검증 중...");
        
        Debug.Log($"🌐 WebGL 템플릿 사용: {{PlayerSettings.WebGL.template}}");
        Debug.Log($"💾 WebGL 메모리 크기: {{PlayerSettings.WebGL.memorySize}}MB");
        Debug.Log($"📦 WebGL 압축 포맷: {{PlayerSettings.WebGL.compressionFormat}}");
        Debug.Log($"⚠️ WebGL 예외 지원: {{PlayerSettings.WebGL.exceptionSupport}}");
        Debug.Log($"💽 WebGL 데이터 캐싱: {{PlayerSettings.WebGL.dataCaching}}");
        
        // WebGL 최적화 설정 확인 및 권장사항
        if (PlayerSettings.WebGL.memorySize < 256)
        {{
            Debug.LogWarning("⚠️ WebGL 메모리 크기가 256MB 미만입니다. 과학실험 시뮬레이션에는 512MB 이상 권장합니다.");
        }}
        else if (PlayerSettings.WebGL.memorySize >= 512)
        {{
            Debug.Log("✅ WebGL 메모리 크기가 적절합니다 (512MB 이상).");
        }}
        
        if (string.IsNullOrEmpty(PlayerSettings.WebGL.template) || PlayerSettings.WebGL.template == "APPLICATION:Default")
        {{
            Debug.LogWarning("⚠️ WebGL 템플릿이 기본값입니다. 교육용 템플릿 사용을 권장합니다.");
        }}
        else
        {{
            Debug.Log($"✅ WebGL 템플릿 설정됨: {{PlayerSettings.WebGL.template}}");
        }}
        
        // WebGL 압축 설정 확인
        if (PlayerSettings.WebGL.compressionFormat == WebGLCompressionFormat.Disabled)
        {{
            Debug.LogWarning("⚠️ WebGL 압축이 비활성화되어 있습니다. 파일 크기가 클 수 있습니다.");
        }}
        else
        {{
            Debug.Log($"✅ WebGL 압축 활성화: {{PlayerSettings.WebGL.compressionFormat}}");
        }}
        
        // 과학실험 시뮬레이션에 최적화된 설정 권장사항
        Debug.Log("📚 과학실험 시뮬레이션 최적화 권장사항:");
        Debug.Log("  - 메모리: 512MB 이상");
        Debug.Log("  - 압축: Gzip 또는 Brotli");
        Debug.Log("  - 예외 지원: ExplicitlyThrownExceptionsOnly");
        Debug.Log("  - 데이터 캐싱: 활성화");
    }}
    
    private static string[] GetBuildScenes()
    {{
        // Build Settings에서 활성화된 씬들만 가져오기
        var enabledScenes = new System.Collections.Generic.List<string>();
        
        foreach (var scene in EditorBuildSettings.scenes)
        {{
            if (scene.enabled)
            {{
                enabledScenes.Add(scene.path);
            }}
        }}
        
        Debug.Log($"📋 빌드할 씬 수: {{enabledScenes.Count}}");
        foreach (var scene in enabledScenes)
        {{
            Debug.Log($"  - {{scene}}");
        }}
        
        return enabledScenes.ToArray();
    }}
    
    private static string FormatBytes(ulong bytes)
    {{
        string[] sizes = {{ "B", "KB", "MB", "GB", "TB" }};
        double len = bytes;
        int order = 0;
        while (len >= 1024 && order < sizes.Length - 1)
        {{
            order++;
            len = len / 1024;
        }}
        return $"{{len:0.##}} {{sizes[order]}}";
    }}
}}
"""
    
    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        print(f"WebGL 전용 빌드 스크립트 생성 완료: {script_path}")
        return True
    except Exception as e:
        print(f"WebGL 빌드 스크립트 생성 실패: {e}")
        return False

def run_unity_webgl_build(project_path, timeout=BUILD_TIMEOUT):
    """Unity CLI를 사용하여 WebGL 빌드를 실행합니다. (Player Settings 완전 반영)"""
    unity_path = UNITY_EDITOR_PATH
    
    # Unity 경로가 존재하지 않으면 자동 검색
    if not os.path.exists(unity_path):
        print(f"Unity 경로를 찾을 수 없습니다: {unity_path}")
        print("Unity 경로 자동 검색 중...")
        unity_path = find_unity_editor_path()
        if not unity_path:
            print("Unity Editor를 찾을 수 없습니다. UNITY_EDITOR_PATH를 확인해주세요.")
            return False
        print(f"Unity 경로 발견: {unity_path}")
    
    project_name = get_project_name_from_path(project_path)
    
    print(f"🌐 Unity WebGL Player Settings 반영 빌드 시작: {project_name}")
    
    # WebGL 전용 빌드 스크립트 생성
    if not create_unity_webgl_build_script(project_path):
        return False
    
    # Unity CLI 명령어 구성
    cmd = [
        unity_path,
        "-batchmode",
        "-quit", 
        "-projectPath", project_path,
        "-buildTarget", "WebGL",
        "-executeMethod", "AutoWebGLBuildScript.BuildWebGLWithPlayerSettings",
        "-logFile", "-"
    ]
    
    try:
        print(f"🌐 Unity WebGL 빌드 실행 중... (타임아웃: {timeout}초)")
        print(f"명령어: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # 로그 출력
        if result.stdout:
            print("=== Unity WebGL 빌드 로그 ===")
            print(result.stdout)
        
        if result.stderr:
            print("=== Unity WebGL 빌드 에러 ===")
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ Unity WebGL 빌드 성공: {project_name}")
            return True
        else:
            print(f"❌ Unity WebGL 빌드 실패: {project_name} (종료 코드: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Unity WebGL 빌드 타임아웃: {project_name} ({timeout}초 초과)")
        return False
    except Exception as e:
        print(f"❌ Unity WebGL 빌드 예외: {project_name} - {e}")
        return False

def build_multiple_webgl_projects(project_dirs, parallel=False, max_workers=2):
    """여러 Unity 프로젝트를 WebGL로 빌드합니다."""
    print(f"\n=== Unity WebGL 다중 프로젝트 빌드 시작 ===")
    
    if parallel:
        return build_multiple_webgl_projects_parallel(project_dirs, max_workers)
    else:
        return build_multiple_webgl_projects_sequential(project_dirs)

def build_multiple_webgl_projects_sequential(project_dirs):
    """여러 Unity 프로젝트를 WebGL로 순차적으로 빌드합니다."""
    success_count = 0
    fail_count = 0
    results = []
    
    for project_dir in project_dirs:
        if not os.path.exists(project_dir):
            print(f"❌ 프로젝트 경로가 존재하지 않습니다: {project_dir}")
            fail_count += 1
            results.append((get_project_name_from_path(project_dir), False))
            continue
        
        project_name = get_project_name_from_path(project_dir)
        print(f"\n--- {project_name} WebGL 빌드 시작 ---")
        
        if run_unity_webgl_build(project_dir):
            success_count += 1
            results.append((project_name, True))
        else:
            fail_count += 1
            results.append((project_name, False))
    
    print(f"\n=== WebGL 순차 빌드 결과 ===")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"총 빌드: {success_count + fail_count}개")
    
    return results

def build_multiple_webgl_projects_parallel(project_dirs, max_workers=2):
    """여러 Unity 프로젝트를 WebGL로 병렬로 빌드합니다."""
    print(f"🌐 WebGL 병렬 빌드 시작 (최대 {max_workers}개 동시 실행)")
    
    success_count = 0
    fail_count = 0
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 모든 프로젝트를 병렬로 제출
        future_to_project = {
            executor.submit(run_unity_webgl_build, project_dir): project_dir 
            for project_dir in project_dirs if os.path.exists(project_dir)
        }
        
        # 완료된 작업들을 처리
        for future in as_completed(future_to_project):
            project_dir = future_to_project[future]
            project_name = get_project_name_from_path(project_dir)
            
            try:
                result = future.result()
                if result:
                    success_count += 1
                    print(f"✅ {project_name} WebGL 병렬 빌드 완료")
                else:
                    fail_count += 1
                    print(f"❌ {project_name} WebGL 병렬 빌드 실패")
                results.append((project_name, result))
            except Exception as e:
                fail_count += 1
                print(f"❌ {project_name} WebGL 병렬 빌드 예외: {e}")
                results.append((project_name, False))
    
    print(f"\n=== WebGL 병렬 빌드 결과 ===")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    print(f"총 빌드: {success_count + fail_count}개")
    
    return results

def clean_build_outputs(project_dirs):
    """모든 프로젝트의 빌드 출력물을 정리합니다."""
    print("\n=== 빌드 출력물 정리 시작 ===")
    
    cleaned_count = 0
    for project_dir in project_dirs:
        if not os.path.exists(project_dir):
            continue
            
        project_name = get_project_name_from_path(project_dir)
        build_dir = os.path.join(project_dir, BUILD_OUTPUT_DIR)
        
        if os.path.exists(build_dir):
            try:
                import shutil
                shutil.rmtree(build_dir)
                print(f"✅ {project_name} 빌드 출력물 정리 완료")
                cleaned_count += 1
            except Exception as e:
                print(f"❌ {project_name} 빌드 출력물 정리 실패: {e}")
        else:
            print(f"⚪ {project_name} 빌드 출력물 없음")
    
    print(f"총 {cleaned_count}개 프로젝트 빌드 출력물 정리 완료")
# endregion

# =========================
# #region 메인 실행부
# =========================

def print_usage():
    """사용법을 출력합니다."""
    print("=== Unity 프로젝트 자동화 도구 사용법 ===")
    print("python dannect.unity.toolkit.py [옵션]")
    print("")
    print("옵션:")
    print("  --help           이 도움말을 표시합니다")
    print("  --skip-git       Git 작업을 건너뜁니다 (UTF-8 변환과 패키지 추가만 실행)")
    print("  --git-only       Git 작업만 실행합니다 (UTF-8 변환과 패키지 추가 건너뜀)")
    print("  --unity-batch    Unity 배치 모드로 Editor 스크립트 실행 (40개 프로젝트 자동화)")
    print("  --full-auto      모든 작업 + Unity 배치 모드 실행 (완전 자동화)")
    print("  --parallel       Unity 배치 모드를 병렬로 실행 (빠른 처리, 메모리 사용량 증가)")
    print("  --build-webgl    Unity WebGL 빌드 자동화 (Player Settings 완전 반영)")
    print("  --build-parallel WebGL 빌드를 병렬로 실행 (2개씩 동시 빌드)")
    print("  --clean-builds   모든 빌드 출력물 정리")
    print("  --fix-unity6     Unity 6 deprecated API 자동 수정 (FindObjectOfType 등)")
    print("  --check-unity6   Unity 6 호환성 검사 보고서 생성")
    print("")
    print("기본 동작:")
    print("1. C# 파일 UTF-8 변환")
    print("2. Unity 6 deprecated API 자동 수정")
    print("3. Unity 패키지 추가")
    print("4. Git 커밋 및 푸시 (계층구조 최하위 브랜치 또는 dev 브랜치)")
    print("")
    print("Unity 6 호환성 수정 (--fix-unity6):")
    print("- FindObjectOfType -> FindFirstObjectByType 자동 교체")
    print("- FindObjectsOfType -> FindObjectsByType 자동 교체")
    print("- PlayerSettings.GetIconsForTargetGroup -> PlayerSettings.GetIcons 교체")
    print("- 기타 Unity 6에서 deprecated된 API들 일괄 수정")
    print("- 모든 C# 스크립트 파일을 자동으로 스캔하여 수정")
    print("- 변경 내용 상세 로그 출력")
    print("")
    print("Unity 배치 모드 (--unity-batch, --full-auto):")
    print("- Unity Editor를 배치 모드로 실행하여 Editor 스크립트 자동 실행")
    print("- PackageAssetCopier 등의 [InitializeOnLoad] 스크립트 실행")
    print("- 40개 프로젝트를 순차적으로 자동 처리 (기본)")
    print("- --parallel 옵션으로 병렬 처리 가능 (3개씩 동시 실행)")
    print("- Unity GUI 없이 백그라운드에서 실행")
    print("")
    print("Unity WebGL 빌드 자동화 (--build-webgl):")
    print("- Unity CLI를 사용하여 WebGL 프로젝트를 자동 빌드")
    print("- Player Settings 완전 반영 (제품명, 회사명, 버전, WebGL 설정 등)")
    print("- Build Settings의 활성화된 씬만 빌드")
    print("- Development Build, Profiler 등 빌드 옵션 자동 적용")
    print("- WebGL 전용 최적화 설정 적용 (메모리, 압축, 템플릿 등)")
    print("- 과학실험 시뮬레이션에 최적화된 WebGL 빌드")
    print("- 빌드 출력: 각 프로젝트의 Builds/WebGL 폴더")
    print("- --build-parallel로 병렬 빌드 가능 (2개씩 동시 빌드)")
    print("- 빌드 시간: 프로젝트당 5-15분 (WebGL 최적화 포함)")
    print("")
    print("Git 브랜치 전략:")
    print("- 브랜치 계층구조에서 가장 깊은(아래) 브랜치를 우선 사용")
    print("- 커밋 수가 많고 최근에 작업된 브랜치 선택")
    print("- 적절한 브랜치가 없으면 dev 브랜치 사용/생성")
    print("=====================================")

def main():
    """메인 실행 함수"""
    # 도움말 요청 확인
    if "--help" in sys.argv or "-h" in sys.argv:
        print_usage()
        return
    
    print("=== Unity 프로젝트 자동화 도구 시작 ===\n")
    
    # 명령행 인수 확인
    skip_git = "--skip-git" in sys.argv
    git_only = "--git-only" in sys.argv
    unity_batch = "--unity-batch" in sys.argv
    full_auto = "--full-auto" in sys.argv
    parallel = "--parallel" in sys.argv
    build_webgl = "--build-webgl" in sys.argv
    build_parallel = "--build-parallel" in sys.argv
    clean_builds = "--clean-builds" in sys.argv
    fix_unity6 = "--fix-unity6" in sys.argv
    check_unity6 = "--check-unity6" in sys.argv
    
    if full_auto:
        print("완전 자동화 모드: 모든 작업 + Unity 배치 모드 실행...\n")
        unity_batch = True  # full_auto는 unity_batch 포함
    elif unity_batch:
        print("Unity 배치 모드만 실행합니다...\n")
        skip_git = True  # unity_batch만 실행할 때는 다른 작업 건너뜀
    elif git_only:
        print("Git 작업만 실행합니다...\n")
    elif skip_git:
        print("Git 작업을 건너뜁니다...\n")
    
    # Unity 6 호환성 검사만 실행하는 경우
    if check_unity6:
        create_unity6_compatibility_report(project_dirs)
        return
    
    # Unity 6 호환성 수정만 실행하는 경우
    if fix_unity6:
        process_unity6_compatibility(project_dirs)
        return

    # 1. UTF-8 변환 (git-only가 아닌 경우에만 실행)
    if not git_only:
        print("1. C# 파일 UTF-8 변환 작업 시작...")
        for project_dir in project_dirs:
            project_name = get_project_name_from_path(project_dir)
            print(f"\n--- {project_name} UTF-8 변환 ---")
            
            root_dir = os.path.join(project_dir, "Assets")
            if not os.path.exists(root_dir):
                print(f"Assets 폴더 없음: {project_dir}")
                continue
                
            for subdir, _, files in os.walk(root_dir):
                for file in files:
                    if file.endswith('.cs'):
                        try:
                            changed = convert_to_utf8(os.path.join(subdir, file))
                            if changed:
                                print(f"  {file} 변환 완료")
                            else:
                                print(f"  {file} 이미 UTF-8, 변환 생략")
                        except Exception as e:
                            print(f"  {file} 변환 실패: {e}")

        # 2. Unity 6 deprecated API 자동 수정
        print("\n2. Unity 6 deprecated API 자동 수정 시작...")
        unity6_changes_made = process_unity6_compatibility(project_dirs)

        # 3. 각 프로젝트에 패키지 추가
        print("\n3. Unity 패키지 추가 작업 시작...")
        for project_dir in project_dirs:
            project_name = get_project_name_from_path(project_dir)
            print(f"\n--- {project_name} 패키지 추가 ---")
            add_git_packages_to_manifest(project_dir, git_packages)

    # 4. Git 커밋 및 푸시 (skip-git가 아닌 경우에만 실행)
    if not skip_git:
        print("\n4. Git 커밋 및 푸시 작업 시작...")
        
        # 커밋 메시지 생성 (Unity 6 호환성 수정 포함)
        commit_message = "Auto commit: Unity project updates"
        if 'unity6_changes_made' in locals() and unity6_changes_made:
            commit_message += ", Unity 6 API compatibility fixes"
        commit_message += ", and package additions"
        
        for project_dir in project_dirs:
            if os.path.exists(project_dir):
                commit_and_push_changes(project_dir, commit_message)
            else:
                print(f"프로젝트 폴더 없음: {project_dir}")

    # 5. Unity 배치 모드 실행 (unity-batch 또는 full-auto인 경우에만 실행)
    if unity_batch:
        print("\n5. Unity 배치 모드 실행 시작...")
        print(f"총 {len(project_dirs)}개 프로젝트 처리 예정")
        
        # 모든 프로젝트에 배치 스크립트 생성
        print("배치 스크립트 생성 중...")
        for project_dir in project_dirs:
            if os.path.exists(project_dir):
                create_unity_batch_script(project_dir)
        
        if parallel:
            # 병렬 처리
            print("병렬 처리 모드로 실행합니다...")
            process_multiple_projects_parallel(project_dirs, max_workers=3)
        else:
            # 순차 처리 (기본)
            print("순차 처리 모드로 실행합니다...")
            success_count = 0
            fail_count = 0
            
            for i, project_dir in enumerate(project_dirs, 1):
                project_name = get_project_name_from_path(project_dir)
                print(f"\n[{i}/{len(project_dirs)}] {project_name} 처리 중...")
                
                if not os.path.exists(project_dir):
                    print(f"프로젝트 폴더 없음: {project_dir}")
                    fail_count += 1
                    continue
                
                # Unity 배치 모드 실행
                if process_unity_project_batch(project_dir):
                    success_count += 1
                    print(f"✅ {project_name} 처리 완료")
                else:
                    fail_count += 1
                    print(f"❌ {project_name} 처리 실패")
            
            print(f"\n=== Unity 배치 모드 결과 ===")
            print(f"성공: {success_count}개")
            print(f"실패: {fail_count}개")
            print(f"총 처리: {success_count + fail_count}개")
    
    # 6. 빌드 출력물 정리 (clean-builds인 경우에만 실행)
    if clean_builds:
        print("\n6. 빌드 출력물 정리 시작...")
        clean_build_outputs(project_dirs)
    
    # 7. Unity WebGL 프로젝트 빌드 (build-webgl인 경우에만 실행)
    if build_webgl:
        print(f"\n7. Unity WebGL 프로젝트 빌드 시작...")
        
        print(f"🌐 빌드 타겟: WebGL")
        print(f"📊 총 {len(project_dirs)}개 프로젝트 빌드 예정")
        print("🎯 WebGL Player Settings 완전 반영 빌드 모드")
        print("📚 과학실험 시뮬레이션 최적화 적용")
        
        # WebGL 빌드 실행
        build_results = build_multiple_webgl_projects(
            project_dirs, 
            parallel=build_parallel,
            max_workers=2 if build_parallel else 1
        )
        
        # 빌드 결과 요약
        success_builds = sum(1 for _, success in build_results if success)
        fail_builds = len(build_results) - success_builds
        
        print(f"\n=== 최종 WebGL 빌드 결과 ===")
        print(f"✅ 성공: {success_builds}개")
        print(f"❌ 실패: {fail_builds}개")
        print(f"📊 총 빌드: {len(build_results)}개")
        
        if success_builds > 0:
            print(f"\n🌐 WebGL 빌드 완료된 프로젝트들:")
            for project_name, success in build_results:
                if success:
                    print(f"  - {project_name}")
        
        if fail_builds > 0:
            print(f"\n❌ WebGL 빌드 실패한 프로젝트들:")
            for project_name, success in build_results:
                if not success:
                    print(f"  - {project_name}")
    
    print("\n=== 모든 작업 완료 ===")

if __name__ == "__main__":
    main()

# endregion 