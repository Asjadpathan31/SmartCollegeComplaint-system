# Smart College Complaint & Resolution System

A Flask and MySQL academic project prototype for student, staff and administrator complaint workflows.

## Current repository status

**This repository is incomplete as currently published.** The current root contains the Flask application modules (`app.py`, `auth.py`, `config.py`, and `database.py`), dependency files, `ARCHITECTURE.md`, and `.env.example`.

The application code references template files, static assets and a MySQL schema that are not present in the current repository tree. The README from an earlier version also described a test suite and project folders that are not currently checked in. Therefore, do not assume the app can be launched from a fresh clone or that automated tests are available until those files are restored and verified.

## Technology visible in the source

- Python and Flask
- MySQL Connector with connection pooling
- Werkzeug password hashing and Flask sessions
- Environment-based configuration via `.env`

## Security setup

1. Create a local environment file:
   ```bash
   cp .env.example .env
   ```
   On Windows Command Prompt:
   ```bat
   copy .env.example .env
   ```
2. Set your own MySQL credentials and a strong, random Flask secret key in `.env`.
3. Never commit `.env` or real credentials. The repository ignores local environment files; only `.env.example` should be committed.

**Security notice:** an environment file was previously committed to this public repository and has since been removed from the current branch. Removing it from the latest commit does not erase it from Git history. Rotate any credentials that may have been stored in that file before using them again.

## What needs restoring before a runnable release

- The templates referenced by `render_template()`
- The static CSS, JavaScript and image assets
- The SQL schema and seed data referenced by the original setup guide
- A real automated test suite, if tests are intended to be part of the project

After restoring these files, validate the setup from a clean clone and update this README with the verified commands and test results.

## Author

Asjad Pathan · [GitHub](https://github.com/Asjadpathan31) · [Portfolio](https://asjadpathan31.github.io/portfolio/)
