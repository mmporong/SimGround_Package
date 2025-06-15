#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;
using System.IO;
using UnityEngine.UI;
using UnityEngine.Events;

[InitializeOnLoad]
public class PackageAssetCopier
{
    static PackageAssetCopier()
    {
        EditorApplication.delayCall += CopyFilesFromPackage;
    }

    public static void CopyFilesFromPackage()
    {
        // 사전 검증 추가
        ValidatePrefabFiles();
        
        // 프리팹 복사
        CopyPrefabFromPackage();
        // 빌드 스크립트 복사
        // CopyBuildScriptFromPackage();
    }

    public static void CopyPrefabFromPackage()
    {
        string packagePrefabPath = "Packages/com.dannect.toolkit/Runtime/Prefabs/SuccessPopup.prefab";
        string projectPrefabPath = "Assets/04.Prefabs/SuccessPopup.prefab";

        string absPackagePath = Path.GetFullPath(packagePrefabPath);
        string absProjectPath = Path.GetFullPath(projectPrefabPath);

        if (!File.Exists(absPackagePath))
        {
            Debug.LogWarning("패키지 프리팹을 찾을 수 없습니다(아직 Import 중일 수 있음): " + absPackagePath);
            return;
        }

        // 1. 복사 전, 패키지 프리팹의 Button OnClick 정보 로그
        LogButtonOnClickInfo(packagePrefabPath);

        // 2. 프리팹 복사
        Directory.CreateDirectory(Path.GetDirectoryName(absProjectPath));
        File.Copy(absPackagePath, absProjectPath, true);
        AssetDatabase.Refresh();

        Debug.Log("패키지 프리팹을 프로젝트로 복사 완료!");
    }

    // Button OnClick 정보 로그 메서드 추가
    private static void LogButtonOnClickInfo(string prefabAssetPath)
    {
        // 프리팹을 임시로 에디터에서 로드
        GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabAssetPath);
        if (prefab == null)
        {
            Debug.LogWarning("프리팹을 에셋DB에서 로드할 수 없습니다: " + prefabAssetPath);
            return;
        }

        // 모든 Button 컴포넌트 순회
        var buttons = prefab.GetComponentsInChildren<Button>(true);
        foreach (var button in buttons)
        {
            Debug.Log($"[Button] {GetHierarchyPath(button.transform)}");

            var onClick = button.onClick;
            int count = onClick.GetPersistentEventCount();
            for (int i = 0; i < count; i++)
            {
                Object target = onClick.GetPersistentTarget(i);
                string method = onClick.GetPersistentMethodName(i);

                // RuntimeOnly, EditorAndRuntime 등 모드 정보 가져오기
                var callState = onClick.GetPersistentListenerState(i);

                // Null 체크 및 정보 출력
                string targetName = target != null ? target.name : "<None>";
                string targetType = target != null ? target.GetType().Name : "<None>";

                Debug.Log(
                    $"  - OnClick {i + 1}: " +
                    $"Mode = {callState}, " +
                    $"오브젝트 = {targetName} ({targetType}), " +
                    $"메소드 = {method}"
                );
            }
        }
    }

    // 계층 경로 구하는 함수
    private static string GetHierarchyPath(Transform transform)
    {
        string path = transform.name;
        while (transform.parent != null)
        {
            transform = transform.parent;
            path = transform.name + "/" + path;
        }
        return path;
    }

    public static void CopyBuildScriptFromPackage()
    {
        string packageScriptPath = "Packages/com.dannect.toolkit/Editor/Scripts/AutoWebGLBuild.cs";
        string projectScriptPath = "Assets/Editor/Scripts/AutoWebGLBuild.cs";

        string absPackagePath = Path.GetFullPath(packageScriptPath);
        string absProjectPath = Path.GetFullPath(projectScriptPath);

        if (!File.Exists(absPackagePath))
        {
            Debug.LogWarning("패키지 빌드 스크립트를 찾을 수 없습니다(아직 Import 중일 수 있음): " + absPackagePath);
            return;
        }


        Directory.CreateDirectory(Path.GetDirectoryName(absProjectPath));
        File.Copy(absPackagePath, absProjectPath, true);
        AssetDatabase.Refresh();

        Debug.Log("패키지 빌드 스크립트를 프로젝트로 복사 완료!");
    }

    // 프리팹 파일 검증 메서드 추가
    private static void ValidatePrefabFiles()
    {
        Debug.Log("=== 패키지 프리팹 파일 검증 시작 ===");
        
        string[] requiredPrefabs = {
            "SuccessPopup.prefab",
            // 필요한 다른 프리팹들 추가 가능
        };
        
        string prefabFolder = "Packages/com.dannect.toolkit/Runtime/Prefabs";
        
        foreach (string prefabName in requiredPrefabs)
        {
            string prefabPath = Path.Combine(prefabFolder, prefabName);
            if (File.Exists(prefabPath))
            {
                Debug.Log($"✅ {prefabName} 존재 확인");
            }
            else
            {
                Debug.LogError($"❌ {prefabName} 파일 없음! 경로: {prefabPath}");
                
                // 대안 파일 제안
                if (Directory.Exists(prefabFolder))
                {
                    Debug.Log("📁 현재 존재하는 프리팹 파일들:");
                    string[] existingFiles = Directory.GetFiles(prefabFolder, "*.prefab");
                    foreach (string file in existingFiles)
                    {
                        Debug.Log($"  - {Path.GetFileName(file)}");
                    }
                }
            }
        }
        
        Debug.Log("=== 패키지 프리팹 파일 검증 완료 ===");
    }
}
#endif 
