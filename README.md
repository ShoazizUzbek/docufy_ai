# Docufy AI

Enterprise AI Document Intelligence Platform — upload documents, process them
(OCR + text extraction + chunking), ask questions and get AI answers with
citations back to the exact source page/section.

## Stack

- **Backend**: Django + Django REST Framework, PostgreSQL, Celery + Redis, MinIO (S3-compatible storage), Qdrant (vector DB)
- **Frontend**: Next.js (App Router) + React + TypeScript + Tailwind CSS + shadcn/ui
- **OCR/parsing**: PyMuPDF (digital PDFs), PaddleOCR (scanned files) — Phase 2
- **Embeddings**: BGE-M3 (multilingual, 1024-dim) stored in Qdrant — Phase 3
- **LLM**: internal AI Gateway module, provider-agnostic — swaps between the Claude API (Anthropic) and a local model (e.g. Qwen2.5 via Ollama) with one env var — Phase 4

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

### 3. Celery worker (Phase 2+)

Document processing (text extraction, OCR, chunking) runs as a Celery task.
In a separate terminal, with the venv activated:

```bash
celery -A docufy_ai worker -l info
```

Without a running worker, uploaded documents stay `UPLOADED` — the task
sits queued in Redis until a worker picks it up.

### 4. Frontend

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

## Phase 2 — Document processing pipeline

**What was built:**

- **Celery task** (`documents/tasks.py`): `process_document_task`, queued via
  `.delay()` right after a successful upload (`documents/views.py`). Requires
  a running worker — see "Celery worker" above; without one, documents stay
  `UPLOADED` indefinitely (the task just sits in the Redis queue).
- **Extraction** (`documents/processing/extractors.py`): every extractor
  takes raw file *bytes*, not a path — `pipeline._extract()` reads the file
  via `document.file.open('rb')` (the Django storage API) rather than
  `.file.path`, since the MinIO/S3 backend has no local filesystem path.
  - **PDF**: PyMuPDF pulls the text layer plus each line's font size. If the
    average extracted characters per page falls under a threshold (i.e. a
    scanned/image-only PDF), it renders each page to an image and routes
    through OCR instead.
  - **DOCX**: `python-docx`, walking paragraphs; `Heading N` / `Title`
    styles become headings, manual page breaks (`<w:br w:type="page"/>`)
    increment a page counter (docx has no fixed pagination otherwise).
  - **TXT**: paragraph-split on blank lines; a form-feed (`\f`) character
    splits pages if present, otherwise the whole file is page 1.
  - **Images / scanned PDFs**: **PaddleOCR**. Since documents mix Uzbek
    (Latin), Russian (Cyrillic), and English with no per-document language
    tag, `documents/processing/ocr.py` runs every language pack listed in
    `OCR_LANGUAGES` (default `en,ru`) against the page and keeps whichever
    produced the most confidently-recognized text — a cheap stand-in for
    real language detection. There's no dedicated Uzbek model; `en` covers
    its Latin script reasonably well, not perfectly.
- **Structure detection** (`documents/processing/blocks.py`): best-effort,
  not ML-based. PDF headings are lines whose font size is notably larger
  than the page's most common (body) size; DOCX headings come from paragraph
  style; plain text/OCR output has no font info, so headings there are
  detected by keyword (Chapter/Article/Section/Глава/Раздел/Статья/Bo'lim/
  Modda/Bob) or an all-caps short line. A stack tracks open headings by
  level to build each block's `hierarchy_path` (e.g. `"Chapter 2 > Article
  14"`) and nearest `section_heading`.
- **Chunking** (`documents/processing/chunking.py`): groups consecutive
  blocks into 200–500 "token" chunks (a whitespace-word-count proxy — Phase
  3 will re-derive exact counts from the BGE-M3 tokenizer at embedding
  time), never merging across a hierarchy/section boundary. A single
  paragraph that alone exceeds 500 tokens is split by sentence (hard word
  wrap as a last resort).
- **Data model**: new `Chunk` model (`document` FK, `index`, `page_number`,
  `section_heading`, `hierarchy_path`, `text`, `token_count`). Reprocessing
  a document deletes and replaces its chunks.
- **Status flow**: `UPLOADED` → `PROCESSING` → `READY` (with `page_count`
  set) or `FAILED` (with `error_message`) — no new statuses were needed, so
  the frontend's existing polling/badge already lights up for this for
  free, per the original spec's expectation.

**How to test:**

1. Backend: `python manage.py test` — 36 tests total. Phase 2 adds tests
   under `documents/tests/`: `test_chunking.py` (heading detection,
   hierarchy-path construction, chunk sizing/section-boundary/oversized-
   paragraph splitting — pure unit tests, no I/O), `test_extractors.py`
   (PDF text-layer + OCR-fallback extraction against a real PDF built with
   PyMuPDF, DOCX heading/page-break extraction, TXT paragraph/page
   splitting — all working from in-memory bytes, matching how the pipeline
   actually reads files), and `test_pipeline.py` (`process_document()`
   end-to-end against real TXT/PNG files, including a
   reprocessing-replaces-old-chunks case). OCR itself is mocked in tests
   (`run_ocr`) rather than exercising the real PaddleOCR model, since
   asserting on model output isn't meaningful and it would make the suite
   slow/flaky; the OCR *wiring* (routing, language-pack selection, heading
   detection on its output) is what's tested. The real model was verified
   manually against a generated scanned PDF end-to-end through the API +
   Celery worker + MinIO (see below) — it reaches `READY` with chunks;
   recognition quality on mixed-language input is best-effort, per above.
2. Manual, full pipeline: run infra + backend + a Celery worker
   (`celery -A docufy_ai worker -l info`) + frontend. Upload a text-layer
   PDF, a scanned/image-only PDF, a `.docx`, and a `.txt` file. Watch each
   move `Uploaded → Processing → Ready` in the Documents page (it's
   already polling). Inspect the resulting chunks in the admin
   (`/admin/documents/chunk/`) — check `page_number`, `section_heading`,
   and `hierarchy_path` look right for a document with real headings.
3. To exercise OCR for real (not mocked), upload a scanned/image document —
   PaddleOCR downloads its detection/recognition models on first use
   (requires network access) and CPU inference is noticeably slower than
   the text-layer path.

## Phase 3 — Search & retrieval

**What was built:**

- **Embeddings** (`documents/processing/embeddings.py`): BGE-M3
  (`BAAI/bge-m3` via `sentence-transformers`), lazily loaded once per
  process. It's genuinely multilingual (100+ languages, including Uzbek,
  Russian, and English), so — unlike OCR — there's no per-language pass;
  one model embeds everything, and needs no special instruction prefix for
  either passages or queries.
- **Vector store** (`documents/processing/vector_store.py`): thin Qdrant
  wrapper — `ensure_collection()` (1024-dim, cosine distance), `upsert_chunks()`,
  `delete_document_vectors()`, `search()`. Every point's payload carries
  `organization_id` (used to scope every query — critical for multi-tenancy),
  `document_id`, `page_number`, `section_heading`, `hierarchy_path`, `text`,
  and `original_filename`, so a search result is fully self-contained
  without a DB round-trip.
- **Pipeline integration** (`documents/processing/pipeline.py`):
  `process_document()` now embeds and upserts a document's chunks right
  after chunking, before marking it `READY` — a document is only "ready"
  once it's actually searchable. Reprocessing deletes old Qdrant points
  for that document first (`delete_document_vectors`), matching the
  existing DB chunk-replacement behavior. An embedding/Qdrant failure marks
  the document `FAILED`, same as an extraction failure.
- **Search endpoint**: `POST /api/search/` (new `search` app) — body
  `{"query": str, "limit"?: int}`, returns matching chunks ordered by
  cosine similarity, scoped to the caller's organization. `limit` defaults
  to 10, capped at 50.
- **Frontend**: the `TopBar`'s cmd+K dialog now does live, debounced
  (300ms) semantic search as you type, showing up to 5 results with
  filename/hierarchy/snippet; selecting one (or "View all results") goes
  to `/search?q=...`. The Search page (`frontend/src/app/(app)/search/page.tsx`)
  runs the same search, shows up to 20 results with a match percentage,
  and clicking a result opens the existing `ContextPanel` with the full
  passage — set in `font-serif`, since that's exactly the "long-form
  reading content" the design system reserves that font for.
- **Bug fixed in passing**: the shared `CommandDialog` component
  (`frontend/src/components/ui/command.tsx`, from Phase 1's shadcn init)
  never wrapped its children in cmdk's `<Command>` root, so
  `CommandInput`/`CommandList`/etc. had no context to read from — the
  cmd+K dialog's static "Go to" items happened to still render, which
  masked it. Fixed by wrapping `TopBar`'s dialog content in `<Command
  shouldFilter={false}>` (filtering is server-side now anyway).

**How to test:**

1. Backend: `python manage.py test` — 52 tests total. New coverage:
   `documents/tests/test_embeddings.py` (mocks the model — tests the
   wrapper logic, not BGE-M3 itself), `documents/tests/test_vector_store.py`
   and `search/tests/test_search_api.py` (both run against the **real**
   Qdrant container from `docker-compose`, in an isolated per-test-run
   collection that's deleted afterward, with `embed_texts` mocked to
   deterministic vectors — so Qdrant's upsert/filter/search/delete
   behavior is genuinely exercised without needing the ML model loaded).
   `documents/tests/test_pipeline.py` (Phase 2) now mocks
   `upsert_chunks`/`delete_document_vectors` at the class level so it
   stays fast and focused on extraction/chunking; one new test in there
   confirms the pipeline actually calls them with the right chunks, and
   another confirms an embedding failure marks the document `FAILED`.
2. Real model, manually verified (not worth the model-load cost in the
   automated suite): loaded BGE-M3 and embedded the same sentence in
   English, Russian, and Uzbek — cross-lingual cosine similarity for
   matching meaning came back ~0.93 (EN-RU) and ~0.82 (EN-UZ), vs. ~0.40
   for an unrelated sentence, confirming the cross-lingual retrieval this
   whole phase depends on actually works.
3. Manual, full pipeline: infra + backend + Celery worker + frontend.
   Upload a multi-section document, wait for `Ready`, then search for a
   phrase that shares **no keywords** with the target passage (e.g. "when
   do I have to pay?" against a chunk that says "rent... first day of each
   calendar month..."). Confirm the right section ranks first — that's
   the actual point of semantic over keyword search. Try both the cmd+K
   dialog and the `/search` page; click a result and confirm the
   `ContextPanel` opens with the full passage.

**Dependency notes** (see `requirements.txt` comments):
`sentence-transformers` pulls in `torch`, whose default PyPI wheel bundles
CUDA libraries even on a CPU-only machine (multi-GB) — installed instead
from PyTorch's dedicated CPU wheel index via `--extra-index-url` in
`requirements.txt`. `transformers` also refused to load the model on
torch <2.6 (CVE-2025-32434 restricts `torch.load` on older versions), so
torch is pinned to `2.6.0`, not the smaller `2.5.1` first tried.

## Phase 4 — RAG & AI answers

**What was built:**

- **AI Gateway** (`ai_gateway/`, plain Python package — no models, not a
  registered Django app): `ai_chat(messages, context=None, **kwargs) ->
  str`, provider-agnostic. `AI_GATEWAY_PROVIDER` picks the backend:
  - `anthropic` — Claude API via the official SDK. Needs `AI_GATEWAY_API_KEY`.
  - `ollama` — any local model exposed through Ollama's OpenAI-compatible
    `/v1/chat/completions` endpoint (defaults to `qwen2.5:7b-instruct` at
    `http://localhost:11434/v1`; override with `AI_GATEWAY_MODEL` /
    `AI_GATEWAY_BASE_URL`, e.g. to run `gemma2:9b` instead). **Qwen2.5 was
    chosen as the local default over Gemma specifically because of this
    project's multilingual requirement** — Qwen's training covers Uzbek/
    Russian noticeably better.
  - Both implementations share the same interface
    (`AIGatewayClient.chat(messages, ...)`), so swapping providers is a
    one-line env var change — nothing else in the codebase references a
    provider by name outside `ai_gateway/`.
- **RAG endpoint**: `POST /api/ask/` (new `ask_ai` app) — body
  `{"question": str, "conversation_history"?: [{question, answer}, ...]}`.
  `ask_ai/rag.py` does the actual work: embed the question (reusing Phase
  3's `embed_query`), retrieve top-K org-scoped chunks from Qdrant
  (reusing Phase 3's `vector_store.search`), and — **only if there's
  something worth asking about** — ask the LLM to answer strictly from
  those excerpts. The LLM is asked to respond as JSON (`answer`,
  `cited_sources`, `confident`, `follow_up_questions`); citations are
  built by mapping `cited_sources` back to the actual retrieved chunk
  metadata, not by trusting anything else the model says. A markdown code
  fence around the JSON (some models add one despite instructions) is
  stripped before parsing; if the response still isn't valid JSON, the raw
  text becomes the answer with `confident: false` rather than showing the
  user a parse error.
- **Fallback instead of guessing** (per spec), handled without ever
  calling the LLM in the first two cases:
  1. No chunks in the org's index at all → "upload some documents first."
  2. Top retrieval score below `RAG_MIN_SCORE` (default 0.3) → "couldn't
     find anything that clearly answers this."
  3. LLM itself reports low confidence, or claims confidence but cites
     nothing → confidence is downgraded to `false` regardless of what it
     claimed (`confident AND has_citations`, not just what the model said).
  4. The AI Gateway itself fails (network, bad key, model down) →
     "couldn't reach the AI service," with whatever sources were found
     still shown for transparency.
- **Frontend**: Ask AI is now a real multi-turn conversation view — user
  question, answer block (`font-serif`, per the design system), citation
  chips (`components/ask-ai/citation-chip.tsx`) that open the existing
  `ContextPanel` with the full passage, an expandable "N sources" list
  showing everything retrieved (not just what was cited, with a match %),
  and follow-up suggestion chips that re-submit as the next question with
  conversation history attached. Low-confidence answers render with a
  dashed border / muted background instead of the normal card style — a
  visual cue, not a separate component.

**How to test:**

1. Backend: `python manage.py test` — 80 tests total. New coverage:
   `ai_gateway/tests/` (both clients' request/response handling mocked at
   the SDK/HTTP boundary — message-format translation, error handling,
   default model selection — no real network calls) and `ask_ai/tests/`
   (`test_rag.py` covers every branch in the list above — no chunks, weak
   score, valid citation, markdown-fenced JSON, downgraded confidence,
   unparseable response, gateway failure, conversation history — all with
   `ai_chat` mocked; `test_ask_ai_api.py` covers the endpoint: auth, blank/
   missing question, malformed `conversation_history`, org scoping).
2. Real end-to-end verification without a real LLM key (none was available
   to build against — see below): stood up a tiny fake OpenAI-compatible
   HTTP server as a stand-in backend, pointed `AI_GATEWAY_PROVIDER=ollama`
   at it, and drove the **actual running** Django server + Celery worker +
   Next.js frontend through a real upload → process → ask flow. This
   exercises the real `OllamaClient` HTTP request/response code (not a
   mock of it), the real embedding + Qdrant retrieval, and the real
   frontend rendering — confirmed multi-turn conversation state, citation
   chips opening `ContextPanel`, the sources list expanding with correct
   match percentages, follow-up chips re-submitting with history, and the
   low-confidence dashed-border styling, all through the browser.
3. **Not yet verified against a real LLM** — no Anthropic API key or local
   Ollama install was available in this environment (Ollama's Linux binary
   download was impractically slow here; also this is a dev sandbox, not
   the machine anyone intends to run a local model on). To test for real:
   - Anthropic: set `AI_GATEWAY_API_KEY` (and `AI_GATEWAY_PROVIDER=anthropic`,
     the default).
   - Local: install Ollama, `ollama pull qwen2.5:7b-instruct`, set
     `AI_GATEWAY_PROVIDER=ollama`. No key needed.
   Either way, the JSON-prompting approach (asking a real model to emit
   exactly the schema `ask_ai/rag.py` expects) hasn't been checked against
   a real model's actual output — worth a first real conversation to make
   sure a live model reliably follows the format after the fake-server
   verification above.

## Phase 5 — Citations & document viewer

**What was built:**

- **`GET /api/documents/{id}/content/`**: the document's chunks, grouped
  by page and ordered — what both the citation-preview panel and the
  Document Viewer render. This *is* the "page-level position info per
  chunk" the spec asks for — Phase 2's `Chunk.page_number` already carried
  it, so this endpoint is just exposing it, not new storage. **Note on
  scope**: this renders the *extracted text*, grouped by page — not a
  pixel-faithful reproduction of the original PDF/DOCX. Consistent with
  how the rest of this MVP treats documents (text-first pipeline, not a
  visual one) and avoids needing a PDF.js/mammoth.js integration for
  Phase 5; revisit if true visual fidelity turns out to matter.
- **`DocumentPassageViewer`** (`frontend/src/components/documents/document-passage-viewer.tsx`):
  fetches that endpoint and renders every page's chunks in `font-serif`;
  given a `targetChunkId`, that chunk gets an accent background and is
  scrolled into view. This is the actual "highlight" — a highlighted DOM
  node, not text-layer search — which only works because we're rendering
  extracted text rather than the original file.
- **Citations now open the real document, not just the cited chunk**:
  every citation click across the app (Search, Ask AI, and the new
  "Ask about this document") now goes through
  `useOpenDocumentPassage()` → the `ContextPanel` shows the *whole*
  document via `DocumentPassageViewer`, scrolled and highlighted to that
  passage, plus an "Open full document" link to the dedicated viewer.
  Previously (Phases 3-4) it showed only that one chunk's raw text — this
  is what the spec's "opens the document... scrolled/highlighted" actually
  asked for, that earlier version was a placeholder.
- **Document Viewer page** (`frontend/src/app/(app)/documents/[id]/page.tsx`):
  full document render as the main content (reusing `DocumentPassageViewer`,
  no target — matches the design system's explicit statement that the
  `ContextPanel` is "what citation clicks *and the document viewer* will
  drive"). On load it opens `ContextPanel` with: a metadata section
  (status, type, pages, size, uploader, upload date), an "Extracted
  entities" section that's honestly a placeholder — real extraction is
  Phase 6, not invented early — and "Ask about this document"
  (`components/documents/ask-about-document.tsx`, reusing `ConversationTurnCard`
  from Phase 4). Handles all four document statuses with appropriate
  messaging (not just `READY`). The Documents list now links each row's
  filename to its viewer page.
- **Document-scoped Ask AI**: `vector_store.search()` gained an optional
  `document_id` filter; `POST /api/ask/` accepts an optional `document_id`;
  "Ask about this document" passes it through so retrieval — and therefore
  every citation in the answer — is scoped to just that one document
  instead of the whole organization.
- **Real bug fixed in passing, unrelated to the above**: the Sidebar's org
  switcher dropdown (`DropdownMenuLabel` showing the user's email) crashed
  with a Base UI `MenuGroupContext is missing` error — that component
  requires being inside a `<Menu.Group>` in this Base UI-backed shadcn
  setup, unlike Radix where a bare label works. Present since Phase 1;
  never previously caught because dropdown interaction is hard to drive
  reliably in this environment's browser automation, and it happened to
  render without visibly breaking under some conditions. Fixed in
  `frontend/src/components/layout/sidebar.tsx`.

**How to test:**

1. Backend: `python manage.py test` — 88 tests total. New coverage:
   `documents/tests/test_api.py` (`DocumentContentAPITests` — page
   grouping/ordering, org-scoping, empty-content case),
   `documents/tests/test_vector_store.py` (document-scoped search against
   the real Qdrant container, embeddings mocked), `ask_ai/tests/` (the
   document-scoped no-content message, `document_id` passed through
   `vector_store.search()`, the API accepting/validating/rejecting
   `document_id`).
2. Manual, full pipeline: upload a multi-section, multi-page document,
   wait for `Ready`, click its name in the Documents list → confirm the
   full text renders page-by-page in serif, the metadata panel opens
   automatically with correct details, and "Extracted entities" honestly
   says Phase 6. Ask something in "Ask about this document" and confirm
   every citation/source comes from *that* document only (verified during
   development against a real multi-document organization — the org-wide
   `Bank_AI_Test_Regulation_UZ.docx` did **not** leak into scoped results).
   From the Search page or Ask AI, click a citation and confirm the panel
   shows the full document scrolled/highlighted to that passage, with a
   working "Open full document" link.
3. Same fake-OpenAI-compatible-server technique as Phase 4 was used again
   here to verify "Ask about this document" for real (no LLM key
   available) — see Phase 4's section above for what that does and
   doesn't prove.

## Phase 6 — Document intelligence basics

**Scope note**: the original spec had three items — document comparison,
entity extraction, and auto-classification. **Comparison was explicitly
descoped by the user** ("useless feature for now, skip this") — only
entity extraction and auto-classification shipped.

**What was built:**

- **`documents/processing/intelligence.py`**: one LLM call per document
  does both classification and entity extraction together (cheaper than
  two calls, and both read the same text). Input is the document's full
  extracted text, capped at `MAX_INPUT_CHARS` (12,000 chars) to bound
  prompt size/cost on long documents — a real limitation on very large
  documents, noted below.
- **Classification**: one of `CONTRACT` / `REGULATION` / `POLICY` /
  `REPORT` / `OTHER` (`Document.Category`, a fixed choices field — not
  freeform text, so it's actually filterable/groupable later). An
  unrecognized or missing category in the model's response falls back to
  `OTHER` rather than failing.
- **Entity extraction**: dates, monetary amounts, and party names, each a
  flat list of strings as written in the source text (no normalization —
  "$1,200" and "January 1, 2026" stay exactly as the document phrases
  them). Stored as `Document.entities`, a `JSONField` shaped
  `{"dates": [...], "amounts": [...], "parties": [...]}`.
- **Never blocks the document**: wired into `pipeline.process_document()`
  right after embedding, wrapped in its own try/except — unlike
  extraction/chunking/embedding (which must succeed for `READY`),
  classification/entities are supplementary. An LLM failure, a malformed
  response, or any other error here just leaves `category`/`entities` at
  their defaults and the document still reaches `READY` normally. This
  mirrors the Phase 4 RAG endpoint's approach to LLM response parsing
  (strip markdown fences, parse JSON, fall back gracefully) — same
  pattern, applied here to a different schema.
- **Frontend**: a `CategoryBadge` component (Documents list gained a
  Category column showing it, or "–" for documents processed before this
  phase existed — there's no backfill migration, only newly-processed
  documents get classified). The Document Viewer's "Extracted entities"
  section, previously an honest Phase-6 placeholder, now renders real
  Parties/Dates/Amounts groups — or an explicit "no entities found"
  vs. "not yet processed" message, which are different states (see
  `ExtractedEntities` in `frontend/src/app/(app)/documents/[id]/page.tsx`).

**How to test:**

1. Backend: `python manage.py test` — 98 tests total. New:
   `documents/tests/test_intelligence.py` (valid response, markdown-fenced
   JSON, invalid category falling back to `OTHER`, unparseable response
   leaving the document unchanged, AI Gateway failure not raising, a
   document with no chunks skipping the LLM call entirely, non-string
   entity values being coerced or dropped) and two new
   `test_pipeline.py` cases confirming `analyze_document()` is actually
   called with the right document, and that its failure doesn't fail the
   document.
2. Manual, full pipeline (same fake-LLM-server technique as Phases 4-5,
   extended to return the classification/entity JSON shape when it
   detects the analysis system prompt vs. the RAG one): uploaded a lease
   document, confirmed it reached `READY` with `category: "CONTRACT"` and
   populated `dates`/`amounts`/`parties` — verified through the running
   API directly and through the browser (Documents list Category column,
   Document Viewer's Details + Extracted entities sections). Also
   confirmed the pre-Phase-6 `Bank_AI_Test_Regulation_UZ.docx` document
   correctly shows the "–" / "not yet processed" fallback states rather
   than crashing or showing stale placeholder text.

**Known limitation, not fixed**: `MAX_INPUT_CHARS` truncation means entity
extraction on a long document only sees its first ~12,000 characters —
entities mentioned later in a long contract or regulation won't be found.
A more thorough version would run this per-chunk (like embeddings) and
merge/deduplicate results, at higher LLM cost. Left as a known scope
tradeoff rather than built speculatively.
