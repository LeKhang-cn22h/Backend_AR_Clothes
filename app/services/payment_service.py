import stripe
from app.config import settings
from app.schemas.payment import StripeCreateRequest, StripeCreateResponse
from app.repositories.payment_repository import PaymentRepository

stripe.api_key = settings.STRIPE_SECRET_KEY

class PaymentService:
    def __init__(self, repo: PaymentRepository):
        self.repo = repo

    async def create_stripe_session(self, req: StripeCreateRequest) -> StripeCreateResponse:
        # Convert VND → USD (1 USD ≈ 25,000 VND), tối thiểu 50 cents
        amount_usd_cents = max(int((req.amount / 25000) * 100), 50)

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": req.order_desc,
                    },
                    "unit_amount": amount_usd_cents,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=(
                f"http://localhost:8000/payment/stripe/success"
                f"?session_id={{CHECKOUT_SESSION_ID}}&orderId={req.order_id}"
            ),
            cancel_url=(
                f"{settings.FE_BASE_URL}/payment/result"
                f"?status=failed&orderId={req.order_id}"
            ),
            metadata={"order_id": req.order_id},
        )

        await self.repo.save_stripe_session(
            order_id=req.order_id,
            session_id=session.id,
        )

        return StripeCreateResponse(payment_url=session.url)

    async def handle_success(self, session_id: str, order_id: str) -> dict:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                await self.repo.update_payment_status(
                    order_id=order_id,
                    payment_status="paid",
                    transaction_no=session.payment_intent,
                )
                return {"status": "success", "order_id": order_id}
            return {"status": "failed", "order_id": order_id, "message": "Chưa thanh toán"}
        except Exception as e:
            return {"status": "failed", "order_id": order_id, "message": str(e)}