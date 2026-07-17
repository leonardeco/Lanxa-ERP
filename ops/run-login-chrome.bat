@echo off
setlocal
set "ROOT=%~dp0.."
copy /Y "%ROOT%\ops\_login_chrome.cjs" "%ROOT%\frontend\_login_chrome.cjs" >nul
set "ERP_CRED_FILE=%ROOT%\ops\smoke-screens\_login_cred.json"
set "ERP_URL=https://127.0.0.1:5173"
set "ERP_KEEP_MS=1200000"
start "ERP-Login-Chrome" /D "%ROOT%\frontend" cmd /k "node _login_chrome.cjs"
echo Login Chrome launched.
endlocal
exit /b 0
