@echo off
setlocal
rem Use the repository Node, and the npm CLI already installed on this machine.
set "MARKETING_NODE=%~dp0..\.tools\node_modules\node\bin\node.exe"
if not exist "%MARKETING_NODE%" (
  echo Local Node is missing. Run npm ci in the .tools directory first.
  exit /b 1
)
set "PATH=%~dp0..\.tools\node_modules\node\bin;%PATH%"
set "MARKETING_NPM="
for /f "delims=" %%I in ('where npm.cmd') do if not defined MARKETING_NPM set "MARKETING_NPM=%%I"
if not defined MARKETING_NPM exit /b 1
for %%I in ("%MARKETING_NPM%") do set "MARKETING_NPM_CLI=%%~dpInode_modules\npm\bin\npm-cli.js"
"%MARKETING_NODE%" "%MARKETING_NPM_CLI%" %*
exit /b %errorlevel%
