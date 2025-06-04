@echo off
echo ====================================
echo AI File Assistant Setup
echo ====================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

REM Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

REM Compile C program
echo.
echo Compiling C program...
gcc -o file_lister.exe file_lister.c -ladvapi32
if errorlevel 1 (
    echo ERROR: Failed to compile. Install MinGW or Visual Studio.
    pause
    exit /b 1
)

REM Test services
echo.
echo Testing AI services...
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ Deepgram:', 'OK' if os.getenv('DEEPGRAM_API_KEY') else 'MISSING')"
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ ElevenLabs:', 'OK' if os.getenv('ELEVEN_LABS_API_KEY') else 'MISSING')"
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ Gemini:', 'OK' if os.getenv('GEMINI_API_KEY') else 'MISSING')"
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✅ LiveKit:', 'OK' if os.getenv('LIVEKIT_URL') else 'MISSING')"

echo.
echo ✅ Setup complete!
echo.
echo Run: streamlit run app.py
echo.
pause