@echo off
echo.
echo ========================================
echo  TESTING DROP ZONE SYSTEM
echo ========================================
echo.

echo Creating test request file...
echo Create a Revit tool that counts all doors in the model > test_request.txt

echo.
echo Dropping file into code generator zone...
copy test_request.txt "D:\claude-code-revit\revit_zones\code_generator\"

echo.
echo File dropped! The monitor will process it.
echo Check: D:\claude-code-revit\revit_zones\code_generator\processed\
echo.
pause