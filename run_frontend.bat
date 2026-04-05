@echo off
REM Start Streamlit frontend for greenhouse environment
REM Opens at http://localhost:8501

echo.
echo Starting Greenhouse Web Interface...
echo http://localhost:8501
echo.
echo Press Ctrl+C to stop the server.
echo.

cd /d "%~dp0"
streamlit run app.py
