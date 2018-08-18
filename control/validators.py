from base.validators import BaseValidator

an = {'allow_none': True}


class DataGetter:
    def __init__(self, s):
        self.data = s.request.data

    def __getitem__(self, item):
        return self.data.get(item, None)


def create_generic_validator(fields):
    class GenericValidator(BaseValidator):
        def is_valid(self):
            data = self.request.data
            for key in data:
                if key in fields:
                    try:
                        fields[key].parse(data[key])
                    except Exception as e:
                        self.code = 400
                        self.message = '"%s" key parse failed, error is "%s"' % (key, e.message)
                        return False
            return True

    return GenericValidator
