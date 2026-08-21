from fastapi import APIRouter, Request

router = APIRouter(tags=["status"])


@router.get("/status")
async def status(request: Request) -> dict[str, dict[str, str | int]]:
    '''
    Returns the status of the breakers in the poller.
    '''
    poller = request.app.state.poller
    return {
        name: {
            "state": breaker.state.value,
            "failure_count": breaker.failure_count,
        }
        for name, breaker in poller.breakers().items()
    }
