from fastapi import APIRouter

router = APIRouter()

@router.get("/health", summary="API检查")
def health_check():
    return {"status": "ok"}
