from . serializers import SerializableException


class ApiException(Exception, SerializableException):
    """
        Base class for all API-exceptions
    """

    def __init__(self, message, code=400):
        super(Exception, self).__init__(message)
        self.exception = self.__class__.__name__
        self.http_code = code


class AuthException(ApiException):
    """
        Authorization user API-exception
    """
    NOT_FOUND_CODE = 100
    INVALID_PASSWORD = 101
    INVALID_TOKEN = 102
    INVALID_SESSION = 103
    INVALID_EXTERNAL_USER = 104
    EXTERNAL_LOGIN_ERROR = 105
    INVALID_TOKEN_FORMAT = 106

    def __init__(self, code, message, http_code=400):
        super(AuthException, self).__init__(message, http_code)
        self.code = code


class NetworkException(ApiException):
    """
        Third-party services disable API-exception
    """
    SMS_GATEWAY_DISABLE = 200
    SMS_GATEWAY_NOT_AVAILABLE = 201
    SMD_GATEWAY_ERROR = 202

    def __init__(self, code, message, http_code=400):
        super(NetworkException, self).__init__(message, http_code)
        self.code = code


class PermissionException(ApiException):
    """
    User permission denial API-exception
    """
    SIGNATURE_INVALID = 300
    NO_PERMISSION = 301
    ONLY_ONE_CARD = 302
    VENDOR_NOT_FOUND = 303
    ONLY_ONE_ACTIVE_SESSION_REQUIRED = 304
    CREDIT_CARD_REQUIRED = 305
    EMAIL_REQUIRED = 306
    NOT_PRIVELEGIED = 307
    FORBIDDEN_CHANGING = 308

    def __init__(self, code, message, http_code=400):
        super(PermissionException, self).__init__(message, http_code)
        self.code = code


class ValidationException(ApiException):
    """
        Input user data validation failed API-exception
    """

    VALIDATION_ERROR = 400
    INVALID_JSON_FORMAT = 401
    RESOURCE_NOT_FOUND = 402
    ALREADY_EXISTS = 403
    INVALID_IMAGE = 404  # Image doesn't meet conditions(e.g. size lt 300x300)
    EMAIL_ALREADY_USED = 405
    INVALID_RESOURCE_STATE = 406
    ACTION_UNAVAILABLE = 407

    # Raised when input data is not valid json object
    UNKNOWN_VALIDATION_CODE = 499

    def __init__(self, code, message, http_code=400):
        super(ValidationException, self).__init__(message, http_code)
        self.code = code


class PaymentException(ApiException):
    """
        Payment gateway exceptions
    """
    BAD_PAYMENT_GATEWAY = 600
    EXCEPTION_3DS_NOT_AUTH = 601
    EXCEPTION_DENIED_FROD_MONITOR = 602
    EXCEPTION_DENIED_INVALID_CARD = 603
    EXCEPTION_INVALID_REPEAT_LATER = 604
    EXCEPTION_BANK_OPERATION_DENIED = 605
    EXCEPTION_MANY_MONEY = 606
    EXCEPTION_INTERNAL_ERROR = 607

    def __init__(self, code, message, http_code=400):
        super(PaymentException, self).__init__(message, http_code)
        self.code = code