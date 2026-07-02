@echo off
REM Power.Talks refresh routine — wrapper for Windows Task Scheduler.
REM Runs the full pipeline (download -> profile -> summarize -> web data ->
REM rebuild) for both Market Rules and Stakeholder Meetings.
REM
REM Exit code is 0 when every step succeeded, 1 if any step failed (see the
REM per-run log under "Database Codes\logs\").

setlocal
cd /d "E:\wamp64\www\Power.Talks"
py -3 "Database Codes\run_routine.py" %*
exit /b %ERRORLEVEL%
