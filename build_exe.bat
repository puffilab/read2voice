@echo off
setlocal

echo [1/3] Installing dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed.
  exit /b 1
)

echo [2/3] Building EXE...
python -m PyInstaller --noconfirm --onefile --windowed --name EpubReaderTTS epub_reader_tts.py
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo [3/3] Done.
echo EXE path: dist\EpubReaderTTS.exe
endlocal
