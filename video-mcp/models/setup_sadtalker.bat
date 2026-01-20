@echo off
echo ============================================
echo SadTalker Setup Script
echo ============================================
echo.

cd /d D:\_CLAUDE-TOOLS\video-mcp\models\SadTalker

echo [1/4] Creating Python virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

echo.
echo [2/4] Installing PyTorch with CUDA 11.8...
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2+cu118 --index-url https://download.pytorch.org/whl/cu118

echo.
echo [3/4] Installing SadTalker requirements...
pip install -r requirements.txt
pip install dlib-bin

echo.
echo [4/4] Downloading pretrained models...
echo This may take a while (several GB of models)...

if not exist "checkpoints" mkdir checkpoints
if not exist "gfpgan\weights" mkdir gfpgan\weights

echo Downloading face models...
curl -L -o checkpoints/mapping_00109-model.pth.tar "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00109-model.pth.tar"
curl -L -o checkpoints/mapping_00229-model.pth.tar "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00229-model.pth.tar"
curl -L -o checkpoints/SadTalker_V0.0.2_256.safetensors "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_256.safetensors"
curl -L -o checkpoints/SadTalker_V0.0.2_512.safetensors "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_512.safetensors"

echo Downloading GFPGAN (face enhancement)...
curl -L -o gfpgan/weights/detection_Resnet50_Final.pth "https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth"
curl -L -o gfpgan/weights/parsing_parsenet.pth "https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth"

echo.
echo ============================================
echo Setup Complete!
echo ============================================
echo.
echo To test, run:
echo   cd D:\_CLAUDE-TOOLS\video-mcp\models\SadTalker
echo   venv\Scripts\activate
echo   python inference.py --driven_audio examples/driven_audio/bus_chinese.wav --source_image examples/source_image/full_body_1.png
echo.
pause
