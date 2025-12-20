from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {
        "message": "SEMEFO API Server",
        "status": "running"
    }


@router.get("/health")
def health():
    return {"status": "ok"}
