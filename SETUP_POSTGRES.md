# 🔥 Forest Fire Detection — PostgreSQL Setup Guide

## What Was Changed

### 1. Backend `.env` (PostgreSQL connection)
File: `backend/.env`
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/forest_fire_db
```
**Edit this** if your Postgres username/password/database name is different.

### 2. Frontend `.env.local`
File: `frontend/.env.local`
```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

### 3. Node Server `.env`
File: `server/.env` — for the Express/pg users API (port 5001).

### 4. `asyncpg` added to requirements
The FastAPI backend uses SQLAlchemy async with `asyncpg` driver (added to `requirements.txt`).

### 5. Role selection on Register page
Users can now pick their role during registration:
- 👁 **Viewer** — read-only access
- 🌲 **Forest Officer** — upload images, run detections
- 🚨 **Emergency Response Officer** — predictions + alerts
- 🧪 **Research Analyst** — spatial analysis + reports

### 6. Backend enforces role on registration
`user_service.py` now reads the `role` field and assigns the matching DB role.
`Super Admin` can never be self-assigned (falls back to Viewer).

---

## Setup Steps

### Step 1 — Create the PostgreSQL database

```bash
psql -U postgres
CREATE DATABASE forest_fire_db;
\q
```

### Step 2 — Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 3 — Start the FastAPI backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

On first start, the server will:
- Auto-create all tables (users, roles, permissions, etc.)
- Seed 5 default roles with permissions
- Seed a default Super Admin: `admin` / `SuperSecurePassword123!`

### Step 4 — Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:3000

### Step 5 — (Optional) Seed Node server sample data

```bash
cd server
npm install
npm run db:seed    # creates users table + 3 sample users
npm run dev        # starts Express API on port 5001
```

---

## Roles Available

| Role | Permissions |
|------|-------------|
| Super Admin | Everything |
| Forest Officer | Upload images, predictions, alerts |
| Emergency Response Officer | Predictions, reports, alerts |
| Research Analyst | Predictions, reports, spatial analysis |
| Viewer | Predictions, reports (read-only) |

---

## Troubleshooting

**"asyncpg not found"**
```bash
pip install asyncpg
```

**"Database does not exist"**
```bash
psql -U postgres -c "CREATE DATABASE forest_fire_db;"
```

**"Connection refused"**
Make sure PostgreSQL is running:
```bash
# macOS
brew services start postgresql

# Linux
sudo systemctl start postgresql

# Windows
net start postgresql
```

**Change DB credentials**
Edit `backend/.env`:
```
DATABASE_URL=postgresql+asyncpg://YOUR_USER:YOUR_PASSWORD@localhost:5432/forest_fire_db
```
