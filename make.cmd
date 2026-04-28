@echo off
setlocal

if "%~1"=="" goto :usage

if /I "%~1"=="perf-preflight" (
  powershell -ExecutionPolicy Bypass -File backend\scripts\perf_preflight.ps1
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="perf-phase0" (
  powershell -ExecutionPolicy Bypass -File backend\scripts\run_phase0_e2e.ps1
  exit /b %ERRORLEVEL%
)

if /I "%~1"=="perf-phase0-safe" (
  powershell -ExecutionPolicy Bypass -File backend\scripts\run_phase0_safe.ps1
  exit /b %ERRORLEVEL%
)

echo Unknown target: %~1
goto :usage

:usage
echo Available targets:
echo   make perf-preflight
echo   make perf-phase0
echo   make perf-phase0-safe
exit /b 1
