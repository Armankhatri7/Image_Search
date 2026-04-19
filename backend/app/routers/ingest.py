from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.routers.deps import get_current_user_id
from app.schemas import IndexingStatus, UploadResponse
from app.services.deletion_service import deletion_service
from app.services.indexing_service import indexing_service
from app.services.supabase_client import supabase_service

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.get("/known-faces")
def list_known_faces(user_id: str = Depends(get_current_user_id)) -> list[dict]:
    rows = supabase_service.select("known_faces", filters={"user_id": user_id})
    rows.sort(key=lambda row: row.get("created_at", ""), reverse=True)

    result: list[dict] = []
    for row in rows:
        image_path = row.get("image_path")
        result.append(
            {
                "id": row.get("id"),
                "person_name": row.get("person_name"),
                "image_path": image_path,
                "image_url": supabase_service.signed_url(image_path) if image_path else "",
                "created_at": row.get("created_at"),
            }
        )

    return result


@router.delete("/known-face/{known_face_id}")
def delete_known_face(known_face_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    deleted = deletion_service.delete_known_face(user_id=user_id, known_face_id=known_face_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Known face not found")
    return {"message": "Known face deleted", "item_id": known_face_id}


@router.delete("/photo/{photo_id}")
def delete_photo(photo_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    deleted = deletion_service.delete_photo(user_id=user_id, photo_id=photo_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    return {"message": "Photo and related data deleted", "item_id": photo_id}


@router.get("/photos")
def list_photos(user_id: str = Depends(get_current_user_id)) -> list[dict]:
    rows = supabase_service.select("photos", filters={"user_id": user_id}, limit=60)
    rows.sort(key=lambda row: row.get("created_at", ""), reverse=True)

    result: list[dict] = []
    for row in rows:
        if row.get("status") == "failed":
            original_path = row.get("original_path")
            annotated_path = row.get("annotated_path")
            if original_path:
                try:
                    supabase_service.remove_file(original_path)
                except Exception:
                    pass
            if annotated_path:
                try:
                    supabase_service.remove_file(annotated_path)
                except Exception:
                    pass
            try:
                supabase_service.delete("photos", {"id": row.get("id"), "user_id": user_id})
            except Exception:
                pass
            continue

        original_path = row.get("original_path")
        result.append(
            {
                "id": row.get("id"),
                "status": row.get("status"),
                "error_message": row.get("error_message"),
                "original_path": original_path,
                "annotated_path": row.get("annotated_path"),
                "preview_url": supabase_service.signed_url(original_path) if original_path else "",
                "created_at": row.get("created_at"),
            }
        )

    return result


@router.post("/known-face", response_model=UploadResponse)
async def upload_known_face(
    person_name: str = Form(...),
    image: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
) -> UploadResponse:
    image_bytes = await image.read()
    try:
        row = indexing_service.upload_known_face(user_id=user_id, person_name=person_name, image_bytes=image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return UploadResponse(message="Known face indexed", item_id=row["id"])


@router.post("/photo", response_model=UploadResponse)
async def upload_photo(
    image: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
) -> UploadResponse:
    image_bytes = await image.read()
    try:
        photo = indexing_service.upload_photo(user_id=user_id, image_bytes=image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return UploadResponse(message="Photo uploaded and indexing started", item_id=photo["id"])


@router.get("/photo/{photo_id}/status", response_model=IndexingStatus)
def get_photo_status(photo_id: str, user_id: str = Depends(get_current_user_id)) -> IndexingStatus:
    rows = supabase_service.select("photos", filters={"id": photo_id, "user_id": user_id}, limit=1)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    row = rows[0]
    return IndexingStatus(
        photo_id=photo_id,
        status=row.get("status", "unknown"),
        error_message=row.get("error_message"),
        updated_at=row.get("updated_at"),
    )
