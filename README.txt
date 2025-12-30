Habit Tracker (Streamlit)

A small habit tracker that runs locally in your browser.ÊIt stores everything in a local SQLite database.

Features
* Create habits with a schedule (daily / weekdays / custom days)
* Check in habits for any date
* Streaks and success rate per habit
* A simple ÒtodayÓ view with whatÕs due

Requirements
* Python 3.10+

Setup -> I was unable to upload the venv here, so a new one needs to be created locally when downloading this repo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run Habit_Tracker.py

Run the app
streamlit run Habit_Tracker.py

Data
The database lives in:
* data/habits.db

If you want a clean start,Êclose the app and delete that file.

