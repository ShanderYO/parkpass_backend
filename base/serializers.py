class SerializableException(object):
    """
        Mixin-class for serialize API exception logic
    """
    def to_dict(self):
        return {
            "exception": self.exception,
            "code": self.code,
            "message": self.message
        }