from firebase_admin import credentials, firestore as fs
import firebase_admin
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def _get_firestore():
    if not firebase_admin._apps:
        base = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base, "serviceAccountKey.json"),
            os.path.join(base, "..", "serviceAccountKey.json"),
        ]
        key_path = next((p for p in candidates if os.path.exists(p)), None)
        if not key_path:
            raise FileNotFoundError("Không tìm thấy serviceAccountKey.json")
        firebase_admin.initialize_app(credentials.Certificate(os.path.abspath(key_path)))
    return fs.client()


class PaymentRepository:
    def __init__(self):
        self._db = None

    @property
    def db(self):
        if self._db is None:
            self._db = _get_firestore()  
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
                "updatedAt": fs.SERVER_TIMESTAMP,
            }
            if transaction_no:
                update_data["stripePaymentIntent"] = transaction_no
            if payment_status == "paid":
                doc = self.db.collection("orders").document(order_id).get()
                if doc.exists and doc.to_dict().get("status") == "pending":
                    update_data["status"] = "confirmed"
            self.db.collection("orders").document(order_id).update(update_data)
            return True
        except Exception as e:
            logger.error(f"Error updating order {order_id}: {e}")
            return False

    async def save_stripe_session(self, order_id: str, session_id: str) -> bool:
        try:
            self.db.collection("orders").document(order_id).update({
                "stripeSessionId": session_id,
                "updatedAt": fs.SERVER_TIMESTAMP,
            })
            return True
        except Exception as e:
            logger.error(f"Error saving stripe session {order_id}: {e}")
            return False