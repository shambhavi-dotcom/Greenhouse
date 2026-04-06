# Quickstart: Run Frontend and Backend

## 1) Install dependencies

From the project root:

```bash
pip install -r requirements.txt
```

## 2) Run the frontend (web app)

Option A (direct):

```bash
streamlit run app.py
```

Option B (PowerShell helper):

```powershell
.\run_frontend.ps1
```

Option C (CMD helper):

```bat
run_frontend.bat
```

Open in browser:

```text
http://localhost:8501
```

## 3) Run the backend/CLI evaluation

```bash
python inference.py
```

This runs easy/medium/hard tasks and prints a grading report.

## Frontend usage (current behavior)

- Select mode: Dashboard, Single Episode, Batch Evaluation.
- Select difficulty: Easy, Medium, Hard.
- Select Crop Output in the left sidebar:
    - tomato
    - lettuce
    - herbs
    - cucumber
- In Single Episode:
    - one run executes all 4 crops,
    - table compares all crops,
    - charts show the crop selected in Crop Output.

## What to expect

- Features shown clearly: temperature, humidity, soil moisture, co2, light.
- Machine controls shown: fan, water sprinter, co2 emitter, light control.
- Mold is not shown in the app UI.
- Energy starts full and goes down with machine use only.

## Troubleshooting

Port busy:

```bash
streamlit run app.py --server.port=8502
```

Verify Streamlit install:

```bash
python -m streamlit --version
```
