from django.core.exceptions import ValidationError

from accounts.validators import validate_id, validate_unix_timestamp, validate_parking_card_id
from base.exceptions import ValidationException
from base.utils import get_logger
from base.validators import BaseValidator, validate_phone_number


class RpsCreateParkingSessionValidator(BaseValidator):
    def is_valid(self):
        get_logger().info("RpsCreateParkingSessionValidator: "+str(self.request.data))
        client_id = self.request.data.get("client_id", None)
        started_at = self.request.data.get("started_at", None)

        parking_id = self.request.data.get("parking_id", None)

        if not parking_id or not client_id or not started_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'session_id', 'parking_id', 'client_id' and 'started_at' are required"
            return False

        try:
            validate_id(parking_id, "parking_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        try:
            validate_id(client_id, "client_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        try:
            validate_unix_timestamp(started_at, "started_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        return True


class RpsUpdateParkingSessionValidator(BaseValidator):
    def is_valid(self):
        get_logger().info("RpsCreateParkingSessionValidator: " + str(self.request.data))
        client_id = self.request.data.get("client_id", None)
        started_at = self.request.data.get("started_at", None)

        parking_id = self.request.data.get("parking_id", None)
        debt = self.request.data.get("debt", None)
        if debt is not None:
            debt = str(debt)
        updated_at = self.request.data.get("updated_at", None)

        if not client_id or not started_at or not parking_id or not debt or not updated_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'client_id', 'started_at', 'parking_id', 'debt' and 'updated_at' are required"
            return False

        try:
            validate_id(client_id, "client_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        try:
            validate_id(parking_id, "parking_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        try:
            float_debt = float(debt)
            if float_debt < 0:
                raise TypeError()
        except (ValueError, TypeError):
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'debt' has invalid format. Must be positive decimal value"
            return False

        try:
            validate_unix_timestamp(started_at, "started_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        try:
            validate_unix_timestamp(updated_at, "updated_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        return True


class RpsCancelParkingSessionValidator(BaseValidator):
    def is_valid(self):
        get_logger().info("RpsCreateParkingSessionValidator: " + str(self.request.data))
        client_id = self.request.data.get("client_id", None)
        started_at = self.request.data.get("started_at", None)

        parking_id = self.request.data.get("parking_id", None)

        if not parking_id or not client_id or not parking_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'parking_id', 'started_at' and 'client_id' are required"
            return False

        try:
            validate_id(parking_id, "parking_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        try:
            validate_id(client_id, "client_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        try:
            validate_unix_timestamp(started_at, "started_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        return True


class RpsCompleteParkingSessionValidator(BaseValidator):
    def is_valid(self):
        get_logger().info("RpsCreateParkingSessionValidator: " + str(self.request.data))
        client_id = self.request.data.get("client_id", None)
        started_at = self.request.data.get("started_at", None)

        parking_id = self.request.data.get("parking_id", None)
        debt = self.request.data.get("debt", None)
        if debt is not None:
            debt = str(debt)
        completed_at = self.request.data.get("completed_at", None)

        if not client_id or not started_at or not parking_id or not debt or not completed_at:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'session_id', 'parking_id', 'debt' and 'completed_at' are required"
            return False

        try:
            validate_id(parking_id, "parking_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        try:
            validate_id(client_id, "client_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        try:
            float_debt = float(debt)
            if float_debt < 0:
                raise TypeError()
        except (ValueError, TypeError):
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'debt' has invalid format. Must be positive decimal value"
            return False

        try:
            validate_unix_timestamp(started_at, "started_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        try:
            validate_unix_timestamp(completed_at, "completed_at")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        return True


class RpsUpdateListParkingSessionValidator(BaseValidator):
    def is_valid(self):
        get_logger().info("RpsCreateParkingSessionValidator: " + str(self.request.data))
        parking_id = self.request.data.get("parking_id", None)
        sessions = self.request.data.get("sessions", None)

        if not parking_id or not sessions:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'parking_id' and 'sessions' are required"
            return False

        try:
            validate_id(parking_id, "parking_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        if type(sessions) != type([]):
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Session value must be list type"
            return False

        for index, session_dict in enumerate(sessions):
            client_id = session_dict.get("client_id", None)
            started_at = session_dict.get("started_at", None)
            debt = session_dict.get("debt", None)
            updated_at = session_dict.get("updated_at", None)

            if not client_id or not started_at or debt is None or not updated_at:
                self.code = ValidationException.VALIDATION_ERROR
                self.message = "Items of session element %s must have 'client_id', 'started_at', 'debt' and 'updated_at' keys" % index
                return False

            try:
                validate_id(client_id, "client_id")
            except ValidationError as e:
                self.code = ValidationException.VALIDATION_ERROR
                self.message = str(e) + "Item %s" % index
                return False

            try:
                float_debt = float(debt)
                if float_debt < 0:
                    raise TypeError()
            except (ValueError, TypeError):
                self.code = ValidationException.VALIDATION_ERROR
                self.message = "Key 'debt' in session item %s has invalid format. Must be positive or zero decimal value" % index
                return False

            try:
                validate_unix_timestamp(started_at, "started_at")
            except ValidationError as e:
                self.code = ValidationException.VALIDATION_ERROR
                self.message = str(e) + "Item %s" % index
                return False

            try:
                validate_unix_timestamp(updated_at, "updated_at")
            except ValidationError as e:
                self.code = ValidationException.VALIDATION_ERROR
                self.message = str(e)+"Item %s" % index
                return False
        return True


class ParkingCardRequestBodyValidator(BaseValidator):
    def is_valid(self):
        get_logger().info("ParkingCardRequestBodyValidator: " + str(self.request.data))
        parking_id = self.request.data.get("parking_id", None)
        card_id = self.request.data.get("card_id", None)
        # phone = self.request.data.get("phone", None)

        if not parking_id or not card_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Keys 'parking_id', 'card_id' are required"
            return False

        try:
            validate_id(parking_id, "parking_id")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        try:
            validate_parking_card_id(card_id)
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        # try:
        #     validate_phone_number(phone)
        # except ValidationError as e:
        #     self.code = ValidationException.VALIDATION_ERROR
        #     self.message = str(e)
        #     return False

        return True


class ParkingCardSessionBodyValidator(BaseValidator):
    def is_valid(self):
        get_logger().info("ParkingCardSessionBodyValidator: " + str(self.request.data))
        card_session = self.request.data.get("card_session", None)

        if not card_session:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'card_session' is required"
            return False

        try:
            validate_id(card_session, "card_session")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        return True

class DeveloperCardSessionBodyValidator(BaseValidator):
    def is_valid(self):
        get_logger().info("DeveloperCardSessionBodyValidator: " + str(self.request.data))
        parking_card_id = self.request.data.get("parking_card_id", None)
        parking_id = self.request.data.get("parking_id", None)
        duration = self.request.data.get("duration", None)
        debt = self.request.data.get("debt", None)
        card_session_id = self.request.data.get("card_session_id", None)

        if not parking_card_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'parking_card_id' is required"
            return False

        if not parking_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'parking_id' is required"
            return False

        if not duration:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'duration' is required"
            return False

        if not debt:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'debt' is required"
            return False

        if not card_session_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'card_session' is required"
            return False

        try:
            validate_id(card_session_id, "card_session")
        except ValidationError as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        return True


class CreateOrGetAccountBodyValidator(BaseValidator):
    def is_valid(self):
        get_logger().info("CreateOrGetAccountBodyValidator: " + str(self.request.data))
        phone = self.request.data.get("phone", None)
        parking_id = self.request.data.get("parking_id", None)

        if not phone or not parking_id:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = "Key 'phone' and 'parking_id' is required"
            return False

        try:
            validate_phone_number(phone)
            validate_id(parking_id, "parking_id")
        except Exception as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False
        return True


class SubscriptionUpdateBodyValidator(BaseValidator):
    def is_valid(self):
        get_logger().info("SubscriptionUpdateBodyValidator: " + str(self.request.data))

        unlimited = self.request.data.get("unlimited", False)

        user_id = self.request.data.get("user_id", None)
        parking_id = self.request.data.get("parking_id", None)
        data = self.request.data.get("data", None)

        name = self.request.data.get("name", None)
        description = self.request.data.get("description", None)
        duration = self.request.data.get("duration", None)
        id_ts = self.request.data.get("id_ts", None)
        id_transition = self.request.data.get("id_transition", None)
        expired_at = self.request.data.get("expired_at", None)

        if unlimited:
            if not all([user_id, parking_id, data]):
                self.code = ValidationException.VALIDATION_ERROR
                self.message = "Keys 'user_id', 'parking_id', 'data' are required"
                return False
        else:
            if not all([user_id, parking_id, name, description, id_ts, id_transition, data]):
                self.code = ValidationException.VALIDATION_ERROR
                self.message = "Keys 'user_id', 'parking_id', 'name', " \
                           "'description', 'id_ts', 'id_transition', 'data' are required"
                return False

            try:
                if duration:
                    validate_id(duration, 'duration')
                if expired_at:
                    validate_unix_timestamp(expired_at, 'expired_at')

            except Exception as e:
                self.code = ValidationException.VALIDATION_ERROR
                self.message = str(e)
                return False

        try:
            validate_id(user_id, 'user_id')
            validate_id(parking_id, 'parking_id')

        except Exception as e:
            self.code = ValidationException.VALIDATION_ERROR
            self.message = str(e)
            return False

        return True
