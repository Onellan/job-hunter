# Job-Hunter Project Rules

## Mission

Build the best self-hosted job aggregation platform.

The application must be lightweight enough to run comfortably on a Raspberry Pi 4 Model B with 1 GB RAM.

Performance and maintainability are more important than feature count.

---

# Architecture

Follow Clean Architecture.

Never mix layers.

Presentation Layer

↓

Application Layer

↓

Domain Layer

↓

Infrastructure Layer

Dependencies always point inward.

---

# Technology Stack

Backend

- Python 3.12+
- FastAPI
- SQLModel
- SQLite
- APScheduler

Frontend

- Jinja2
- HTMX
- PicoCSS

Scraping

- Playwright
- JobSpy
- BeautifulSoup

Testing

- pytest

Deployment

- Docker Compose

---

# Never Use

React

Angular

Vue

Node.js

Redis

RabbitMQ

Celery

Microservices

Kubernetes

Heavy JavaScript frameworks

---

# Code Standards

Everything must be

- Type hinted
- Tested
- Documented

No duplicated code.

No circular imports.

No giant classes.

No giant functions.

Maximum function size

≈50 lines

Maximum file size

≈500 lines

Split modules before they become difficult to navigate.

---

# Database Rules

Providers never write directly to SQLite.

Only repositories may access the database.

Never write SQL inside API routes.

---

# Providers

Every provider must implement BaseProvider.

Providers return only standardized Job models.

Providers must never know about:

SQLite

Exporters

UI

Scheduler

---

# API Rules

Routes must be thin.

Business logic belongs in services.

Validation belongs in models.

---

# UI Rules

Render server-side.

Prefer HTMX over JavaScript.

Avoid page reloads.

No SPA framework.

---

# CSS

Use PicoCSS.

No Bootstrap.

No Tailwind.

Minimal custom CSS.

---

# Performance Goals

Idle memory

<100 MB

Dashboard

<1 second

Database

Indexed

Lazy loading

Pagination

---

# Naming

Use meaningful names.

Never abbreviate unless common.

Good

job_provider.py

Bad

jp.py

---

# Documentation

Every public class

Every public function

Every provider

Every service

must have docstrings.

---

# Logging

Structured logging only.

Never print().

---

# Testing

Every new feature requires tests.

Bug fixes require regression tests.

---

# Git

Small commits.

Meaningful messages.

Never commit broken code.

---

# AI Rules

Before generating code:

Understand the architecture.

Search for existing implementations.

Reuse existing code where possible.

Avoid duplication.

Prefer composition over inheritance.

Always explain architectural decisions.

Never introduce unnecessary dependencies.

When unsure:

Ask before implementing.
