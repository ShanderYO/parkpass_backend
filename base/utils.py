# -*- coding: utf-8 -*-
import json
import logging
import re
import time
import datetime

import pytz
from django.core.exceptions import ObjectDoesNotExist, FieldError
from django.http import JsonResponse
from django.utils import timezone
from django_elasticsearch.client import es_client

from dss.Serializer import serializer

from base.exceptions import ValidationException
from parkpass_backend.settings import BASE_LOGGER_NAME
from parkpass_backend.settings import PAGINATION_OBJECTS_PER_PAGE


def strtobool(s):
    if s.lower() == 'true':
        return True
    if s.lower() == 'false':
        return False
    raise ValueError('%r must be "true" or "false"' % s)


def generic_pagination_view(obj, view_base_class, filter_by_account=False, account_field=None, exclude_attr=()):
    class GenericPaginationView(view_base_class):
        def get(self, request):
            # Кучка непонятного кода, потому что "Rest Framework связывает нас по рукам и ногам, с нуля проще"
            filter = {}
            data = dict(request.GET)  # Кастуем в словарь, чтобы можно было удалять элементы

            for key in data:  # Кастуем в инт все числовые значения, остальные в str
                values = data[key]
                data.pop(key)
                key = key.encode('utf-8')
                data[key] = []
                for value in values:
                    data[key].append(int(value) if value.isdigit() else value.encode('utf-8'))

            page = int(data.pop('page', 0))
            count = int(data.pop('count', PAGINATION_OBJECTS_PER_PAGE))

            for key in data:
                try:
                    if hasattr(obj, key):  # Если указано название существующего поля
                        attr, modifier = key, 'eq'  # То мы сравниваем точное значение
                        first_attr = attr
                    else:
                        _ = key.split('__')  # Иначе ловим модификатор
                        attr, modifier = '__'.join(_[:-1]), _[-1]
                        first_attr = _[0]
                    if modifier not in ('eq', 'gt', 'lt', 'ne', 'ge',
                                        'le', 'in', 'tlt', 'tgt') or not hasattr(obj, first_attr):
                        raise ValueError()
                    if data[key][0] in {'True', 'False', 'true', 'false'}:
                        # Кастуем значение в bool, если оно таковым является
                        if modifier == 'eq':
                            filter[attr] = strtobool(data[key][0])
                        elif modifier == 'ne':
                            filter[attr] = not strtobool(data[key][0])
                        else:
                            raise ValueError()
                    else:
                        if modifier == 'eq':
                            filter[attr] = data[key][0]
                        elif modifier == 'in':
                            filter[attr + '__in'] = data[key]
                        elif modifier in ('tlt', 'tgt'):
                            # Для дат используем отдельные модификаторы, так как это реально проще,
                            # чем дёргать с модели поле для проверки типа(которое может ссылаться и на другую модель)
                            filter[attr + '__' + modifier[1:]] = datetime_from_unix_timestamp_tz(int(data[key][0]))
                        else:
                            filter[attr + '__' + modifier] = data[key][0]
                except (ValueError, FieldError):
                    e = ValidationException(
                        ValidationException.VALIDATION_ERROR,
                        "Invalid filter format"
                    )
                    return JsonResponse(e.to_dict(), status=400)
            account_dict = {}
            if filter_by_account:  # Если необходимо, фильтруем объекты по аккаунту пользователя, запросившего их
                for i in {'vendor', 'account', 'owner'}:  # TODO: DEPRECATION
                    account = getattr(request, i, None)
                    if account is not None:
                        _ = account_field if account_field else i
                        account_dict = {_: account}
                        break
            filter.update(account_dict)
            objects = obj.objects.filter(**filter)
            result = []
            for o in objects:
                result.append(serializer(o, exclude_attr=exclude_attr))
            length = len(result)
            if length > count:  # Пагинация
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


def parse_timestamp_utc(value):
    int_val = parse_int(value)
    if int_val:
        int_val += 60 * 60 * 3 # Timezome MSK
    return int_val


def get_today_end_datetime():
    td = datetime.date.today()
    end_time = datetime.time(23,59,59)
    return datetime.datetime.combine(td, end_time)


def parse_get_param(param):
    result = []
    for key in param:
        if not isinstance(key, unicode) and not isinstance(key, str):
            result.append(key)
        elif key[0] == u'"' and key[-1] == u'"':  # String
            result.append(key.encode('utf-8')[1:-1])
        elif key.isdecimal():  # Int
            result.append(int(key))
        elif re.match(r'^[0-9.]+$', key):  # Float
            result.append(float(key))
        elif key.lower() == u'true':
            result.append(True)
        elif key.lower() == u'false':
            result.append(False)
        else:
            result.append(key.encode('utf-8'))
    return result if len(result) != 1 else result[0]


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


def clear_phone(phone):
    return phone \
        .replace('+', '') \
        .replace('(', '') \
        .replace(')', '') \
        .replace(' ', '') \
        .replace('-', '') \


def datetime_from_unix_timestamp_tz(value):
    if value is None:
        return None
    started_at_date = datetime.datetime.fromtimestamp(float(value))
    return pytz.utc.localize(started_at_date)


def datetime_to_unix_timestamp_tz(value):
    if value is None:
        return None
    return int(time.mktime(value.timetuple()))


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
        if parse_int(value) not in map(lambda x: x[0], self._choices):
            if self._raise:
                raise ValidationException(
                    ValidationException.VALIDATION_ERROR,
                    "Value %r must be one of %s" % (value, self._choices)
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


def edit_object_view(request, id, object, fields, incl_attr=None, req_attr=None, create=False, edit=True):
    """
    Generic object editing API view
    :param request: pass request
    :param id: ID of object, -1 to create new one
    :param object: DB Model of object
    :param fields: dict of fields with types
    :param incl_attr: What attributes to show via serializer
    :param req_attr: Dict of model attrs to be specified in getter and set to new objects
    """
    return_code = 200
    if req_attr is None:
        req_attr = {}
    try:
        if id == -1:
            instance = object()
            for attr, value in req_attr.items():
                instance.__setattr__(attr, value)
            return_code = 201
        else:
            if create:
                instance, created = object.objects.get_or_create(id=id, **req_attr)
                if not created and not edit:
                    e = ValidationException(ValidationException.ALREADY_EXISTS, 'Use PUT to edit existing objects')
                    return JsonResponse(e.to_dict(), status=409)
            else:
                instance = object.objects.get(id=id, **req_attr)
    except ObjectDoesNotExist:
        e = ValidationException(
            ValidationException.RESOURCE_NOT_FOUND,
            "Object with such ID not found"
        )
        return JsonResponse(e.to_dict(), status=400)
    try:
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

    except ValidationException as exc:
        return JsonResponse(exc.to_dict(), status=400)
    instance.full_clean()
    instance.save()
    # TODO: Fix showing str's
    return JsonResponse(serializer(instance, include_attr=incl_attr), status=return_code)


def elastic_log(index, message, data):
    from datetime import datetime

    body_dict = {
        "timestamp": datetime.now(),
        "message": message,
        "data": data
    }
    try:
        es_client.index(
            index=index,
            body=body_dict,
        )
    except Exception as e:
        get_logger(BASE_LOGGER_NAME).warning(str(e))
