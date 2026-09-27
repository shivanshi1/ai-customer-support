from fastapi import APIRouter


router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return the health status of the API."""

    return {"status": "healthy"}
