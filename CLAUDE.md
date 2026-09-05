# Docufy AI

Enterprise AI Document Intelligence Platform (MVP, single organization).
Upload documents (PDF, DOCX, TXT, scanned images; Uzbek/Russian/English),
process them (OCR + text extraction + chunking), ask questions and get AI
answers with citations back to the exact source page/section.

## Tech stack

- **Backend**: Python, Django + Django REST Framework
- **Async/background jobs**: Celery + Redis
- **Database**: PostgreSQL
- **File storage**: MinIO (S3-compatible), via `django-storages`
- **Vector database**: Qdrant — Phase 3, one collection (`docufy_chunks`, 1024-dim cosine), payload-filtered by `organization_id` per query
- **OCR**: PyMuPDF first (digital PDFs with a text layer, via font-size heading heuristics), PaddleOCR fallback (scanned files/images) — Phase 2. `pdfplumber` was in the original stack list but turned out unnecessary — PyMuPDF alone covers text + font-size extraction; not installed.
- **Embeddings**: BGE-M3 (`BAAI/bge-m3` via `sentence-transformers`, 1024-dim, genuinely multilingual — one model handles the Uzbek/Russian/English mix, no per-language passes needed) — Phase 3
- **LLM**: internal AI Gateway module (`ai_gateway/`), provider-agnostic — `AI_GATEWAY_PROVIDER` switches between `anthropic` (Claude API) and `ollama` (local model — defaults to Qwen2.5, chosen over Gemma for its stronger Uzbek/Russian coverage) with no other code changes — Phase 4. Also powers Phase 6's document classification/entity extraction (`documents/processing/intelligence.py`) — same gateway, different prompt.
- **Frontend**: Next.js 16 (App Router) + React + TypeScript + Tailwind CSS v4 + shadcn/ui (shadcn here is built on **Base UI**, not Radix — component APIs differ: `delay` not `delayDuration`, no `asChild`, use the `render` prop instead)
- **Auth**: JWT (`djangorestframework-simplejwt`), tokens in `localStorage` on the frontend with transparent refresh-on-401

## Project structure

```
docufy_ai/
├── docufy_ai/            # Django project package (settings, urls, celery app)
├── core/                 # Organization + custom User model, JWT auth endpoints
├── documents/            # Document + Chunk models, upload endpoint, processing pipeline
│   ├── processing/        # blocks.py (heading/hierarchy), chunking.py, tokens.py,
│   │                       #   extractors.py (PDF/DOCX/TXT/image), ocr.py (PaddleOCR),
│   │                       #   embeddings.py (BGE-M3), vector_store.py (Qdrant),
│   │                       #   intelligence.py (classification + entities, Phase 6), pipeline.py
│   ├── tasks.py           # Celery task wrapping pipeline.process_document
│   ├── views.py           # DocumentViewSet — includes content/ action (chunks grouped by
│   │                       #   page) — Phase 5
│   └── tests/              # test_api.py, test_chunking.py, test_extractors.py, test_pipeline.py,
│                          #   test_embeddings.py, test_vector_store.py, test_intelligence.py
├── search/               # Semantic search endpoint (POST /api/search/) — Phase 3
├── ai_gateway/           # Provider-agnostic ai_chat() — anthropic_client.py, openai_compatible.py
│                          #   (also OllamaClient), factory.py, base.py. Plain package, not an
│                          #   installed Django app (no models) — Phase 4
├── ask_ai/               # RAG endpoint (POST /api/ask/) — rag.py has the retrieve+prompt+parse
│                          #   logic, accepts an optional document_id scope — Phase 4/5
├── requirements.txt
├── Dockerfile            # image shared by the backend + celery services
├── docker-compose.yml    # postgres, redis, minio, qdrant, backend, celery (frontend stays native)
├── .env.example          # backend env vars
├── manage.py
└── frontend/              # Next.js app
    ├── src/
    │   ├── app/
    │   │   ├── login/            # public
    │   │   └── (app)/            # authenticated route group (RequireAuth-guarded)
    │   │       ├── documents/
    │   │       │   └── [id]/     # Document Viewer — full render + metadata panel — Phase 5
    │   │       ├── search/       # semantic search UI — Phase 3
    │   │       ├── ask-ai/       # multi-turn conversation view — Phase 4
    │   │       ├── workflows/    # stub
    │   │       └── analytics/    # stub
    │   ├── components/
    │   │   ├── layout/           # Sidebar, TopBar, ContextPanel, AppShell, RequireAuth
    │   │   ├── documents/        # DocumentStatusBadge, CategoryBadge (Phase 6),
    │   │   │                     #   DocumentPassageViewer, AskAboutDocument — Phase 5
    │   │   ├── ask-ai/           # CitationChip, ConversationTurnCard — Phase 4
    │   │   └── ui/                # shadcn/ui primitives (Base UI-backed)
    │   ├── hooks/                # use-auth, use-context-panel, use-open-document-passage — Phase 5
    │   └── lib/
    │       ├── api/               # typed client.ts, tokens.ts, auth.ts, documents.ts, search.ts, ask-ai.ts, types.ts
    │       └── format.ts
    └── .env.example
```

## Design system (frontend)

Tokens live in [frontend/src/app/globals.css](frontend/src/app/globals.css) as CSS
variables wired into Tailwind v4's `@theme inline` block — **never hardcode these
values in a page; use the Tailwind utility classes** (`bg-background`,
`text-muted-foreground`, `border-border`, `bg-accent text-accent-foreground`, etc.)
so every screen stays consistent.

**Palette** (light only, no dark mode built):
| Token | Value | Use |
|---|---|---|
| `background` | `#fbfbfa` | page background |
| `sidebar` | `#f6f6f5` | sidebar background |
| `card` / `popover` | `#ffffff` | cards, panels, dropdowns |
| `border` | `#e6e5e2` | hairline borders (default) |
| `border-strong` / `input` | `#d8d7d3` | stronger borders, input borders, dashed dropzone |
| `foreground` | `#1c1c1a` | primary (near-black) text |
| `muted-foreground` | `#54534d` | secondary text |
| `tertiary-foreground` | `#8a8983` | tertiary/placeholder text |
| `primary` / `ring` / `sidebar-primary` | `oklch(0.42 0.11 261)` | the one accent — muted deep indigo. Active nav, primary buttons, focus rings, citation chip borders |
| `accent` / `sidebar-accent` | `oklch(0.94 0.02 261)` | accent-soft background — active nav item bg, citation chip bg, highlighted passage bg |
| `accent-foreground` | `oklch(0.42 0.11 261)` | text/icon on accent-soft backgrounds |

Rules: **no gradients, no drop shadows beyond a 1px border, no rounded-corner+left-accent-border card pattern.** Radius is intentionally modest (`--radius: 0.5rem`).

**Typography**: `Inter` (`font-sans`, default) for all UI chrome — nav, buttons,
labels, tables. `Source Serif 4` (`font-serif`) for long-form reading content
only — AI answer text (Phase 4) and document body text (Phase 5) — never UI
labels. Both loaded via `next/font/google` in [frontend/src/app/layout.tsx](frontend/src/app/layout.tsx)
with `latin` + `cyrillic` subsets (for Uzbek/Russian).

**Layout**: `AppShell` ([frontend/src/components/layout/app-shell.tsx](frontend/src/components/layout/app-shell.tsx))
composes `Sidebar` (~248px, collapsible to 64px; org switcher + primary nav +
Knowledge Spaces list) + `TopBar` (slim, cmd+K global search trigger) +
`<main>` (centered, `max-w-3xl`) + `ContextPanel` (collapsible right panel,
420px, opened via the `useContextPanel()` hook). All authenticated routes
live under the `(app)` route group and are wrapped in `RequireAuth`.

Citations render as small chips using `accent`/`accent-foreground` (border +
soft background) that call `useOpenDocumentPassage()` (wraps
`useContextPanel().open(...)`, Phase 5) to show the full document in the
`ContextPanel`, scrolled and highlighted to the cited passage. The Document
Viewer page (`/documents/[id]`, Phase 5) drives the same `ContextPanel` for
its metadata/entities/"ask about this document" panel — per this shared-panel
design, opening a citation from within that panel's own mini-chat replaces
the metadata view with the passage view (no "back" affordance beyond the
passage view's "Open full document" link, which reloads the metadata panel).

## Running locally

**1. Backend, Celery & infra (Docker Compose)** — postgres, redis, minio,
qdrant, `backend` (Django), and `celery` all run in containers. Only the
frontend runs natively on the host.

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_demo   # demo org + admin user + MinIO bucket
```

First build pulls several GB (torch/paddlepaddle/sentence-transformers) —
slow once, cached after. Host-side ports (only relevant for tools running
outside Docker, or the native fallback below) are remapped from Docker
defaults to avoid clashing with a host Postgres/Redis: Postgres →
`localhost:5435`, Redis → `localhost:6380`. MinIO is on `:9000` (API) /
`:9001` (console), Qdrant on `:6333`, Django on `:8000`. Inside the
Docker network, `backend`/`celery` reach the others via service name and
*internal* port (`postgres:5432`, `redis:6379`, etc. — see the
`x-backend-env` anchor in `docker-compose.yml`), not these remapped ones.

Demo login: `admin@docufy.ai` / `ChangeMe123!`. Tests:
`docker compose exec backend python manage.py test`. Logs:
`docker compose logs -f backend celery`.

Django autoreloads on code change (bind-mounted + `runserver`'s own
reloader); **Celery does not** — `docker compose restart celery` after
changing task code. Both containers read `.env` once at startup, so
`docker compose restart backend celery` after changing it (e.g. switching
`AI_GATEWAY_PROVIDER`).

Running Django/Celery natively instead (e.g. for IDE debugging) still
works — `.env`'s defaults already assume that mode (localhost + the
remapped ports above); just run `docker compose up -d postgres redis
minio qdrant` (skip `backend`/`celery`) and then the usual
`venv` + `pip install -r requirements.txt` + `manage.py runserver` /
`celery -A docufy_ai worker -l info` locally.

**2. Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

Open http://localhost:3000. Build/lint checks: `npm run build && npm run lint`.

## Progress

**✅ Phase 1 — Foundation (complete)**
- `Organization` + custom `User` model (multi-tenant-ready schema, single org for MVP), JWT auth (`/api/auth/login/`, `/refresh/`, `/me/`)
- Document upload endpoint → MinIO, `Document` model with status (`UPLOADED`/`PROCESSING`/`READY`/`FAILED`)
- CORS configured for local dev
- Frontend scaffold: design tokens, `Sidebar`/`TopBar`/`ContextPanel` shared layout, typed API client, login page, Documents page (upload + status list, polls while a doc is active)
- Docker Compose, `.env.example` (both sides), `seed_demo` management command
- 10 backend tests passing (auth, upload validation, org-scoping)

**✅ Phase 2 — Document processing pipeline (complete)**
- Celery task (`documents/tasks.py`) queued on upload; extractors read file
  *bytes* via the storage API (`document.file.open('rb')`), not `.file.path`
  — required for MinIO/S3, which has no local path (caught + fixed during
  manual testing, since the local-storage tests didn't exercise that gap)
- PDF extraction (PyMuPDF: text layer + font-size heading detection, OCR
  fallback for scanned pages), DOCX (python-docx: heading styles + manual
  page breaks), TXT (paragraph/form-feed page splitting)
- PaddleOCR for scanned PDFs/images — runs each language in `OCR_LANGUAGES`
  (default `en,ru`) and keeps the best-scoring result, a stand-in for real
  language detection across the Uzbek/Russian/English mix (no dedicated
  Uzbek model; deviation noted in the Phase 2 spec below)
- Structure detection (`documents/processing/blocks.py`): font-size/style/
  keyword-based heading detection + hierarchy-path stack; chunking
  (`chunking.py`) groups blocks into 200–500 "token" (whitespace-word-count
  proxy) chunks, never crossing a section boundary
- New `Chunk` model; `Document.page_count` now populated; frontend
  Documents page gained a Pages column
- 36 backend tests passing (was 10); PaddleOCR/paddlepaddle pinned in
  `requirements.txt` (unpinned installs backtrack badly — avoid) and needed
  a numpy<2 + opencv 4.6.0.66 pin to resolve a real ABI conflict — see
  `requirements.txt` comments

**✅ Phase 3 — Search & retrieval (complete)**
- BGE-M3 embeddings (`documents/processing/embeddings.py`) + Qdrant vector
  store (`vector_store.py`, collection `docufy_chunks`, 1024-dim cosine,
  payload includes `organization_id` for tenant-scoped search); wired into
  `pipeline.process_document()` right after chunking — a document isn't
  `READY` until it's embedded and indexed
- `POST /api/search/` (new `search` app): query in, org-scoped top-K
  chunks out, ordered by similarity
- Frontend: `TopBar` cmd+K now does live debounced semantic search;
  `/search` page runs full search and opens matched passages in the
  existing `ContextPanel` (in `font-serif`, per the design system)
- Fixed a real bug in passing: the shared `CommandDialog` component never
  wrapped children in cmdk's `<Command>` root, so `CommandInput`/`CommandList`
  had no context — invisible before because the static "Go to" list still
  rendered. Fixed in `TopBar`.
- Verified real cross-lingual retrieval quality (not just wiring): same
  meaning across EN/RU/UZ scored ~0.82–0.93 cosine similarity vs. ~0.40 for
  unrelated text; live semantic search correctly ranks a paraphrased query
  ("when do I have to pay?") above its exact-keyword match
- 52 backend tests passing (was 36); `torch` needed the CPU-only wheel
  index (default PyPI wheel bundles CUDA, multi-GB) and `>=2.6` specifically
  (transformers refuses `torch.load` below that — CVE-2025-32434) — see
  `requirements.txt` comments

**✅ Phase 4 — RAG & AI answers (complete)**
- AI Gateway (`ai_gateway/`): `ai_chat(messages, context=None, **kwargs) -> str`,
  provider-agnostic. `AI_GATEWAY_PROVIDER=anthropic` (Claude API, needs
  `AI_GATEWAY_API_KEY`) or `ollama` (local model via Ollama's OpenAI-
  compatible endpoint, defaults to `qwen2.5:7b-instruct` — chosen over
  Gemma for stronger Uzbek/Russian coverage). Swapping is one env var;
  nothing outside `ai_gateway/` references a provider by name.
- `POST /api/ask/` (`ask_ai` app): retrieves org-scoped top-K chunks
  (reusing Phase 3's embedding + Qdrant search), asks the LLM to answer
  strictly from them as JSON (`answer`/`cited_sources`/`confident`/
  `follow_up_questions`), and maps `cited_sources` back to real chunk
  metadata rather than trusting the model's own claims. Low-confidence
  fallback (no LLM call) when there's nothing indexed or the top retrieval
  score is weak; confidence is also downgraded server-side if the model
  claims confidence without actually citing anything.
- Frontend: real multi-turn Ask AI view — answer in `font-serif`, citation
  chips opening `ContextPanel`, expandable full-sources list with match %,
  follow-up chips that resubmit with conversation history, dashed-border
  styling for low-confidence answers.
- **No real LLM key was available to test against** (user chose to build
  against a mock and supply credentials later). Verified for real anyway:
  stood up a fake OpenAI-compatible HTTP server and pointed the real
  running stack (Django + Celery + Next.js) at it through
  `AI_GATEWAY_PROVIDER=ollama` — this exercises the actual `OllamaClient`
  HTTP path and the actual frontend rendering, just not a real model's
  output. **Not yet verified: whether a real LLM (Claude or local Qwen)
  reliably follows the JSON response format** — that's the one thing that
  still needs a real key/model to confirm.
- 80 backend tests passing (was 52)

**✅ Phase 5 — Citations & document viewer (complete)**
- `GET /api/documents/{id}/content/`: chunks grouped by page — this *is*
  the "page-level position info per chunk" the spec asks for (Phase 2's
  `Chunk.page_number` already carried it; this endpoint just exposes it).
  Renders the extracted text page-by-page, not a pixel-faithful original —
  consistent with this MVP's text-first approach throughout, avoids a
  PDF.js/mammoth.js integration.
- `DocumentPassageViewer` (shared component): renders a document's pages;
  given a target chunk, highlights + scrolls to it. Every citation click
  app-wide (Search, Ask AI, "ask about this document") now goes through
  `useOpenDocumentPassage()` to show this in `ContextPanel` — previously
  (Phases 3-4) citations only showed the raw cited chunk's text, not the
  document; that was a placeholder, this is what the spec actually asked
  for.
- Document Viewer page (`/documents/[id]`): full document render as main
  content; `ContextPanel` auto-opens with metadata, an honest "Phase 6"
  placeholder for extracted entities, and "Ask about this document".
  Documents list rows now link here.
- `vector_store.search()` and `POST /api/ask/` gained an optional
  `document_id` scope so "Ask about this document" only retrieves from
  that one document, not the whole org.
- **Real bug fixed in passing**: Sidebar's org-switcher dropdown label
  crashed (Base UI `MenuGroupContext is missing` — needs a `<Menu.Group>`
  wrapper that Radix wouldn't have required). Present since Phase 1, never
  caught before now — see tech stack note above.
- 88 backend tests passing (was 80)

**✅ Phase 6 — Document intelligence basics (complete, comparison descoped)**
- **User explicitly descoped document comparison** ("useless feature for
  now, skip this") — only entity extraction + auto-classification shipped.
  If comparison is wanted later, its spec is still preserved untouched
  below.
- `documents/processing/intelligence.py`: one combined LLM call per
  document (not two) does classification (`Document.Category` — CONTRACT/
  REGULATION/POLICY/REPORT/OTHER, a fixed choices field) and entity
  extraction (dates/amounts/parties as flat string lists in
  `Document.entities`, a JSONField). Input capped at 12,000 chars — a real
  limitation on long documents, not fixed (see deviation note below).
- Wired into `pipeline.process_document()` with its own try/except:
  unlike extraction/chunking/embedding, a failure here never fails the
  document — category/entities just stay unset and the doc still reaches
  `READY`, since this is supplementary metadata, not required for the
  document to be searchable or askable.
- Frontend: `CategoryBadge` (Documents list gained a Category column),
  and the Document Viewer's "Extracted entities" section — previously an
  honest Phase-6 placeholder — now renders real Parties/Dates/Amounts, or
  distinguishes "not yet processed" from "processed, nothing found".
- Verified through the real Celery pipeline (not just mocked tests): the
  fake-LLM-server technique from Phases 4-5 was extended to detect which
  system prompt it received and return the right JSON shape for either
  RAG Q&A or document analysis.
- 98 backend tests passing (was 88)

**All six planned phases are now complete**, except document comparison
(part of the original Phase 6 spec), which remains unbuilt — descoped by
explicit user request, not forgotten. Its spec is preserved as-is below
if it's wanted later; a session picking that up should treat it as its
own mini-phase and follow the same ground rules (tests, README/CLAUDE.md
updates) as everything above.

Full requirements for each unstarted phase are in **Phase specs** below —
read the relevant phase's spec in full before starting it. When a phase
ships: change its checkbox to ✅, add a short bullet list here (like Phase 1's
above) summarizing what was actually built and any deviations from the spec,
and leave the spec section below untouched as the historical source of truth.

## Phase specs (original requirements)

These are the original, full-detail phase prompts from the project kickoff.
A new session picking up mid-project should read this section in full before
resuming work — it has requirements not necessarily captured in the
one-line Progress bullets above.

**Ground rules that apply to every phase:**
- Do not deviate from the tech stack listed above without asking first.
- Build phases in order. Stop after each phase, report what was built and
  how to test it, and wait for confirmation before starting the next one.
- For every phase: write tests for core logic (chunking correctness,
  retrieval accuracy, citation correctness, etc.), and add a short section to
  the README explaining what was added and how to run it locally — then
  update the Progress section in this file.

---

### Phase 2 — Document processing pipeline

- Celery worker triggered on upload.
- Detect if a PDF has a text layer (PyMuPDF) vs needs OCR (PaddleOCR).
- Extract text, preserve page numbers.
- Best-effort structure detection (headings/sections).
- Chunk the text: paragraph/section-level chunks (200–500 tokens), each
  storing `document_id`, page number, section heading if known, and a
  hierarchy-path prefix (e.g. `"Chapter 2 > Article 14"`).
- Document status updates through the pipeline stages, visible in the
  frontend (the Documents page already polls while a doc is
  `UPLOADED`/`PROCESSING`, so this should light up for free — add any new
  intermediate statuses to `DocumentStatusBadge` and the `ACTIVE_STATUSES`
  set in `frontend/src/app/(app)/documents/page.tsx` if introduced).

> **Shipped as ✅ above.** Deviations: no new statuses were needed (UPLOADED/
> PROCESSING/READY/FAILED covers it). "Token" in chunking is a whitespace
> word-count proxy, not a real tokenizer — Phase 3 should re-derive exact
> counts from the BGE-M3 tokenizer if that matters there. OCR language
> handling isn't true detection: it runs every language in `OCR_LANGUAGES`
> (`documents/processing/ocr.py`) and keeps the best-scoring result, which
> is a real quality limitation on mixed-script pages (can produce
> Latin/Cyrillic character mix-ups) — revisit with real per-document/per-
> line language detection if OCR quality matters more later. `pdfplumber`
> was dropped (PyMuPDF alone covers text + font-size extraction).

### Phase 3 — Search & retrieval

- Generate embeddings per chunk with BGE-M3, store in Qdrant with metadata.
- Semantic search endpoint: query in, top-K matching chunks with
  document/page/section info out.
- Frontend: the global cmd+K search (shell already exists in `TopBar`, wired
  to a placeholder — replace with real results), plus a dedicated Search page
  (currently a stub at `frontend/src/app/(app)/search/page.tsx`).

> **Shipped as ✅ above.** Deviations: chunk `token_count` is still the
> whitespace-word-count proxy from Phase 2 — did *not* end up re-deriving it
> from the BGE-M3 tokenizer, since it's only used for sizing chunks (not for
> anything embedding-accuracy-sensitive) and the proxy is good enough for
> that. Result cards show a "match %" (raw cosine similarity × 100, not a
> calibrated probability) — fine for relative ranking, don't read too much
> into the absolute number. No re-ranking step; results are raw
> vector-similarity order.

### Phase 4 — RAG & AI answers

- AI Gateway module: provider-agnostic `ai_chat(messages, context)`.
- RAG endpoint: retrieve top chunks, force the LLM to answer only from them
  and cite which chunk(s) it used; low-confidence fallback message instead
  of guessing.
- Frontend: the Ask AI conversation view exactly as designed — answer block,
  citation chips below it, expandable sources, follow-up suggestion chips,
  right-side panel opening on citation click (use the existing
  `useContextPanel()` hook — see Design system above). Currently a stub at
  `frontend/src/app/(app)/ask-ai/page.tsx`.

> **Shipped as ✅ above.** Deviations: the spec's `ai_chat(messages, context)`
> signature is implemented literally — `context` is optional grounding text
> injected as a leading system message, generic (not RAG-specific), so
> `ai_gateway/` stays reusable for any future LLM call, not just this RAG
> endpoint. Added a local-model provider (`ollama`) beyond the spec's
> "hosted API" framing, per explicit user request — see the tech stack
> entry above for why Qwen2.5 over Gemma. **Not verified against a real
> LLM** (no API key/local model available to this session) — verified
> instead against a fake OpenAI-compatible server standing in for the real
> HTTP path; see the Phase 4 README section for exactly what that did and
> didn't prove. A future session should do one real conversation (either
> provider) before trusting the JSON-prompting approach in `ask_ai/rag.py`
> holds up against actual model output, not just a scripted stand-in.

### Phase 5 — Citations & document viewer

- Store page-level position info per chunk.
- Clicking a citation opens the document in the right-side `ContextPanel`,
  scrolled/highlighted to that passage.
- Document Viewer page matching the design: full document render, metadata
  panel, extracted entities, "Ask about this document" input.

> **Shipped as ✅ above.** Deviations: "full document render" means the
> extracted text rendered page-by-page (reusing Phase 2's chunks), not a
> pixel-faithful rendering of the original PDF/DOCX — no PDF.js/mammoth.js
> integration. "Highlighted" is a highlighted DOM node in that text
> rendering, not a highlight overlaid on the original file. "Extracted
> entities" is an honest placeholder pointing at Phase 6, since that's
> where entity extraction is actually specified — nothing was faked early.
> The metadata panel reuses the shared `ContextPanel` per the original
> design brief's own framing (see Design system → Layout above), which
> means it isn't a separate always-visible column — a citation click while
> viewing metadata replaces it with the passage view.

### Phase 6 — Document intelligence basics

- Document comparison: two versions in, added/removed/modified sections out,
  each with old text, new text, and an AI-generated explanation.
- Basic entity extraction (dates, amounts, party names) via the LLM, stored
  as structured metadata.
- Auto-classification on upload (contract, regulation, policy, report, etc.).

> **Entity extraction + auto-classification shipped as ✅ above; document
> comparison explicitly descoped by the user** ("useless feature for now,
> skip this") — the bullet above is preserved as-is in case it's picked up
> in a future session; nothing about it has been started.
>
> Deviations on what did ship: classification and entity extraction happen
> as **one combined LLM call**, not conceptually separate steps — cheaper,
> and both read the same document text anyway. Entities are flat string
> lists with no normalization (dates/amounts stay exactly as phrased in
> the source, not parsed into actual date/number types) and no location
> info (unlike chunks, an entity doesn't know which page/chunk it came
> from — follow Phase 5's `page_number`-on-`Chunk` pattern if that's
> needed later). Input is capped at 12,000 characters, so entities past
> that point in a long document won't be found — a known, undealt-with
> scope tradeoff, not an oversight (see `documents/processing/intelligence.py`
> and the Phase 6 README section for the full reasoning). Category is a
> fixed five-value choices field (not freeform text) specifically so it
> stays filterable/groupable if that's built on later.

---

**Original design brief** (for reference — already implemented in Phase 1,
kept here so later phases stay visually consistent):

> Layout: compact left sidebar (~248px, collapsible) with org switcher,
> primary nav (Search, Ask AI, Documents, Workflows, Analytics), and a
> Knowledge Spaces list below it; a slim top bar with a cmd+K global search
> trigger; main content centered with a max-width column; a collapsible
> right-side contextual panel for document/citation preview.
>
> Palette: near-white background, off-white sidebar, hairline borders,
> near-black ink, soft gray secondary text, faint tertiary text. One
> restrained accent — a muted deep indigo/blue — used only for active nav
> state, primary buttons, focus rings, and citation highlights. No
> gradients, no drop shadows beyond a 1px border, no rounded-corner-plus-
> left-accent-border card pattern.
>
> Typography: Inter for all UI chrome; Source Serif 4 for AI answer text and
> document body text (long-form reading content only, not UI labels).
>
> Citations in AI answers render as small chips (accent-colored border/
> background) that open the right-side panel scrolled to the cited
> page/section, with the passage highlighted.

> Update this section at the end of every phase: move the phase to ✅ in
> Progress with a one-line summary of what shipped, and note here (inline,
> under the relevant phase spec) any deviation from the original spec so
> future sessions know the spec text is no longer 1:1 with reality.
