from django.core.exceptions import ValidationError


def validate_inn(value):
    if not len(value) in (10, 12) or not value.isdigit():
        raise ValidationError("INN must be 12 or 10 digits long and contain only digits")


def validate_kpp(value):
    if not len(value) == 9 or not value.isdigit():
        raise ValidationError("KPP must be 9 digits long")
