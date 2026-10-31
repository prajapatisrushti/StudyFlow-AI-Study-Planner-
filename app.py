import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "studyflow.db"

st.set_page_config(page_title="StudyFlow | AI Study Planner", page_icon="📘", layout="wide")

# ---------- Database ----------
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT DEFAULT '#5B8DEF',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject_id INTEGER,
            due_date TEXT,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'Pending',
            estimated_minutes INTEGER DEFAULT 30,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER,
            exam_name TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            notes TEXT DEFAULT '',
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER,
            session_date TEXT NOT NULL,
            minutes INTEGER NOT NULL,
            notes TEXT DEFAULT '',
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS weekly_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_date TEXT NOT NULL,
            subject_id INTEGER,
            activity TEXT NOT NULL,
            minutes INTEGER DEFAULT 60,
            FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE SET NULL
        );
        """)
        count = conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0]
        if count == 0:
            conn.executemany("INSERT INTO subjects(name,color) VALUES(?,?)", [
                ("Computer Networks", "#5B8DEF"),
                ("Machine Learning", "#8B6CE8"),
                ("Database Management", "#19A58C"),
            ])

def query_df(sql, params=()):
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params)

def execute(sql, params=()):
    with get_connection() as conn:
        conn.execute(sql, params)
        conn.commit()

def subjects_df():
    return query_df("SELECT id, name, color FROM subjects ORDER BY name")

def subject_options():
    df = subjects_df()
    return {row["name"]: int(row["id"]) for _, row in df.iterrows()}

init_db()

# ---------- Styling ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #F5F7FC; }
.block-container { padding-top: 1.8rem; padding-bottom: 3rem; max-width: 1450px; }
[data-testid="stSidebar"] { background: #101B3C; }
[data-testid="stSidebar"] * { color: #F5F7FF !important; }
.hero { background: linear-gradient(120deg,#172B59,#3159A8); padding: 26px 30px; border-radius: 18px; color: white; margin-bottom: 22px; }
.hero h1 { color: white; margin: 0; font-size: 2rem; }
.hero p { color: #DCE6FF; margin: 8px 0 0 0; }
.metric-card { background: white; border: 1px solid #E8ECF5; padding: 18px; border-radius: 15px; }
.small-muted { color: #78839B; font-size: .9rem; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 📘 StudyFlow")
    st.caption("Plan smarter. Learn better.")
    page = st.radio("NAVIGATION", ["Dashboard", "My Subjects", "Study Tasks", "Exam Planner", "Weekly Planner", "Progress Analytics"])
    st.divider()
    st.caption("Your study space, all in one place.")

# ---------- Helpers ----------
def subject_name_map():
    return subject_options()

def subject_label(subject_id):
    if pd.isna(subject_id):
        return "Unassigned"
    df = subjects_df()
    found = df[df.id == int(subject_id)]
    return found.iloc[0]["name"] if not found.empty else "Unassigned"

def header(title, subtitle):
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)

def add_subject_select(label="Subject", key=None):
    opts = subject_name_map()
    names = ["Unassigned"] + list(opts.keys())
    selected = st.selectbox(label, names, key=key)
    return None if selected == "Unassigned" else opts[selected]

def task_frame():
    df = query_df("""
        SELECT tasks.*, subjects.name AS subject_name
        FROM tasks LEFT JOIN subjects ON tasks.subject_id = subjects.id
        ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, due_date
    """)
    return df

# ---------- Dashboard ----------
if page == "Dashboard":
    header("Good to see you! 👋", f"Your learning journey at a glance · {date.today().strftime('%A, %d %B %Y')}")
    tasks = task_frame()
    exams = query_df("SELECT * FROM exams ORDER BY exam_date")
    sessions = query_df("SELECT * FROM study_sessions")
    total_tasks = len(tasks)
    completed = int((tasks.status == "Completed").sum()) if total_tasks else 0
    pending = total_tasks - completed
    minutes = int(sessions.minutes.sum()) if not sessions.empty else 0
    c1,c2,c3,c4 = st.columns(4)
    for col, label, value, icon in [
        (c1,"Tasks completed",f"{completed}/{total_tasks}","✅"),
        (c2,"Pending tasks",str(pending),"📝"),
        (c3,"Study time",f"{minutes//60}h {minutes%60}m","⏱️"),
        (c4,"Upcoming exams",str(len(exams[exams.exam_date >= date.today().isoformat()])) if not exams.empty else "0","🎯")
    ]:
        with col:
            st.markdown(f'<div class="metric-card"><div class="small-muted">{icon} {label}</div><h2>{value}</h2></div>', unsafe_allow_html=True)
    st.write("")
    left, right = st.columns([1.25,1])
    with left:
        st.subheader("Your task overview")
        if tasks.empty:
            st.info("No tasks yet. Add your first task in **Study Tasks**.")
        else:
            chart = tasks.status.value_counts().rename_axis("Status").reset_index(name="Tasks")
            st.plotly_chart(px.pie(chart, names="Status", values="Tasks", hole=.62), use_container_width=True)
    with right:
        st.subheader("Next exams")
        upcoming = exams[exams.exam_date >= date.today().isoformat()].head(5) if not exams.empty else exams
        if upcoming.empty:
            st.info("No upcoming exams. Add one in Exam Planner.")
        else:
            for _, exam in upcoming.iterrows():
                days = (date.fromisoformat(exam.exam_date) - date.today()).days
                st.markdown(f"**{exam.exam_name}**  \n{subject_label(exam.subject_id)} · {exam.exam_date} · **{days} days left**")
                st.divider()
    st.subheader("Smart study suggestion")
    pending_df = tasks[tasks.status != "Completed"] if not tasks.empty else tasks
    if not pending_df.empty:
        high = pending_df[pending_df.priority == "High"]
        suggestion = high.iloc[0] if not high.empty else pending_df.iloc[0]
        st.success(f"Start with **{suggestion.title}** ({suggestion.priority.lower()} priority). Try one focused 25-minute session, then take a 5-minute break.")
    else:
        st.success("You're all caught up! Add a task or log a study session to keep building your progress.")

# ---------- Subjects ----------
elif page == "My Subjects":
    header("My Subjects", "Organise the topics you're learning.")
    with st.expander("＋ Add a new subject", expanded=False):
        with st.form("add_subject_form"):
            name = st.text_input("Subject name", placeholder="e.g. Artificial Intelligence")
            color = st.color_picker("Choose a colour", "#5B8DEF")
            submitted = st.form_submit_button("Add subject", type="primary")
            if submitted:
                if not name.strip():
                    st.error("Please enter a subject name.")
                else:
                    try:
                        execute("INSERT INTO subjects(name,color) VALUES(?,?)", (name.strip(), color))
                        st.success("Subject added!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("That subject already exists.")
    df = subjects_df()
    if df.empty:
        st.info("No subjects added yet.")
    else:
        cols = st.columns(3)
        for i, (_, row) in enumerate(df.iterrows()):
            with cols[i % 3]:
                st.markdown(f'<div class="metric-card"><h3>{row["name"]}</h3><p class="small-muted">Your subject workspace</p></div>', unsafe_allow_html=True)
                if st.button("Delete subject", key=f"del_sub_{row['id']}"):
                    execute("DELETE FROM subjects WHERE id=?", (int(row["id"]),))
                    st.rerun()

# ---------- Tasks ----------
elif page == "Study Tasks":
    header("Study Tasks", "Break big goals into small, achievable steps.")
    with st.form("task_form", clear_on_submit=True):
        title = st.text_input("Task title", placeholder="e.g. Revise supervised learning")
        a,b,c = st.columns(3)
        with a:
            sid = add_subject_select()
        with b:
            due = st.date_input("Due date", value=date.today() + timedelta(days=1))
        with c:
            priority = st.selectbox("Priority", ["High","Medium","Low"], index=1)
        estimate = st.number_input("Estimated time (minutes)", min_value=5, max_value=600, value=30, step=5)
        if st.form_submit_button("＋ Add task", type="primary"):
            if title.strip():
                execute("INSERT INTO tasks(title,subject_id,due_date,priority,estimated_minutes) VALUES(?,?,?,?,?)",
                        (title.strip(), sid, due.isoformat(), priority, int(estimate)))
                st.success("Task added!")
                st.rerun()
            else:
                st.error("Enter a task title.")
    st.divider()
    df = task_frame()
    if df.empty:
        st.info("Your task list is empty. Add your first task above.")
    else:
        f1,f2 = st.columns(2)
        with f1:
            status_filter = st.selectbox("Filter by status", ["All","Pending","In Progress","Completed"])
        with f2:
            priority_filter = st.selectbox("Filter by priority", ["All","High","Medium","Low"])
        view = df.copy()
        if status_filter != "All": view = view[view.status == status_filter]
        if priority_filter != "All": view = view[view.priority == priority_filter]
        for _, task in view.iterrows():
            with st.container(border=True):
                x,y,z = st.columns([4,2,1])
                with x:
                    st.markdown(f"**{task.title}**")
                    st.caption(f"{task.subject_name or 'Unassigned'} · Due {task.due_date or 'No date'} · {task.priority} priority · {task.estimated_minutes} min")
                with y:
                    new_status = st.selectbox("Status", ["Pending","In Progress","Completed"],
                                              index=["Pending","In Progress","Completed"].index(task.status),
                                              key=f"status_{task.id}", label_visibility="collapsed")
                    if new_status != task.status:
                        execute("UPDATE tasks SET status=? WHERE id=?", (new_status, int(task.id)))
                        st.rerun()
                with z:
                    if st.button("🗑️", key=f"delete_task_{task.id}", help="Delete task"):
                        execute("DELETE FROM tasks WHERE id=?", (int(task.id),))
                        st.rerun()

# ---------- Exams ----------
elif page == "Exam Planner":
    header("Exam Planner", "Keep every important exam date in one place.")
    with st.form("exam_form", clear_on_submit=True):
        exam_name = st.text_input("Exam name", placeholder="e.g. Machine Learning Semester Exam")
        a,b = st.columns(2)
        with a: sid = add_subject_select()
        with b: exam_date = st.date_input("Exam date", value=date.today() + timedelta(days=7))
        notes = st.text_area("Notes / topics to cover", placeholder="Units, chapters, important topics...")
        if st.form_submit_button("Add exam", type="primary"):
            if exam_name.strip():
                execute("INSERT INTO exams(subject_id,exam_name,exam_date,notes) VALUES(?,?,?,?)",
                        (sid, exam_name.strip(), exam_date.isoformat(), notes.strip()))
                st.success("Exam added!")
                st.rerun()
            else: st.error("Enter an exam name.")
    exams = query_df("SELECT * FROM exams ORDER BY exam_date")
    if not exams.empty:
        st.subheader("Your exam calendar")
        for _, exam in exams.iterrows():
            days = (date.fromisoformat(exam.exam_date) - date.today()).days
            with st.container(border=True):
                st.markdown(f"**{exam.exam_name}** · {subject_label(exam.subject_id)}")
                st.write(f"📅 {exam.exam_date}  |  {'Today!' if days == 0 else (f'{days} days left' if days > 0 else f'{abs(days)} days ago')}")
                if exam.notes: st.caption(exam.notes)
                if st.button("Delete exam", key=f"del_exam_{exam.id}"):
                    execute("DELETE FROM exams WHERE id=?", (int(exam.id),))
                    st.rerun()
    else:
        st.info("No exams added yet.")

# ---------- Weekly Planner ----------
elif page == "Weekly Planner":
    header("Weekly Planner", "Give your week a realistic study rhythm.")
    with st.form("weekly_form", clear_on_submit=True):
        a,b = st.columns(2)
        with a: plan_day = st.date_input("Study date", value=date.today())
        with b: sid = add_subject_select()
        activity = st.text_input("What will you work on?", placeholder="e.g. Revise Unit 2 and solve questions")
        mins = st.number_input("Duration (minutes)", min_value=10, max_value=600, value=60, step=10)
        if st.form_submit_button("Add to weekly plan", type="primary"):
            if activity.strip():
                execute("INSERT INTO weekly_plan(plan_date,subject_id,activity,minutes) VALUES(?,?,?,?)",
                        (plan_day.isoformat(), sid, activity.strip(), int(mins)))
                st.success("Added to your plan!")
                st.rerun()
            else: st.error("Enter an activity.")
    start = date.today() - timedelta(days=date.today().weekday())
    end = start + timedelta(days=6)
    plan = query_df("SELECT * FROM weekly_plan WHERE plan_date BETWEEN ? AND ? ORDER BY plan_date",
                    (start.isoformat(), end.isoformat()))
    st.subheader(f"This week · {start.strftime('%d %b')} – {end.strftime('%d %b')}")
    for offset in range(7):
        day = start + timedelta(days=offset)
        day_items = plan[plan.plan_date == day.isoformat()] if not plan.empty else plan
        with st.expander(f"{day.strftime('%A, %d %b')} · {len(day_items)} planned activities", expanded=(day == date.today())):
            if day_items.empty:
                st.caption("Nothing planned yet.")
            else:
                for _, item in day_items.iterrows():
                    st.write(f"• **{item.activity}** — {subject_label(item.subject_id)} · {item.minutes} min")
                    if st.button("Remove", key=f"remove_plan_{item.id}"):
                        execute("DELETE FROM weekly_plan WHERE id=?", (int(item.id),))
                        st.rerun()

# ---------- Analytics ----------
elif page == "Progress Analytics":
    header("Progress Analytics", "See your consistency and celebrate your progress.")
    sessions = query_df("SELECT * FROM study_sessions ORDER BY session_date")
    tasks = task_frame()
    done = int((tasks.status == "Completed").sum()) if not tasks.empty else 0
    total = len(tasks)
    a,b,c = st.columns(3)
    a.metric("Tasks completed", done)
    b.metric("Completion rate", f"{(done/total*100):.0f}%" if total else "0%")
    c.metric("Total study hours", f"{sessions.minutes.sum()/60:.1f}" if not sessions.empty else "0.0")
    st.subheader("Log a study session")
    with st.form("session_form", clear_on_submit=True):
        x,y,z = st.columns(3)
        with x: sid = add_subject_select()
        with y: session_day = st.date_input("Date", value=date.today())
        with z: session_minutes = st.number_input("Minutes studied", min_value=5, max_value=720, value=30, step=5)
        session_notes = st.text_input("What did you study? (optional)")
        if st.form_submit_button("Save study session", type="primary"):
            execute("INSERT INTO study_sessions(subject_id,session_date,minutes,notes) VALUES(?,?,?,?)",
                    (sid, session_day.isoformat(), int(session_minutes), session_notes.strip()))
            st.success("Study session saved!")
            st.rerun()
    sessions = query_df("SELECT * FROM study_sessions ORDER BY session_date")
    if not sessions.empty:
        sessions["date"] = pd.to_datetime(sessions.session_date)
        daily = sessions.groupby("date", as_index=False).minutes.sum()
        st.subheader("Study time over time")
        st.plotly_chart(px.bar(daily, x="date", y="minutes", labels={"date":"Date","minutes":"Minutes studied"}), use_container_width=True)
        by_subject = sessions.assign(subject=sessions.subject_id.apply(subject_label)).groupby("subject", as_index=False).minutes.sum()
        st.subheader("Study time by subject")
        st.plotly_chart(px.pie(by_subject, names="subject", values="minutes", hole=.5), use_container_width=True)
    else:
        st.info("Log your first study session to unlock your analytics.")
    if not tasks.empty:
        st.subheader("Task completion")
        status_counts = tasks.status.value_counts().rename_axis("Status").reset_index(name="Tasks")
        st.plotly_chart(px.bar(status_counts, x="Status", y="Tasks", color="Status"), use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.caption("StudyFlow · Built to help you stay consistent 💙")
