!define APP_NAME "Mi Querido Lomito CRM"
!define APP_EXE "MiQueridoLomitoCRM.exe"
!define APP_PUBLISHER "Mi Querido Lomito"
!define APP_VERSION "1.0.0"
!define APP_ICON "icon.ico"
!define UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\MiQueridoLomitoCRM"

Name "${APP_NAME}"
OutFile "dist\MiQueridoLomitoCRM_Setup.exe"
InstallDir "$LOCALAPPDATA\MiQueridoLomitoCRM"
RequestExecutionLevel user
SetCompressor /SOLID lzma

!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "${APP_ICON}"
!define MUI_UNICON "${APP_ICON}"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Abrir ${APP_NAME}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Spanish"

Section "Instalar" SecInstall
    SetShellVarContext current
    SetOutPath "$INSTDIR"
    File "dist\${APP_EXE}"
    File "${APP_ICON}"

    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_ICON}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\Desinstalar ${APP_NAME}.lnk" "$INSTDIR\uninstall.exe"
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_ICON}"

    WriteUninstaller "$INSTDIR\uninstall.exe"

    WriteRegStr HKCU "${UNINST_KEY}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKCU "${UNINST_KEY}" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
    WriteRegStr HKCU "${UNINST_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "${UNINST_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
    WriteRegStr HKCU "${UNINST_KEY}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKCU "${UNINST_KEY}" "DisplayVersion" "${APP_VERSION}"
    WriteRegDWORD HKCU "${UNINST_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${UNINST_KEY}" "NoRepair" 1
SectionEnd

Section "Uninstall"
    SetShellVarContext current
    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\${APP_ICON}"
    Delete "$INSTDIR\lomito_config.json"
    Delete "$INSTDIR\uninstall.exe"
    RMDir "$INSTDIR"

    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Desinstalar ${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"

    DeleteRegKey HKCU "${UNINST_KEY}"
SectionEnd
