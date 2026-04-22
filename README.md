# Image_Search

Image_Search is a prompt-driven personal photo retrieval system inspired by the core experience of Google Photos search. The project enables users to upload their private image collections, register known people, and query photos using natural language requests such as:

"Fetch me all photos of Arman wearing a jacket"

The current implementation is an MVP designed to validate product behavior and search quality before production-scale optimization.

## Base Problem Statement

Personal photo collections grow quickly and become difficult to navigate manually. Traditional folder-based organization fails when users want to search by semantic intent (people, clothing, actions, context), for example:

- all photos of a specific person
- all photos where someone is wearing a specific item
- all photos matching an activity or scene

The core problem this project solves is:

How do we make private image collections searchable by natural language while reducing hallucinations and identity errors?

To solve that, the system combines:

- deterministic face recognition for person identity
- multimodal semantic understanding for rich scene descriptions
- embedding similarity search for natural-language retrieval

## Technical Solution

The system uses a modular architecture where each component has a focused responsibility.

### Stack

- Frontend: Streamlit
- Backend API: FastAPI
- Database and storage: Supabase (Postgres + Storage)
- VLM and LLM: Gemini models
- Face detection and encoding: face_recognition

### High-Level Design

- Streamlit handles authentication, upload flows, and result display.
- FastAPI handles business logic, ingestion orchestration, identity matching, and search.
- Supabase stores metadata tables and image files.
- Gemini generates semantic summaries and text embeddings.
- Vector similarity is computed against stored summary embeddings.

### Why this design

- Identity should be handled by face embeddings, not generative inference.
- Semantics should be handled by VLM/LLM for flexible natural language retrieval.
- Separating identity and semantics reduces hallucination risk and keeps behavior explainable.

## Technical Flow

### 1. Authentication

1. User signs up or logs in with username/password.
2. Backend issues JWT.
3. All user data access is scoped by user_id from token.

### 2. Known Face Enrollment Flow

1. User uploads a known face image with person name.
2. Face detector/encoder runs on image.
3. Validation enforces exactly one face for clean identity registration.
4. Face embedding is stored with person_name and user_id.
5. Source image is stored in Supabase Storage.

### 3. Photo Ingestion Flow

1. User uploads a photo.
2. Original image is stored in Supabase Storage.
3. Faces are detected and encoded.
4. Each detected face is matched against user's known faces via cosine similarity.
5. Annotated image with boxes/labels is generated for indexing/debug workflows.
6. Gemini generates n+1 summaries:

- one overall image summary
- one summary per detected person context

7. Each summary is embedded and stored with:

- photo_id
- user_id
- optional person_name
- summary type (overall/person)
- embedding vector

8. Photo status is updated to indexed or cleaned up on failure.

### 4. Search Flow

1. User submits natural-language prompt.
2. Prompt is embedded using Gemini embeddings.
3. Lightweight query intent parsing checks for person-specific intent.
4. If confident person intent exists, summaries are pre-filtered by person_name.
5. Similarity scores are computed between query embedding and candidate summaries.
6. Results below minimum threshold are rejected.
7. Top results are deduplicated by photo_id and returned with displayable image URLs.

## Current Features (MVP)

- Username/password authentication
- Known face upload and enrollment
- Photo upload and indexing
- User-scoped data listing (faces and photos)
- Prompt-based semantic search
- Person-aware filtering in query flow
- Image-based search result rendering in UI
- Delete known face functionality
- Delete photo functionality with full cleanup:
- original image
- annotated image
- related summaries and detections (cascade)

## Repository Structure

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
			deletion_service.py
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

## Setup and Run

### Prerequisites

- Python 3.11+
- Supabase project
- Gemini API key

### Installation

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

### Environment

Create .env from .env.example and set at minimum:

- SUPABASE_URL
- SUPABASE_KEY
- SUPABASE_BUCKET
- GEMINI_API_KEY
- GEMINI_LLM_MODEL
- GEMINI_VLM_MODEL
- GEMINI_EMBED_MODEL

### Database

Run SQL schema in Supabase SQL editor:

- [supabase/schema.sql](supabase/schema.sql)

### Start Services

Backend:

```bash
cd backend
python run.py
```

Frontend:

```bash
streamlit run frontend/streamlit_app.py
```

## API Overview

Authentication:

- POST /auth/signup
- POST /auth/login

Ingestion and management:

- GET /ingest/known-faces
- POST /ingest/known-face
- DELETE /ingest/known-face/{known_face_id}
- GET /ingest/photos
- POST /ingest/photo
- DELETE /ingest/photo/{photo_id}
- GET /ingest/photo/{photo_id}/status

Search:

- POST /search

## Strengths of This Approach

1. Identity-semantic separation

- Face recognition is deterministic identity layer.
- Gemini is semantic layer.
- This reduces identity hallucinations.

2. User-scoped ownership model

- All rows are associated with user_id.
- APIs enforce token-scoped access.
- Deletion is ownership-checked.

3. Explainable search results

- Returned results include similarity scores and summary excerpts.
- Debugging retrieval quality is straightforward.

4. Practical MVP architecture

- Fast to iterate and test in real data.
- Streamlit UI accelerates validation before building a production frontend.

5. Data lifecycle control

- Failed indexing cleanup and explicit delete flows reduce stale/duplicate artifacts.

## Scope of Future Improvements

### Retrieval quality

- Threshold calibration using labeled evaluation sets (precision@k, recall@k).
- Better per-person and per-attribute re-ranking.
- Hybrid retrieval combining metadata constraints and vector ranking.

### Face recognition robustness

- Multi-reference enrollment per person.
- Better pose and quality handling for side-angle faces.
- Margin-based identity matching (best vs second-best score gap).

### Performance and scale

- Background job queue for ingestion (async workers).
- Batch embedding and caching strategies.
- Optimized vector indexing strategy for supported dimensions.

### Security hardening

- Row-Level Security policies in Supabase for defense-in-depth.
- Stronger key management and operational hardening.

### Product experience

- Better search explainability in UI.
- Faceted filters (person, time, scene).
- Gallery controls for bulk actions and review workflows.

## Current Status

This repository is an actively evolving MVP. The project already demonstrates end-to-end value for person-aware prompt search over private images and is structured to support iterative improvements in quality, safety, and scale.
