@echo off
REM Power.Talks GALLERY chart routine - wrapper for Windows Task Scheduler.
REM
REM Separate from "Power.Talks Daily Refresh" (run_routine.bat, 1 AM) on
REM purpose: this routine reads thousands of PDFs and spends its own AI
REM budget, so it must not share a window with the nightly refresh.
REM
REM Exit codes: 0 every step succeeded, 1 a step failed, 2 the AI subscription
REM window was used up and the remaining documents were left for the next run
REM (see the per-run log under "Documents Database\GALLERY\routine_log\").

setlocal
cd /d "E:\wamp64\www\Power.Talks"
py -3 "Database Codes\download_GALLERY_charts\run_gallery_routine.py" %*
exit /b %ERRORLEVEL%
