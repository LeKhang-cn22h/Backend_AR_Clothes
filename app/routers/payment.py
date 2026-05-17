from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.repositories.payment_repository import PaymentRepository
from app.services.payment_service import PaymentService
from app.schemas.payment import StripeCreateRequest, StripeCreateResponse
from app.config import settings

router = APIRouter(prefix="/payment", tags=["payment"])

def get_service():
    return PaymentService(PaymentRepository())

@router.post("/stripe/create", response_model=StripeCreateResponse)
async def create_stripe_payment(req: StripeCreateRequest):
    service = get_service()
    return await service.create_stripe_session(req)

@router.get("/stripe/success")
async def stripe_success(session_id: str, orderId: str):
    service = get_service()
    result = await service.handle_success(session_id, orderId)
    fe = settings.FE_BASE_URL
    if result["status"] == "success":
        return RedirectResponse(
            url=f"{fe}/payment/result?status=success&orderId={orderId}",
            status_code=302
        )
    return RedirectResponse(
        url=f"{fe}/payment/result?status=failed&orderId={orderId}&message={result.get('message','')}",
        status_code=302
    )