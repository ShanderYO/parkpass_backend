# Python import
import hashlib
import hmac
import json

# Django import
from django.core.exceptions import ObjectDoesNotExist, ValidationError, FieldDoesNotExist
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from dss.Serializer import serializer

# App import
from base.exceptions import ValidationException, AuthException, PermissionException, ApiException
from base.utils import get_logger, datetime_from_unix_timestamp_tz, parse_int
from base.utils import parse_get_param as parse
from base.validators import ValidatePostParametersMixin, validate_phone_number
from parkpass.settings import REQUESTS_LOGGER_NAME, PAGINATION_OBJECTS_PER_PAGE
from vendors.models import Vendor
from .models import NotifyIssue

_lookups = ('exact', 'iexact', 'contains', 'icontains', 'in', 'gt', 'lt', 'gte', 'lte', 'eq', 'ne'
            'startswith', 'istartswith', 'endswith', 'iendswith', 'range', 'isnull', 'regex', 'iregex',)


class APIView(View, ValidatePostParametersMixin):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        logger = get_logger(REQUESTS_LOGGER_NAME)
        logger.info("Accessing URL '%s'" % request.path)
        if request.method in {'GET', 'DELETE'}:
            logger.info("It's a %s request" % request.method)
        elif request.method in {'POST', 'PUT'}:
            logger.info("%s request content: '%s'" % (request.method, request.body))
        else:
            logger.info("Unrecognized request method")
        # Only application/json Content-type allow
        if not request.META.get('CONTENT_TYPE', "").startswith("application/json") and request.POST:
            return JsonResponse({
                "error": "HTTP Status 415 - Unsupported Media Type"
            }, status=415)

        if request.method in {'POST', 'PUT'}:
            # Parse json-string
            try:
                request.data = json.loads(request.body)
            except Exception as e:
                e = ValidationException(
                    ValidationException.INVALID_JSON_FORMAT,
                    e.message
                )
                return JsonResponse(e.to_dict(), status=400)
            # Validate json-parameters
            if self.validator_class:
                exception_response = self.validate_request(request)
                if exception_response:
                    return exception_response
        try:
            response = super(APIView, self).dispatch(request, *args, **kwargs)
        except ApiException, e:
            return JsonResponse(e.to_dict(), status=e.http_code)
        logger.info("Sending response '%s' with code '%i'" % (response.content, response.status_code))
        return response


class SignedRequestAPIView(APIView):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if not request.META.get('HTTP_X_SIGNATURE', None):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "Signature is empty. [x-signature] header required"
            )
            return JsonResponse(e.to_dict(), status=400)

        if not request.META.get('HTTP_X_VENDOR_NAME', None):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "The vendor name is empty. [x-vendor-name] header required"
            )
            return JsonResponse(e.to_dict(), status=400)

        try:
            request.vendor = Vendor.objects.get(
                name=str(request.META["HTTP_X_VENDOR_NAME"]),
            )
        except ObjectDoesNotExist:
            e = PermissionException(
                PermissionException.VENDOR_NOT_FOUND,
                "Vendor does not exist"
            )
            return JsonResponse(e.to_dict(), status=400)

        signature = hmac.new(str(request.vendor.secret), request.body, hashlib.sha512)

        if request.vendor.account_state == request.vendor.ACCOUNT_STATE.DISABLED:
            e = PermissionException(
                PermissionException.NO_PERMISSION,
                "Account is disabled"
            )
            return JsonResponse(e.to_dict(), status=400)

        if signature.hexdigest() != request.META["HTTP_X_SIGNATURE"].lower():
            e = PermissionException(
                PermissionException.SIGNATURE_INVALID,
                "Invalid signature"
            )
            return JsonResponse(e.to_dict(), status=400)

        return super(SignedRequestAPIView, self).dispatch(request, *args, **kwargs)


class LoginRequiredAPIView(APIView):
    account_type = 'account'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request, self.account_type) or not getattr(request, self.account_type, None):
            auth_exception = AuthException(AuthException.INVALID_TOKEN, "Invalid or empty token")
            return JsonResponse(auth_exception.to_dict(), status=401)
        return super(LoginRequiredAPIView, self).dispatch(request, *args, **kwargs)


def generic_login_required_view(account_model):
    class GenericLoginRequiredAPIView(LoginRequiredAPIView):
        account_type = account_model.__name__.lower()

    # print("DEPRECATED: Will be removed due to optimizing accounting architecture")
    return GenericLoginRequiredAPIView


def type_variative_view(view, type):
    """
    Fabric of account views for specific account type
    :param view: APIView with TypeVariativeViewMixin to specify type of it
    :param type: Type of account
    :return: Generic view for specified account type
    """

    class GenericTypeVariativeView(view):
        __doc__ = view.__doc__
        account_class = type

    return GenericTypeVariativeView


class LoginRequiredFormMultipartView(View, ValidatePostParametersMixin):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):

        # Only multipart/form-data Content-type allow
        if not request.META['CONTENT_TYPE'].startswith("multipart/form-data"):
            return JsonResponse({
                "error": "HTTP Status 415 - Unsupported Media Type"
            }, status=415)

        if request.method == 'POST':
            # Parse json-string
            try:
                request.data = json.loads(request.body)
            except Exception as e:
                e = ValidationException(
                    ValidationException.INVALID_JSON_FORMAT,
                    e.message
                )
                return JsonResponse(e.to_dict(), status=400)

            # Validate json-parameters
            if self.validator_class:
                exception_response = self.validate_request(request)
                if exception_response:
                    return exception_response

        if not request.account:
            auth_exception = AuthException(AuthException.INVALID_TOKEN, "Invalid or empty token")
            return JsonResponse(auth_exception.to_dict(), status=401)
        return super(LoginRequiredFormMultipartView, self).dispatch(request, *args, **kwargs)


class NotifyIssueView(APIView):
    def post(self, request):
        phone = request.data.get('phone', None)
        try:
            validate_phone_number(phone)
        except ValidationError:
            e = ValidationException(ValidationException.VALIDATION_ERROR,
                                    'Invalid phone')
            return JsonResponse(e.to_dict(), status=400)
        NotifyIssue.objects.create(phone=phone)
        return JsonResponse({}, status=200)


class ObjectView(object):
    object = None  # models.Model of necessary object
    readonly_fields = None  # Names of fields that can not be changed
    show_fields = None  # Names of fields to be shown and editable. If empty, all fields will be shown
    hide_fields = None  # Names of fields to be hidden(and readonly)
    author_field = None
    account_filter = None  # field to check owner.
    foreign_field = []
    methods = ('GET', 'POST', 'PUT', 'DELETE')

    def on_delete(self, request, obj):
        pass

    def on_create(self, request, obj):
        pass

    def on_post_create(self, request, obj):
        pass

    def on_edit(self, request, obj):
        pass

    def serialize_obj(self, obj):
        root_item = serializer(obj, include_attr=self.show_fields,
                                exclude_attr=self.hide_fields)
        for key, fields in self.foreign_field:
            inner_item = serializer(
                getattr(obj, key),
                include_attr=fields
            )
            root_item[key] = inner_item
            del root_item[key + "_id"]
        return root_item

    def serialize_list(self, qs):
        result = []
        for o in qs:
            root_item = serializer(o,
                                   include_attr=self.show_fields,
                                   exclude_attr=self.hide_fields)
            for key, fields in self.foreign_field:
                inner_item = serializer(
                    getattr(o, key),
                    include_attr=fields)

                root_item[key] = inner_item
                del root_item[key + "_id"]

            result.append(root_item)
        page = None
        if len(qs) > 0:
            page = str(qs[len(qs) - 1].id)
        return result, page

    def dispatch(self, *args, **kwargs):
        if object is None:
            raise NotImplemented('Object must be specified in self.object')
        if kwargs['request'].method not in self.methods:
            raise PermissionException(PermissionException.NO_PERMISSION, '%s method is not allowed' %
                                      kwargs['request'].method)
        return super(ObjectView, self).dispatch(*args, **kwargs)

    def _account_filter(self, request, queryset):
        if self.account_filter:
            account = request.account
            #######DEPRECATED CODE#######
            for i in {'vendor', 'account', 'owner'}:  # TODO: DEPRECATION
                acc = getattr(request, i, None)
                if acc is not None:
                    account = acc
                    break
            #######DEPRECATED CODE#######
            flt = {self.account_filter: account} if self.account_filter else {}
            return queryset.filter(**flt)
        else:
            return queryset

    def _get_object(self, request, id):
        if id is None:
            return self.object()

        qs = self.object.objects.filter(id=id)
        if len(qs) == 0:
            raise ValidationException(ValidationException.RESOURCE_NOT_FOUND,
                                      "Object with such id wasn't found.")
        qs = self._account_filter(request, qs)

        if len(qs) == 0:
            raise PermissionException(PermissionException.NOT_PRIVELEGIED, "You're not privelegied to see"
                                                                           " this object")
        return qs[0]

    def _get_field_type(self, key):
        lookups = key.split('__')
        lookups = lookups[:-1] if lookups[-1] in _lookups else lookups
        current_model = self.object
        for lookup in lookups[:-1]:
            rel = current_model._meta.get_field(lookup).rel
            if rel is None:
                raise ValidationException(ValidationException.VALIDATION_ERROR, '%s can not be parsed as field' % key)
            current_model = rel.to
        return current_model._meta.get_field(lookups[-1]).__class__.__name__

    @staticmethod
    def _prepare_value(field, value):
        try:
            t = field.__class__.__name__
            value = parse([value])
            if value is None:
                return None
            if t == 'ForeignKey':
                to = field.rel.to
                try:
                    return to.objects.get(id=value)
                except ObjectDoesNotExist:
                    raise ValidationException(ValidationException.RESOURCE_NOT_FOUND,
                                              '%s with ID %s does not exist' %
                                              (field.name, value))
            if t in ('DateField', 'DateTimeField'):
                return datetime_from_unix_timestamp_tz(value)
        except (TypeError, ValueError):
            raise ValidationException(ValidationException.VALIDATION_ERROR, 'Invalid value(%s) for field %s'
                                      % (value, field.name))
        return value

    def _create_or_edit(self, request, id):
        if id is None and request.method == 'PUT':
            raise ValidationException(ValidationException.VALIDATION_ERROR,
                                      'Specify ID to edit object or use POST to create a new one',
                                      http_code=405)
        elif id is not None and request.method == 'POST':
            raise ValidationException(ValidationException.VALIDATION_ERROR,
                                      'Use PUT to edit object',
                                      http_code=405)
        obj = self._get_object(request, id)
        editable_fields = []
        readonly = lambda x: ValidationException(ValidationException.VALIDATION_ERROR,
                                                 'Field %s is read-only' % x.name)
        for field in obj._meta.fields:
            if self.readonly_fields and field.name in self.readonly_fields and request.method == 'PUT' \
                    and field.name in request.data:
                raise readonly(field)
            if field.name == self.author_field and field.name in request.data:
                raise readonly(field)
            if (self.show_fields and field.name not in self.show_fields) or \
                    (self.hide_fields and field.name in self.hide_fields) or \
                    (field.name not in request.data):
                continue
            editable_fields.append(field)

        for field in editable_fields:
            value = self._prepare_value(field, request.data.pop(field.name))
            setattr(obj, field.name, value)

        for key in request.data:
            raise ValidationException(ValidationException.VALIDATION_ERROR,
                                      'No such field: %s' % key)
        if self.author_field and request.method == 'POST':
            account = request.account
            #######DEPRECATED CODE#######
            for i in {'vendor', 'account', 'owner'}:  # TODO: DEPRECATION
                acc = getattr(request, i, None)
                if acc is not None:
                    account = acc
                    break
            #######DEPRECATED CODE#######
            setattr(obj, self.author_field, account)

        if request.method == 'POST':
            self.on_create(request, obj)
        else:
            self.on_edit(request, obj)

        obj.save()
        response_data = self.on_post_create(request, obj)

        """
        try:
            obj.full_clean()
        except ValidationError, e:
            raise ValidationException(ValidationException.VALIDATION_ERROR,
                                      e.message_dict)
        """

        location = request.path if id else request.path + unicode(obj.id) + u'/'

        response = JsonResponse(response_data if response_data else {}, status=200)
        response['Location'] = location
        return response

    def put(self, request, id=None):
        return self._create_or_edit(request, id)

    def post(self, request, id=None):
        return self._create_or_edit(request, id)

    def get(self, request, id=None):
        if id is None:
            data = dict(request.GET)
            flt = {}
            page = data.pop('page', 0)

            # TODO modify it
            if type(page) == list:
                page = parse_int(page[0]) if parse_int(page[0]) else 0

            count = data.pop('count', PAGINATION_OBJECTS_PER_PAGE)
            if type(count) == list:
                count = int(count[0])

            for key, value in data.items():
                key = key.encode('utf-8')
                value = parse(value)
                try:
                    fieldtype = self._get_field_type(key)
                except FieldDoesNotExist:
                    raise ValidationException(ValidationException.VALIDATION_ERROR, 'Invalid filter %s' % key)
                if fieldtype == 'ForeignKey':
                    key = key + '__id'
                elif fieldtype in ('DateField', 'DateTimeField'):
                    value = datetime_from_unix_timestamp_tz(value)
                flt[key.encode('utf-8')] = value

            qs = self._account_filter(request, self.object.objects.filter(**flt))

            # Add id pagination
            if page != 0:
                qs = qs.filter(id__lt=page).order_by('-id')[0:count]
            else:
                qs = qs.filter().order_by('-id')[0:count]

            result, page = self.serialize_list(qs)
            return JsonResponse({'next': page, 'result': result}, status=200)

        else:
            obj = self._get_object(request, id)
            serialized = self.serialize_obj(obj)
            return JsonResponse(serialized, status=200)

    def delete(self, request, id=None):
        if id is None:
            raise ValidationException(ValidationException.VALIDATION_ERROR,
                                      'Specify ID to DELETE object',
                                      http_code=405)
        obj = self._get_object(request, id)
        self.on_delete(request, obj)
        obj.delete()
        return JsonResponse({}, status=200)
