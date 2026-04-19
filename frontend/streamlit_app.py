from __future__ import annotations

import os

import requests
import streamlit as st

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="Image Search MVP", layout="wide")
st.title("Image Search (MVP)")

if "token" not in st.session_state:
    st.session_state.token = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = ""


def auth_headers() -> dict[str, str]:
    token = st.session_state.token
    return {"Authorization": f"Bearer {token}"} if token else {}


def safe_get_json(url: str, timeout: int = 60) -> list[dict]:
    try:
        resp = requests.get(url, headers=auth_headers(), timeout=timeout)
    except requests.RequestException as exc:
        st.warning(f"Could not load data from backend: {exc}")
        return []

    if not resp.ok:
        st.error(resp.text)
        return []

    payload = resp.json()
    return payload if isinstance(payload, list) else []


def get_user_known_faces() -> list[dict]:
    if not st.session_state.token:
        return []
    return safe_get_json(f"{BACKEND_BASE_URL}/ingest/known-faces", timeout=90)


def get_user_photos() -> list[dict]:
    if not st.session_state.token:
        return []
    return safe_get_json(f"{BACKEND_BASE_URL}/ingest/photos", timeout=120)


def delete_known_face(known_face_id: str) -> bool:
    resp = requests.delete(
        f"{BACKEND_BASE_URL}/ingest/known-face/{known_face_id}",
        headers=auth_headers(),
        timeout=60,
    )
    if not resp.ok:
        st.error(resp.text)
        return False
    return True


def delete_photo(photo_id: str) -> bool:
    resp = requests.delete(
        f"{BACKEND_BASE_URL}/ingest/photo/{photo_id}",
        headers=auth_headers(),
        timeout=60,
    )
    if not resp.ok:
        st.error(resp.text)
        return False
    return True


with st.sidebar:
    st.subheader("Authentication")
    mode = st.radio("Mode", ["Login", "Sign Up"], horizontal=True)
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Submit", use_container_width=True):
        endpoint = "/auth/login" if mode == "Login" else "/auth/signup"
        resp = requests.post(
            f"{BACKEND_BASE_URL}{endpoint}",
            json={"username": username, "password": password},
            timeout=60,
        )
        if resp.ok:
            payload = resp.json()
            st.session_state.token = payload["access_token"]
            st.session_state.user_id = payload["user_id"]
            st.success("Authenticated")
        else:
            st.error(resp.text)

    if st.session_state.token:
        st.caption(f"User ID: {st.session_state.user_id}")

known_faces_tab, photos_tab, search_tab = st.tabs(["Known faces", "Photos directory", "Search"])

with known_faces_tab:
    if st.session_state.token:
        st.subheader("Your known faces")
        existing_faces = get_user_known_faces()
        if existing_faces:
            cols = st.columns(5)
            for idx, face in enumerate(existing_faces):
                with cols[idx % 5]:
                    st.caption(face.get("person_name", "unknown"))
                    image_url = face.get("image_url", "")
                    if image_url:
                        st.image(image_url, width=140)
                    st.caption(face.get("id", ""))
                    if st.button("Delete", key=f"delete_known_{face.get('id')}"):
                        if delete_known_face(face.get("id", "")):
                            st.success("Known face deleted")
                            st.rerun()
        else:
            st.info("No known faces found for this user yet")

    st.subheader("Upload known face")
    person_name = st.text_input("Person name", key="known_name")
    known_face_file = st.file_uploader("Face image", type=["jpg", "jpeg", "png"], key="known_file")

    if st.button("Upload known face"):
        if not st.session_state.token:
            st.warning("Login first")
        elif not person_name or not known_face_file:
            st.warning("Provide name and image")
        else:
            files = {"image": (known_face_file.name, known_face_file.getvalue(), known_face_file.type)}
            data = {"person_name": person_name}
            resp = requests.post(
                f"{BACKEND_BASE_URL}/ingest/known-face",
                headers=auth_headers(),
                files=files,
                data=data,
                timeout=120,
            )
            if resp.ok:
                st.success(resp.json()["message"])
                st.rerun()
            else:
                st.error(resp.text)

with photos_tab:
    if st.session_state.token:
        st.subheader("Your uploaded photos")
        existing_photos = get_user_photos()
        if existing_photos:
            grid = st.columns(3)
            for idx, photo in enumerate(existing_photos):
                with grid[idx % 3]:
                    st.caption(f"photo_id: {photo.get('id')}")
                    st.caption(f"status: {photo.get('status')}")
                    preview_url = photo.get("preview_url", "")
                    if preview_url:
                        st.image(preview_url, width=260)
                    if photo.get("error_message"):
                        st.warning(photo.get("error_message"))
                    if st.button("Delete photo", key=f"delete_photo_{photo.get('id')}"):
                        if delete_photo(photo.get("id", "")):
                            st.success("Photo deleted")
                            st.rerun()
        else:
            st.info("No uploaded photos found for this user yet")

    st.subheader("Upload photo")
    photo_file = st.file_uploader("Photo", type=["jpg", "jpeg", "png"], key="photo_file")
    if st.button("Upload photo"):
        if not st.session_state.token:
            st.warning("Login first")
        elif not photo_file:
            st.warning("Choose a file")
        else:
            files = {"image": (photo_file.name, photo_file.getvalue(), photo_file.type)}
            resp = requests.post(
                f"{BACKEND_BASE_URL}/ingest/photo",
                headers=auth_headers(),
                files=files,
                timeout=300,
            )
            if resp.ok:
                payload = resp.json()
                st.success(f"{payload['message']} | photo_id={payload['item_id']}")
                st.rerun()
            else:
                st.error(resp.text)

    st.markdown("Check indexing status")
    status_photo_id = st.text_input("Photo ID", key="status_photo_id")
    if st.button("Get status") and status_photo_id:
        resp = requests.get(
            f"{BACKEND_BASE_URL}/ingest/photo/{status_photo_id}/status",
            headers=auth_headers(),
            timeout=60,
        )
        if resp.ok:
            st.json(resp.json())
        else:
            st.error(resp.text)

with search_tab:
    st.subheader("Prompt search")
    prompt = st.text_area("Search prompt", placeholder="Fetch me all photos of Arman wearing a jacket")
    if st.button("Search"):
        if not st.session_state.token:
            st.warning("Login first")
        elif not prompt.strip():
            st.warning("Enter a prompt")
        else:
            resp = requests.post(
                f"{BACKEND_BASE_URL}/search",
                headers=auth_headers(),
                json={"prompt": prompt},
                timeout=120,
            )
            if resp.ok:
                payload = resp.json()
                st.write(f"Detected person filter: {payload.get('parsed_person_name')}")
                results = payload.get("results", [])
                if not results:
                    st.info("No matching images found")
                cols = st.columns(3)
                for idx, item in enumerate(results):
                    with cols[idx % 3]:
                        image_url = item.get("image_url")
                        if image_url:
                            st.image(image_url, width=280)
                        st.caption(f"photo_id: {item['photo_id']}")
                        st.caption(f"similarity: {item['similarity']:.3f}")
                        st.caption(f"person: {item.get('matched_person')}")
                        st.caption(item.get("summary_excerpt", ""))
            else:
                st.error(resp.text)
