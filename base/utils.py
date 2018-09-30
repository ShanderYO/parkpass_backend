import datetime
import logging

import pytz
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from dss.Serializer import serializer

from base.exceptions import ValidationException
from parkpass.settings import BASE_LOGGER_NAME
from parkpass.settings import PAGINATION_OBJECTS_PER_PAGE


def generic_pagination_view(obj, view_base_class, filter_by_account=False, account_field=None):
    class GenericPaginationView(view_base_class):
        def post(self, request, page):
            filter = {}
            for key in request.data:
                try:
                    attr, modifier = key.split('__') if not hasattr(obj, key) else (key, 'eq')
                    if modifier not in ('eq', 'gt', 'lt', 'ne', 'ge', 'le', 'in') or not hasattr(obj, attr):
                        raise ValueError()
                    if isinstance(request.data[key], bool):
                        if modifier == 'eq':
                            filter[attr] = request.data[key]
                        elif modifier == 'ne':
                            filter[attr] = not request.data[key]
                        else:
                            raise ValueError()
                    else:
                        if modifier == 'eq':
                            filter[attr] = request.data[key]
                        else:
                            filter[attr + '__' + modifier] = request.data[key]
                except ValueError:
                    e = ValidationException(
                        ValidationException.VALIDATION_ERROR,
                        "Invalid filter format"
                    )
                    return JsonResponse(e.to_dict(), status=400)
            account_dict = {}
            if filter_by_account:
                for i in {'vendor', 'account', 'owner'}:
                    account = getattr(request, i, None)
                    if account != None:
                        _ = account_field if account_field else i
                        account_dict = {_: account}
            if filter:
                filter.update(account_dict)
                objects = obj.objects.filter(**filter)
            else:
                objects = obj.objects.filter(**account_dict)
            page = int(page)
            result = []
            for o in objects:
                result.append(serializer(o))
            length = len(result)
            count = PAGINATION_OBJECTS_PER_PAGE
            if length > count:
                result = result[page * count:(page + 1) * count]
            return JsonResponse({'count': length, 'objects': result}, status=200)

    return GenericPaginationView


def get_logger(name=BASE_LOGGER_NAME):
    return logging.getLogger(name)


def parse_int(value, raise_exception=False, allow_none=True, only_positive=False):
    if not allow_none and value is None:
        raise ValueError('Required field isn\'t specified')
    if value is None and raise_exception:
        return None
    try:
        if int(value) < 0 and only_positive:
            raise ValueError("Only positive integers allowed")
        return int(value)
    except Exception:
        if raise_exception:
            raise
        return None


def parse_bool(value, raise_exception=False, allow_none=True):
    if not allow_none and value is None:
        raise ValueError('Required field isn\'t specified')
    if value is None and raise_exception:
        return None
    v = str(value).lower()
    if v in ('1', 'true'):
        return True
    elif v in ('0', 'false'):
        return False
    if raise_exception:
        raise ValueError('Boolean value must be `1`, `0`, `true` or `false`')
    return None


def parse_float(value, raise_exception=False, allow_none=True, only_positive=False):
    if not allow_none and value is None:
        raise ValueError('Required field isn\'t specified')
    if value is None and raise_exception:
        return None
    try:
        if float(value) < 0 and only_positive:
            raise ValueError("Only positive floats allowed")
        return float(value)
    except Exception:
        if raise_exception:
            raise
        return None


def datetime_from_unix_timestamp_tz(value):
    if value is None:
        return None
    started_at_date = datetime.datetime.fromtimestamp(value)
    return pytz.utc.localize(started_at_date)


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


def edit_object_view(request, id, object, fields, incl_attr=None, req_attr=None):
    """
    Generic object editing API view
    :param request: pass request
    :param id: ID of object, -1 to create new one
    :param object: DB Model of object
    :param fields: dict of fields with types
    :param incl_attr: What attributes to show via serializer
    :param req_attr: Dict of model attrs to be specified in getter and set to new objects
    """
    if req_attr is None:
        req_attr = {}
    try:
        if id == -1:
            instance = object()
            for attr, value in req_attr.items():
                instance.__setattr__(attr, value)
        else:
            instance = object.objects.get(id=id, **req_attr)
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

    return JsonResponse(serializer(instance, include_attr=incl_attr), status=200)
