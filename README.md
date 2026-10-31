# StudyFlow – AI Study Planner

A fresh Streamlit study-planning app with a local SQLite database.

## Features
- Dashboard with task, study-time and exam summaries
- Subject management
- Study task tracking with priorities and statuses
- Exam planner with countdowns
- Weekly study planner
- Progress analytics with Plotly charts
- Local SQLite persistence

The initial "smart study suggestion" uses simple rules and does not require an API key.

## Run on Windows (PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser. Your data is stored locally in `studyflow.db`.
