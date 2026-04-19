from fastapi import APIRouter, Depends, HTTPException, status

from app.routers.deps import get_current_user_id
from app.schemas import SearchRequest, SearchResponse
from app.services.search_service import search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search(payload: SearchRequest, user_id: str = Depends(get_current_user_id)) -> SearchResponse:
    try:
        return search_service.search(user_id=user_id, prompt=payload.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search is temporarily unavailable. Please try again.",
        ) from exc
