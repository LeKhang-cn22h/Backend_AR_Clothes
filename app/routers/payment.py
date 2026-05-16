from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.repositories.payment_repository import PaymentRepository
from app.services.payment_service import PaymentService
from app.schemas.payment import VNPayCreateRequest, VNPayCreateResponse
from app.config import settings

router = APIRouter(prefix="/payment", tags=["payment"])

def get_service():
    return PaymentService(PaymentRepository())

@router.post("/vnpay/create", response_model=VNPayCreateResponse)
async def create_payment(req: VNPayCreateRequest, request: Request):
    service = get_service()
    ip = request.headers.get("X-Forwarded-For", request.client.host)
    return await service.create_vnpay_url(req, ip.split(",")[0].strip())

@router.get("/vnpay/callback")
async def vnpay_callback(request: Request):
    service = get_service()
    result = await service.handle_callback(dict(request.query_params))
    fe = settings.FE_BASE_URL

    if result["status"] == "success":
        url = f"{fe}/payment/result?status=success&orderId={result['order_id']}&transactionNo={result.get('transaction_no','')}"
    else:
        url = f"{fe}/payment/result?status=failed&orderId={result['order_id']}&message={result.get('message','')}"
    return RedirectResponse(url=url, status_code=302)

@router.get("/vnpay/ipn")
async def vnpay_ipn(request: Request):
    service = get_service()
    result = await service.handle_callback(dict(request.query_params))
    if result["status"] == "success":
        return {"RspCode": "00", "Message": "Confirm Success"}
    return {"RspCode": "97", "Message": "Invalid Checksum"}