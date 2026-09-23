# Smart College Complaint & Resolution System

A full-stack DBMS mini-project: a web platform where students submit and track
campus complaints, and admins manage, assign, and resolve them — backed by a
real MySQL database with proper keys, relationships, and JOIN-driven reporting.

**Stack:** Flask (Python) · MySQL · Bootstrap 5 · Chart.js · Font Awesome

## Features

- Student registration/login and a separate admin login, both session-based
  with hashed passwords (`werkzeug.security`, scrypt) — no plain-text passwords
- Complaint submission, editing, deletion, search, filtering, and sorting
- A live status timeline (Submitted → Assigned → In Progress → Resolved → Closed)
- Student dashboard with Chart.js status/priority charts, driven by real `GROUP BY` queries
- Admin dashboard with 4 charts (status, category, department, 6-month trend) and stat cards
- Admin tools to assign staff, change status/priority, record resolutions, and manage staff/departments
- Row-level access control: students can only ever see their own complaints
- Parameterized queries throughout (SQL-injection safe)
- 41 automated tests covering registration, login, complaint CRUD, search/filter, admin actions, and access control

## Project Structure

```
SmartCollegeComplaint/
├── app.py                  # All Flask routes
├── database.py             # Connection pooling + query helpers
├── auth.py                 # Login decorators + form validation
├── config.py                # Reads MySQL credentials from .env
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # + pytest, for running tests/
├── .env.example
├── database/database.sql     # Full schema + seed data
├── templates/                 # Jinja2 pages
├── static/css/style.css       # Design system
├── static/js/script.js        # Password toggles, charts helpers, validation
└── tests/                     # pytest suite (41 tests)
```

See `ARCHITECTURE.md` for the ER diagram and design notes, `PROJECT_REPORT.md`
for the academic write-up (abstract, DFDs, SQL queries, future scope), and
`VIVA_PREP.md` for 25 DBMS viva questions with answers.

## Setup Instructions (Windows)

**Step 1 — Install Python**
Download and install Python 3.10+ from [python.org](https://www.python.org/downloads/).
During install, check "Add Python to PATH".

**Step 2 — Install MySQL**
Download and install MySQL Community Server from
[dev.mysql.com](https://dev.mysql.com/downloads/mysql/). Note the root password you set.

**Step 3 — Create the database**
Open MySQL Command Line Client (or MySQL Workbench) and run:
```
mysql -u root -p
```

**Step 4 — Run database.sql**
From the project folder, in a normal Command Prompt:
```
mysql -u root -p < database\database.sql
```
This drops/recreates `smart_college_complaint` with all tables and seed data
(8 departments, 2 sample staff, 1 default admin).

**Step 5 — Install dependencies**
```
cd SmartCollegeComplaint
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Step 6 — Configure MySQL credentials**
```
copy .env.example .env
```
Then open `.env` in a text editor and set `MYSQL_PASSWORD` to your MySQL root
password (and `SECRET_KEY` to any random string).

**Step 7 — Run Flask**
```
python app.py
```

**Step 8 — Open the website**
Visit **http://localhost:5000** in your browser.

**If you get a MySQL "Access denied" error at this point:** visit
**http://localhost:5000/config-check** first — it tells you whether `.env`
was actually found and whether a password loaded from it. The #1 cause is
`.env` getting saved as `.env.txt` by a text editor, or being in the wrong
folder. `.env` must sit directly next to `app.py`.

**Step 9 — Log in**
All three seeded accounts work immediately — no manual password reset needed:

| Role | URL | Email | Password |
|---|---|---|---|
| Student | `/login` | `student@college.edu` | `Student@123` |
| Staff | `/staff/login` | `ramesh.staff@college.edu` | `Staff@123` |
| Staff | `/staff/login` | `sunita.staff@college.edu` | `Staff@123` |
| Admin | `/admin/login` | `admin@college.edu` | `Admin@123` |

Or register your own new student account from `/register`. **Change these
default passwords** (or delete the seed rows) before submitting/deploying
anywhere beyond your own machine.

## Adding Your University Logo

Drop your logo file in as `static/images/logo.png` (already done if you used
the provided GHRISTU logo). It auto-displays in the navbar and footer at
40×40px — a square PNG with a transparent background, 160×160px or larger,
looks sharpest. If the file is missing, the site falls back to a plain icon
badge automatically instead of showing a broken image.

## Running Tests

```
pip install -r requirements-dev.txt
pytest tests/ -v
```

The suite uses an in-memory fake database layer (see `tests/conftest.py`), so
it runs without a live MySQL server. All 41 tests pass as of the last commit.

## Default Seed Data

| Table | Seed rows |
|---|---|
| `departments` | 8 (Computer Science, Electronics, Mechanical, Civil, Administration, Hostel, Library, Transport) |
| `staff` | 2 (Ramesh Kumar, Sunita Rao — both password `Staff@123`) |
| `admins` | 1 (`admin@college.edu` / `Admin@123`) |
| `students` | 1 demo account (`student@college.edu` / `Student@123`) |
| `complaints` | 4 sample complaints (varied status/priority/category) so dashboards and charts aren't empty on first run |
| `resolutions` | 1 sample resolution, linked to a resolved complaint |

