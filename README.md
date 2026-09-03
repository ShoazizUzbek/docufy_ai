# Docufy AI

Enterprise AI Document Intelligence Platform — upload documents, process them
(OCR + text extraction + chunking), ask questions and get AI answers with
citations back to the exact source page/section.

## Stack

- **Backend**: Django + Django REST Framework, PostgreSQL, Celery + Redis, MinIO (S3-compatible storage), Qdrant (vector DB)
- **Frontend**: Next.js (App Router) + React + TypeScript + Tailwind CSS + shadcn/ui
- **OCR/parsing**: PyMuPDF/pdfplumber (digital PDFs), PaddleOCR (scanned files) — Phase 2
- **Embeddings**: BGE-M3 — Phase 3
- **LLM**: internal AI Gateway module, provider-agnostic — Phase 4

## Local dev setup

### 1. Infrastructure (Docker Compose)

Postgres, Redis, MinIO, and Qdrant run in Docker. The Django server, Celery
worker, and Next.js dev server run natively on the host for fast iteration.

```bash
docker compose up -d
```

This starts:
- Postgres on `localhost:5435` (remapped from 5432 to avoid clashing with a host Postgres install)
- Redis on `localhost:6380` (remapped from 6379)
- MinIO on `localhost:9000` (API) / `localhost:9001` (console, user `docufy_minio` / `docufy_minio_secret`)
- Qdrant on `localhost:6333`

### 2. Backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # defaults already match docker-compose.yml
python manage.py migrate
python manage.py seed_demo   # creates demo org, admin user, and MinIO bucket
python manage.py runserver
```

Demo login: `admin@docufy.ai` / `ChangeMe123!`

Run backend tests:

```bash
python manage.py test
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

Open http://localhost:3000 — you'll be redirected to `/login`.

## Phase 1 — Foundation

**What was built:**

- **Data model** (`core` app): `Organization` and a custom `User` model
  (email/password auth, `organization` FK, `role`), multi-tenant-ready even
  though the MVP seeds a single organization.
- **Auth**: JWT-based (`djangorestframework-simplejwt`) — `POST /api/auth/login/`
  returns access + refresh tokens and the current user; `POST /api/auth/refresh/`
  rotates the access token; `GET /api/auth/me/` returns the current user. The
  frontend stores tokens in `localStorage` and transparently refreshes on a
  401 (see `frontend/src/lib/api/client.ts`).
- **Document upload** (`documents` app): `POST /api/documents/` (multipart)
  validates the extension (PDF/DOCX/TXT/PNG/JPG/TIFF/BMP), streams the file to
  MinIO under `orgs/<org_id>/documents/<doc_id>/<filename>`, and creates a
  `Document` row (`status=UPLOADED`, scoped to the uploader's organization).
  `GET /api/documents/` lists the org's documents.
- **CORS**: configured via `django-cors-headers` for `localhost:3000`.
- **Frontend**: login page, and an authenticated shell (`Sidebar` / `TopBar` /
  `ContextPanel`) built from shared layout components and Tailwind design
  tokens matching the target visual language (near-white surfaces, hairline
  borders, single indigo accent, Inter for UI chrome). The Documents page
  supports drag-and-drop / click-to-upload and lists documents with a status
  badge; it polls while any document is `UPLOADED`/`PROCESSING` so it's ready
  to reflect Phase 2's pipeline once it lands. Search / Ask AI / Workflows /
  Analytics nav items are present but stubbed ("coming in Phase N") until
  their phases are built.

**How to test:**

1. Bring up infra + backend + frontend as above.
2. Backend: `python manage.py test` (10 tests covering user creation, login,
   `/me`, upload success/validation/org-scoping).
3. Frontend: `npm run build && npm run lint` (type-checks and lints clean).
4. Manual: visit http://localhost:3000, log in with the demo credentials,
   upload a PDF/DOCX/TXT/image from the Documents page, confirm it appears
   in the list with status `Uploaded`. Verify the file landed in MinIO:
   `docker exec docufy_ai-minio-1 mc ls --recursive local/docufy-documents`
   (after `docker exec docufy_ai-minio-1 mc alias set local http://localhost:9000 docufy_minio docufy_minio_secret`).
