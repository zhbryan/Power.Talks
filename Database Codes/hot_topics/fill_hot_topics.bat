@echo off
REM Power.Talks — daily Hot Topics AI fill (Windows Task Scheduler wrapper).
REM Runs Claude Code headless to fill today's scaffolded Hot Topics report
REM (live web research -> per-source summaries -> ERCOT-only topic ranking) and
REM refresh index.json. The prompt (fill_prompt.txt) is self-sufficient: its
REM first step re-runs gen_hot_topics.py, so it works even if the nightly
REM "Power.Talks Daily Refresh" hasn't scaffolded the day yet.
REM
REM Prerequisites: the logged-on user's Claude Code auth (this runs as that user),
REM internet access for web search. WAMP is NOT required to build the report.
REM Output (Claude's transcript) is logged under "Database Codes\logs\".

setlocal
cd /d "E:\wamp64\www\Power.Talks"
if not exist "Database Codes\logs" mkdir "Database Codes\logs"
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%t
set "LOG=Database Codes\logs\hot_topics_fill_%TS%.log"

type "Database Codes\hot_topics\fill_prompt.txt" | "C:\Users\chunl\.local\bin\claude.exe" -p ^
  --model sonnet ^
  --permission-mode acceptEdits ^
  --allowedTools Skill Read Write Edit Bash Glob Grep WebSearch WebFetch ^
  > "%LOG%" 2>&1

echo Hot Topics fill exited with %ERRORLEVEL%. Log: %LOG%
exit /b %ERRORLEVEL%
