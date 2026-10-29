@echo off
setlocal
set "PDT_JAR=%~dp0PDT_3_2b.jar"
set "PDT_PROJECT=%~dp0Walker_Guardiao_MASPY.pd"

if exist "C:\Program Files (x86)\Java\jre1.8.0_511\bin\javaw.exe" (
    start "" "C:\Program Files (x86)\Java\jre1.8.0_511\bin\javaw.exe" -jar "%PDT_JAR%" -p "%PDT_PROJECT%"
    exit /b 0
)

if exist "C:\Program Files\Java\jdk-11.0.16.1\bin\javaw.exe" (
    start "" "C:\Program Files\Java\jdk-11.0.16.1\bin\javaw.exe" -jar "%PDT_JAR%" -p "%PDT_PROJECT%"
    exit /b 0
)

start "" javaw -jar "%PDT_JAR%" -p "%PDT_PROJECT%"
