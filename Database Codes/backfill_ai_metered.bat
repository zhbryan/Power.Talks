@echo off
REM ============================================================================
REM Power.Talks — ONE-OFF AI summary backfill on the METERED Anthropic API.
REM
REM Rebuilds ALL Market-Rules executive summaries + stakeholder sections using
REM the paid API (POWERTALKS_AI_BACKEND=api) with a full rebuild forced
REM (POWERTALKS_FORCE_ALL=1). Runs every category sequentially so the ~32k-token
REM ERCOT glossary prompt stays in the 5-minute prompt cache the whole run
REM (cache reads are 10x cheaper than fresh input) — do NOT parallelize.
REM
REM This is intentionally separate from the nightly refresh, which now defaults
REM to the Claude subscription (POWERTALKS_AI_BACKEND=cli). Run this by hand once.
REM Each script prints its own AI token/cost total at the end; see the log.
REM ============================================================================
setlocal
cd /d "E:\wamp64\www\Power.Talks\Database Codes\summarize_MKT_Rules"

set "POWERTALKS_AI_BACKEND=api"
set "POWERTALKS_FORCE_ALL=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

if not exist "..\logs" mkdir "..\logs"
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%t
set "LOG=..\logs\backfill_ai_metered_%TS%.log"

echo ================================================================ > "%LOG%"
echo Power.Talks AI backfill (metered API, full rebuild) >> "%LOG%"
echo Started: %DATE% %TIME% >> "%LOG%"
echo ================================================================ >> "%LOG%"

for %%C in (nprr nogrr pgrr rmgrr scr copmgrr) do (
  echo. >> "%LOG%"
  echo === SUMMARIZE %%C ================================================ >> "%LOG%"
  py -3 "summarize_ercot_%%C.py" >> "%LOG%" 2>&1
)

for %%C in (NPRR NOGRR PGRR RMGRR SCR COPMGRR) do (
  echo. >> "%LOG%"
  echo === STAKEHOLDER SECTIONS %%C ==================================== >> "%LOG%"
  py -3 "gen_stakeholder_sections.py" %%C --all >> "%LOG%" 2>&1
)

echo. >> "%LOG%"
echo ================================================================ >> "%LOG%"
echo Finished: %DATE% %TIME% >> "%LOG%"
echo ================================================================ >> "%LOG%"
echo Backfill complete. Log: %LOG%
exit /b 0
