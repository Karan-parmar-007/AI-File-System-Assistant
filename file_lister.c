#include <windows.h>
#include <stdio.h>
#include <tchar.h>
#include <aclapi.h>
#include <time.h>
#include <string.h>

// Function to escape strings for JSON
void print_json_string(const char* str) {
    for (int i = 0; str[i] != '\0'; i++) {
        switch (str[i]) {
            case '"':  printf("\\\""); break;
            case '\\': printf("\\\\"); break;
            case '\b': printf("\\b"); break;
            case '\f': printf("\\f"); break;
            case '\n': printf("\\n"); break;
            case '\r': printf("\\r"); break;
            case '\t': printf("\\t"); break;
            default:
                if ((unsigned char)str[i] < 32) {
                    printf("\\u%04x", str[i]);
                } else {
                    putchar(str[i]);
                }
        }
    }
}

void GetFileOwner(LPTSTR fileName, LPTSTR ownerName, DWORD bufferSize) {
    PSID pSidOwner = NULL;
    PSECURITY_DESCRIPTOR pSD = NULL;
    LPTSTR lpName = NULL;
    LPTSTR lpDomain = NULL;
    DWORD dwNameSize = 0, dwDomainSize = 0;
    SID_NAME_USE sidType;

    strcpy(ownerName, "Unknown");

    if (GetNamedSecurityInfo(fileName, SE_FILE_OBJECT, OWNER_SECURITY_INFORMATION,
                            &pSidOwner, NULL, NULL, NULL, &pSD) == ERROR_SUCCESS) {
        LookupAccountSid(NULL, pSidOwner, NULL, &dwNameSize, NULL, &dwDomainSize, &sidType);
        lpName = (LPTSTR)malloc(dwNameSize * sizeof(TCHAR));
        lpDomain = (LPTSTR)malloc(dwDomainSize * sizeof(TCHAR));
        
        if (LookupAccountSid(NULL, pSidOwner, lpName, &dwNameSize, lpDomain, &dwDomainSize, &sidType)) {
            _snprintf(ownerName, bufferSize, "%s\\\\%s", lpDomain, lpName);
        }
        
        free(lpName);
        free(lpDomain);
        LocalFree(pSD);
    }
}

int main() {
    WIN32_FIND_DATA findData;
    HANDLE hFind;
    SYSTEMTIME st;
    TCHAR ownerName[256];
    int fileCount = 0;
    
    printf("{\n\"files\": [\n");
    
    hFind = FindFirstFile(TEXT("*"), &findData);
    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            if (_tcscmp(findData.cFileName, _T(".")) != 0 && 
                _tcscmp(findData.cFileName, _T("..")) != 0) {
                
                if (fileCount > 0) printf(",\n");
                
                // Get owner
                GetFileOwner(findData.cFileName, ownerName, sizeof(ownerName)/sizeof(TCHAR));
                
                // Get times
                SYSTEMTIME created, modified, accessed;
                FileTimeToSystemTime(&findData.ftCreationTime, &created);
                FileTimeToSystemTime(&findData.ftLastWriteTime, &modified);
                FileTimeToSystemTime(&findData.ftLastAccessTime, &accessed);
                
                // Get file type and size
                BOOL isDir = (findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY);
                long long fileSize = isDir ? 0 : ((long long)findData.nFileSizeHigh << 32) + findData.nFileSizeLow;
                
                // Output JSON with proper escaping
                printf("  {\n");
                printf("    \"name\": \"");
                print_json_string(findData.cFileName);
                printf("\",\n");
                printf("    \"type\": \"%s\",\n", isDir ? "directory" : "file");
                printf("    \"size\": %lld,\n", fileSize);
                printf("    \"size_readable\": \"%s\",\n", 
                       isDir ? "N/A" : 
                       fileSize < 1024 ? "bytes" :
                       fileSize < 1048576 ? "KB" : "MB");
                printf("    \"owner\": \"");
                print_json_string(ownerName);
                printf("\",\n");
                printf("    \"created\": \"%02d/%02d/%04d %02d:%02d:%02d\",\n",
                       created.wMonth, created.wDay, created.wYear,
                       created.wHour, created.wMinute, created.wSecond);
                printf("    \"modified\": \"%02d/%02d/%04d %02d:%02d:%02d\",\n",
                       modified.wMonth, modified.wDay, modified.wYear,
                       modified.wHour, modified.wMinute, modified.wSecond);
                printf("    \"accessed\": \"%02d/%02d/%04d %02d:%02d:%02d\",\n",
                       accessed.wMonth, accessed.wDay, accessed.wYear,
                       accessed.wHour, accessed.wMinute, accessed.wSecond);
                printf("    \"attributes\": {\n");
                printf("      \"hidden\": %s,\n", (findData.dwFileAttributes & FILE_ATTRIBUTE_HIDDEN) ? "true" : "false");
                printf("      \"system\": %s,\n", (findData.dwFileAttributes & FILE_ATTRIBUTE_SYSTEM) ? "true" : "false");
                printf("      \"readonly\": %s\n", (findData.dwFileAttributes & FILE_ATTRIBUTE_READONLY) ? "true" : "false");
                printf("    }\n");
                printf("  }");
                
                fileCount++;
            }
        } while (FindNextFile(hFind, &findData));
        FindClose(hFind);
    }
    
    printf("\n],\n\"total_files\": %d\n}\n", fileCount);
    return 0;
}