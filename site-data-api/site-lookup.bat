@echo off
REM Site Data Lookup - Quick Windows command
REM Usage: site-lookup "123 Main St, Miami, FL 33130"

python "%~dp0site_data.py" %*
