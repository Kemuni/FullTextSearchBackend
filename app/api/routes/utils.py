from app.api.base import APIResponseRouter

router = APIResponseRouter(tags=["utils"])


@router.get("/health-check/")
async def health_check():
    return {"status": "ok"}
