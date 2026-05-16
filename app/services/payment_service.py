import hashlib, hmac, urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import VNPayCreateRequest, VNPayCreateResponse
from app.config import settings

def _hmac_sha512(secret: str, data: str) -> str:
    return hmac.new(secret.encode(), data.encode(), hashlib.sha512).hexdigest()

class PaymentService:
    def __init__(self, repo: PaymentRepository):
        self.repo = repo

    async def create_vnpay_url(self, req: VNPayCreateRequest, client_ip: str) -> VNPayCreateResponse:
        now_vn = datetime.now(timezone(timedelta(hours=7)))
        create_date = now_vn.strftime("%Y%m%d%H%M%S")
        txn_ref = f"{req.order_id}_{create_date}"

        params = {
            "vnp_Version": "2.1.0",
            "vnp_Command": "pay",
            "vnp_TmnCode": settings.VNPAY_TMN_CODE,
            "vnp_Amount": str(int(req.amount * 100)),
            "vnp_CreateDate": create_date,
            "vnp_CurrCode": "VND",
            "vnp_IpAddr": client_ip,
            "vnp_Locale": "vn",
            "vnp_OrderInfo": req.order_desc,
            "vnp_OrderType": "other",
            "vnp_ReturnUrl": settings.VNPAY_RETURN_URL,
            "vnp_TxnRef": txn_ref,
        }
        if req.bank_code:
            params["vnp_BankCode"] = req.bank_code

        sorted_params = sorted(params.items())
        raw_data = "&".join(f"{k}={v}" for k, v in sorted_params)
        query_string = "&".join(f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in sorted_params)
        secure_hash = _hmac_sha512(settings.VNPAY_HASH_SECRET, raw_data)

        return VNPayCreateResponse(
            payment_url=f"{settings.VNPAY_URL}?{query_string}&vnp_SecureHash={secure_hash}"
        )

    async def handle_callback(self, params: dict) -> dict:
        vnp_secure_hash = params.pop("vnp_SecureHash", "")
        params.pop("vnp_SecureHashType", None)

        sorted_params = sorted(params.items())
        raw_data = "&".join(f"{k}={v}" for k, v in sorted_params)
        expected = _hmac_sha512(settings.VNPAY_HASH_SECRET, raw_data)

        if not hmac.compare_digest(vnp_secure_hash.lower(), expected.lower()):
            return {"status": "failed", "order_id": "unknown", "message": "Sai chữ ký"}

        response_code = params.get("vnp_ResponseCode", "")
        txn_ref = params.get("vnp_TxnRef", "")
        transaction_no = params.get("vnp_TransactionNo", "")
        order_id = txn_ref.rsplit("_", 1)[0] if "_" in txn_ref else txn_ref

        if response_code == "00":
            await self.repo.update_payment_status(
                order_id=order_id,
                payment_status="paid",
                transaction_no=transaction_no,
                vnpay_response_code=response_code,
            )
            return {"status": "success", "order_id": order_id, "transaction_no": transaction_no}
        else:
            await self.repo.update_payment_status(
                order_id=order_id,
                payment_status="unpaid",
                vnpay_response_code=response_code,
            )
            return {"status": "failed", "order_id": order_id, "message": f"Mã lỗi: {response_code}"}