# Image_Search

Prompt-based image search MVP inspired by Google Photos with person-aware filtering.

Stack:

- Frontend: Streamlit
- Backend: FastAPI
- Database and storage: Supabase
- VLM + LLM + embeddings: Gemini
- Face detection and recognition: face_recognition

## Current MVP scope

- Username/password auth
- Upload known faces
- Upload photos for indexing
- Detect and match faces to known identities
- Create annotated image with boxes and labels
- Generate n+1 summaries via Gemini (overall + per person)
- Store text summaries and embeddings in Supabase
- Prompt search with optional name filtering + similarity ranking

## Project layout

```
backend/
	app/
		main.py
		config.py
		schemas.py
		routers/
			auth.py
			ingest.py
			search.py
			deps.py
		services/
			auth_service.py
			supabase_client.py
			face_service.py
			gemini_service.py
			indexing_service.py
			search_service.py
	run.py
frontend/
	streamlit_app.py
supabase/
	schema.sql
requirements.txt
.env.example
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create `.env` from `.env.example` and fill in:

- `SUPABASE_URL`
- `SUPABASE_KEY` (service role key for server-side operations)
- `SUPABASE_BUCKET`
- `GEMINI_API_KEY`

4. In Supabase SQL editor, run [supabase/schema.sql](supabase/schema.sql).

5. Start backend:

```bash
cd backend
python run.py
```

6. Start Streamlit UI (new terminal):

```bash
streamlit run frontend/streamlit_app.py
```

## API summary

- `POST /auth/signup`
- `POST /auth/login`
- `POST /ingest/known-face` (multipart: `person_name`, `image`)
- `POST /ingest/photo` (multipart: `image`)
- `GET /ingest/photo/{photo_id}/status`
- `POST /search` with JSON `{ "prompt": "..." }`

## Notes

- This is an MVP implementation scaffold for initial testing.
- Face matching uses cosine similarity against known face embeddings.
- Person filtering is only applied when Gemini query intent confidence is high.
- Search currently computes embedding similarity in backend memory after filtered fetch.
