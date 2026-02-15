@echo off
set FFMPEG="C:\Program Files\ffmpeg-2025-03-20-git-76f09ab647-full_build\bin\ffmpeg.exe"
set OUTPUT=%1
set OFFSET_X=%2
set OFFSET_Y=%3
set WIDTH=%4
set HEIGHT=%5
%FFMPEG% -f gdigrab -framerate 30 -offset_x %OFFSET_X% -offset_y %OFFSET_Y% -video_size %WIDTH%x%HEIGHT% -i desktop -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -y %OUTPUT%
