@echo off
TITLE Project M5 - 1-Click Codebase Workspace Indexer

echo ===================================================
echo   Project M5: Day 0 Workspace Indexer
echo ===================================================
echo Target Workspace: %CD%
echo.

python "%~dp0backend\app\rag\indexing\workspace_indexer.py" "%CD%" --reset

echo.
echo ===================================================
echo [SUCCESS] Workspace Indexing Complete!
echo ===================================================
pause
