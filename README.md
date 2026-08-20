# PMP — Project Management System

A simple Django app for tracking projects and tasks on a kanban-style board.

## Features

- Projects with descriptions
- Tasks per project with status (To Do / In Progress / Done), assignee, and due date
- Kanban board view per project
- Django admin for managing everything

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` for the project list, or `/admin/` for the admin site.

## Project structure

- `config/` — Django project settings and root URLs
- `projects/` — app with `Project` and `Task` models, views, and URLs
- `templates/` — HTML templates
