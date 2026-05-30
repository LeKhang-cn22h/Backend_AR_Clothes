from fastapi import APIRouter, Request, Query
from fastapi.responses import RedirectResponse
from app.repositories.payment_repository import PaymentRepository
from app.services.payment_service import PaymentService
from app.schemas.payment import StripeCreateRequest, StripeCreateResponse
from app.config import settings
import stripe
from core.limiter import limiter

router = APIRouter(prefix="/payment", tags=["payment"])

def get_service():
    return PaymentService(PaymentRepository())

@router.post("/stripe/create", response_model=StripeCreateResponse)
@limiter.limit("120/minute")
async def create_stripe_payment(req: StripeCreateRequest):
    service = get_service()
    return await service.create_stripe_session(req)

@router.get("/stripe/success")
@limiter.limit("120/minute")
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
@router.get("/stripe/payments")
@limiter.limit("120/minute")
async def get_stripe_payments(limit: int = Query(default=10, le=100)):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    payment_intents = stripe.PaymentIntent.list(limit=limit)

    result = []
    for p in payment_intents.data:
        metadata = dict(p.metadata) if p.metadata else {}
        order_id = metadata.get("order_id", "")

        payment_method_details = None
        if p.payment_method:
            try:
                pm = stripe.PaymentMethod.retrieve(p.payment_method)
                if pm.card:
                    payment_method_details = {
                        "brand": pm.card.brand,
                        "last4": pm.card.last4,
                    }
            except Exception:
                pass

        result.append({
            "id": p.id,
            "amount": p.amount / 100,
            "amount_vnd": int(p.amount / 100 * 25000),
            "currency": p.currency.upper(),
            "status": p.status,
            "order_id": order_id,
            "created": p.created,
            "payment_method_details": payment_method_details,
        })

    return {"data": result, "total": len(result)}
@router.get("/stripe/payments/{payment_intent_id}")
@limiter.limit("120/minute")
async def get_stripe_payment_detail(payment_intent_id: str):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        p = stripe.PaymentIntent.retrieve(payment_intent_id)
        metadata = dict(p.metadata) if p.metadata else {}
        order_id = metadata.get("order_id", "")

        charge = None
        if p.latest_charge:
            charge = stripe.Charge.retrieve(p.latest_charge)

        return {
            "id": p.id,
            "amount": p.amount / 100,
            "amount_vnd": int(p.amount / 100 * 25000),
            "currency": p.currency.upper(),
            "status": p.status,
            "order_id": order_id,
            "created": p.created,
            "receipt_url": charge.receipt_url if charge else None,
            "payment_method_details": {
                "brand": charge.payment_method_details.card.brand if charge else None,
                "last4": charge.payment_method_details.card.last4 if charge else None,
                "exp_month": charge.payment_method_details.card.exp_month if charge else None,
                "exp_year": charge.payment_method_details.card.exp_year if charge else None,
            } if charge else None,
            "billing_details": {
                "name": charge.billing_details.name if charge else None,
                "email": charge.billing_details.email if charge else None,
            } if charge else None,
        }
    except stripe.error.StripeError as e:
        return {"error": str(e)}