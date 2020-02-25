from base.validators import BaseValidator


class TinkoffCallbackValidator(BaseValidator):
    def is_valid(self):

        # TODO validate token or place to Validator
        token = self.request.data.get("Token", None)
        if not token:
            # print("token does not exists")
            return False
        # TODO validate token

        order_id = self.request.data.get("OrderId", None)
        payment_id = self.request.data.get("PaymentId", None)
        amount = self.request.data.get("Amount", None)
        raw_status = self.request.data.get("Status", None)

        if not order_id or not payment_id or not amount or not raw_status:
            # print("Required [order_id, payment_id, amount, raw_status]")
            return False

        try:
            self.request.data["id"] = int(order_id)
            self.request.data["payment_id"] = int(payment_id)
            self.request.data["amount"] = int(amount)

        except Exception:
            # print("Not int [order_id, payment_id or amount]")
            return False

        if raw_status not in ["AUTHORIZED", "CONFIRMED", "REVERSED",
                              "REFUNDED", "PARTIAL_REFUNDED", "REJECTED"]:
            # print("Invalid input status")
            return False

        success = self.request.data.get("Success", None)
        error_code = self.request.data.get("ErrorCode", None)

        if not success or not error_code:
            # print("success or error_code are required")
            return False

        return True