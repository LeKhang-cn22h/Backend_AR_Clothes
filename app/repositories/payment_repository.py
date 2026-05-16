from firebase_admin import firestore
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class PaymentRepository:
    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = firestore.client()
        return self._db

    async def update_payment_status(
        self,
        order_id: str,
        payment_status: str,
        transaction_no: Optional[str] = None,
        vnpay_response_code: Optional[str] = None,
    ) -> bool:
        try:
            update_data = {
                "paymentStatus": payment_status,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }
            if transaction_no:
                update_data["vnpayTransactionNo"] = transaction_no
            if vnpay_response_code:
                update_data["vnpayResponseCode"] = vnpay_response_code

            # Nếu paid + đang pending → chuyển sang confirmed
            if payment_status == "paid":
                doc = self.db.collection("orders").document(order_id).get()
                if doc.exists and doc.to_dict().get("status") == "pending":
                    update_data["status"] = "confirmed"

            self.db.collection("orders").document(order_id).update(update_data)
            return True
        except Exception as e:
            logger.error(f"Error updating order {order_id}: {e}")
            return False