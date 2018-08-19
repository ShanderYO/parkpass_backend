from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from dss.Serializer import serializer

from base.exceptions import ValidationException
from base.utils import parse_bool, parse_int, parse_float, datetime_from_unix_timestamp_tz


class FieldType:
    def __init__(self, required=False, raise_exception=True):
        self._required = required
        self._raise = raise_exception

    @property
    def is_required(self):
        return self._required

    def parse(self, value):
        return value


class StringField(FieldType):
    def __init__(self, required=False, raise_exception=True, max_length=None):
        self.max_length = max_length
        FieldType.__init__(self, required, raise_exception)

    def parse(self, value):
        if self.max_length is not None:
            if len(str(value)) > self.max_length:
                if self._raise:
                    raise ValueError("Length must be not greater than %s" % self.max_length)
        return str(value)


class IntField(FieldType):
    def parse(self, value):
        return parse_int(value, raise_exception=self._raise)


class PositiveIntField(FieldType):
    def parse(self, value):
        return parse_int(value, raise_exception=self._raise, only_positive=True)


class CustomValidatedField(FieldType):
    def __init__(self, callable, required=False, raise_exception=True):
        self.parser = callable
        FieldType.__init__(self, required, raise_exception)

    def parse(self, value):
        try:
            if value is None and self.is_required:
                raise ValueError("Missing required value")
            return self.parser(value)
        except Exception as e:
            if self._raise:
                raise
            return None


class IntChoicesField(FieldType):
    def __init__(self, choices, required=False, raise_exception=True):
        self._choices = choices
        FieldType.__init__(self, required, raise_exception)

    def parse(self, value):
        if not self.is_required and value is None:
            return None
        if value not in map(lambda x: x[0], self._choices):
            if self._raise:
                raise ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Value %s must be one of %s" % (value, self._choices)
                )
            return None
        return parse_int(value, raise_exception=self._raise)


class BoolField(FieldType):
    def parse(self, value):
        return parse_bool(value, raise_exception=self._raise)


class FloatField(FieldType):
    def parse(self, value):
        return parse_float(value, raise_exception=self._raise)


class PositiveFloatField(FieldType):
    def parse(self, value):
        return parse_float(value, raise_exception=self._raise, only_positive=True)


class DateField(FieldType):
    def parse(self, value):
        return datetime_from_unix_timestamp_tz(parse_int(value, raise_exception=self._raise))


class ForeignField(FieldType):
    def __init__(self, object, required=False, raise_exception=True):
        self._object = object
        FieldType.__init__(self, required, raise_exception)

    def parse(self, value):
        if not value is None:
            return self._object.objects.get(id=value)


def edit_object_view(request, id, object, fields):
    try:
        if id == -1:
            instance = object()
        else:
            instance = object.objects.get(id=id)
    except ObjectDoesNotExist:
        e = ValidationException(
            ValidationException.RESOURCE_NOT_FOUND,
            "Object with such ID not found"
        )
        return JsonResponse(e.to_dict(), status=400)
    try:
        delete = parse_bool(request.data.get("delete", None))
        if delete:
            instance.delete()
            return JsonResponse({}, status=200)
        for field in fields:
            raw = request.data.get(field, None)
            if raw is not None:
                val = fields[field].parse(raw)
                if val is not None:
                    instance.__setattr__(field, val)
            elif fields[field].is_required and id == -1:  # If field is required and action == create
                e = ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    'Field `%s` is required' % field
                )
                return JsonResponse(e.to_dict(), status=400)

    except Exception as exc:
        e = ValidationException(
            ValidationException.VALIDATION_ERROR,
            str(exc)
        )
        return JsonResponse(e.to_dict(), status=400)
    instance.save()

    return JsonResponse(serializer(instance), status=200)
