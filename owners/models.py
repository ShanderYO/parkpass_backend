import os
import re
import time

import datetime
import uuid

from PIL import Image
from adminsortable.models import SortableMixin
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail
from django.dispatch import receiver
from jose import jwt

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from rest_framework import serializers

from base.exceptions import ValidationException
from base.models import BaseAccount, BaseAccountSession, BaseAccountIssue
from base.validators import validate_phone_number, comma_separated_emails
from owners.validators import validate_inn, validate_kpp
from parkings.models import Parking
from parkpass_backend.settings import ZENDESK_WIDGET_SECRET, EMAIL_HOST_USER, MEDIA_ROOT, BASE_DIR
from payments.models import InvoiceWithdraw
from django import forms


class Owner(BaseAccount):
    name = models.CharField(max_length=255, unique=True)

    @property
    def session_class(self):
        return OwnerSession

    @property
    def type(self):
        return 'owner'

    def get_or_create_jwt_for_zendesk_widget(self):
        return self.get_or_create_jwt_for_zendesk(ZENDESK_WIDGET_SECRET)

    def get_or_create_jwt_for_zendesk(self, secret):
        timestamp = int(time.mktime(datetime.datetime.now().timetuple()))
        payload = {
            'name': self.name,
            'email': self.email,
            'jti': self.id,
            'iat': timestamp
        }
        return jwt.encode(payload, secret, algorithm='HS256')

    def create_password_and_send_mail(self):
        raw_password = self.generate_random_password()
        self.set_password(raw_password)
        self.save()
        self.send_recovery_password_owner_mail(raw_password)

    def save(self, *args, **kwargs):
        if not self.id and Owner.objects.filter(email=self.email).exists():
            try:
                1 / 0
            except ZeroDivisionError as e:
                raise Exception('Owner with this email exists') from e
        else:
            super(Owner, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'Company owner'
        verbose_name_plural = 'Company owners'


# @receiver(models.signals.post_save, sender=Owner)
# def execute_after_save(sender, instance, created, *args, **kwargs):
#     if created:
#         if instance.email:
#             raw_password = instance.generate_random_password()
#             instance.set_password(raw_password)
#             instance.save()
#             instance.send_owner_password_mail(raw_password)
class OwnerSession(BaseAccountSession):
    owner = models.OneToOneField(Owner, on_delete=models.CASCADE)

    @classmethod
    def get_account_by_token(cls, token):
        try:
            session = cls.objects.get(token=token)
            if session.is_expired():
                session.delete()
                return None
            return session.owner

        except ObjectDoesNotExist:
            return None


class OwnerIssue(BaseAccountIssue):
    def save(self, *args, **kwargs):
        if not self.id:
            self.type = BaseAccountIssue.OWNER_ISSUE_TYPE
        super(OwnerIssue, self).save(*args, **kwargs)

    def accept(self):
        owner = Owner(
            phone=self.phone,
            email=self.email,
            name=self.name,
        )
        owner.full_clean()
        owner.save()
        owner.create_password_and_send()
        self.delete()
        return owner


class Company(models.Model):
    owner = models.ForeignKey(to=Owner, null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=256)
    inn = models.CharField(max_length=15, validators=(validate_inn,), null=True, blank=True)
    kpp = models.CharField(max_length=15, validators=(validate_kpp,), null=True, blank=True)

    bic = models.CharField(max_length=20, null=True, blank=True)
    bank = models.CharField(max_length=256, null=True, blank=True)
    account = models.CharField(max_length=64, null=True, blank=True)

    legal_address = models.CharField(max_length=512)
    actual_address = models.CharField(max_length=512)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True, validators=(validate_phone_number,))
    use_profile_contacts = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def get_parking_queryset(self):
        return Parking.objects.filter(company=self)


class OwnerApplication(models.Model):
    TYPE_CONNECT_PARKING = 1
    TYPE_SOFTWARE_UPDATE = 2
    TYPE_INSTALL_READER = 3

    types = (
        (TYPE_CONNECT_PARKING, "Connect parking"),
        (TYPE_SOFTWARE_UPDATE, "Software update"),
        (TYPE_INSTALL_READER, "Install readers")
    )
    statuses = (
        (1, "New"),
        (2, "Processing"),
        (3, "Processed"),
        (4, "Cancelled")
    )
    type = models.PositiveSmallIntegerField(choices=types)

    owner = models.ForeignKey(to=Owner, on_delete=models.CASCADE, null=True, blank=True)
    parking = models.ForeignKey(to='parkings.Parking', on_delete=models.CASCADE, null=True, blank=True)
    vendor = models.ForeignKey(to='vendors.Vendor', on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey(to=Company, on_delete=models.CASCADE, null=True, blank=True)

    contact_email = models.EmailField(null=True, blank=True)
    contact_phone = models.CharField(max_length=13, null=True, blank=True)

    description = models.CharField(max_length=1000)
    status = models.PositiveSmallIntegerField(choices=statuses, default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Application #%s " % self.pk


class CompanySettingReports(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    parking = models.ForeignKey(Parking, on_delete=models.CASCADE)
    available = models.BooleanField(default=True)
    report_emails = models.TextField(validators=(comma_separated_emails,), null=True, blank=True)
    period_in_days = models.IntegerField(default=30)
    last_send_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'report_settings'

    def __str__(self):
        return "Report settings for %s %s" % (self.company, self.parking)


class CompanyReport(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    filename = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    invoice_withdraw = models.ForeignKey(
        to=InvoiceWithdraw, on_delete=models.CASCADE,
        null=True, blank=True)

    class Meta:
        db_table = 'owner_report'

    def __str__(self):
        return "Report for %s [%s]" % (self.company, self.created_at)


# Модели для работы с Valet
# ........................................................................................................

class CompanyUsersPermissionCategory(models.Model):  # категория права
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        verbose_name_plural = 'Company users permission categories'

    def __str__(self):
        return self.name


class CompanyUsersPermission(SortableMixin):  # само право
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    slug = models.CharField(max_length=255)
    category = models.ForeignKey(CompanyUsersPermissionCategory, on_delete=models.CASCADE)
    position = models.PositiveIntegerField(default=0, editable=False)

    def set_default_permissions_for_all_roles(self):
        roles = CompanyUsersRole.objects.all()
        for role in roles:
            CompanyUsersRolePermission.objects.create(
                permission=self,
                role=role
            )

    class Meta:
        ordering = ('position',)

    def __str__(self):
        return f"{self.category.name}. {self.name}"


@receiver(models.signals.post_save, sender=CompanyUsersPermission)
def execute_after_save3(sender, instance, created, *args, **kwargs):
    if created:
        instance.set_default_permissions_for_all_roles()


class CompanyUsersPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyUsersPermission
        fields = [
            'id', 'name', 'slug', 'category', 'position'
        ]


class CompanyUsersRolePermission(models.Model):  # связующая таблица
    id = models.AutoField(primary_key=True)
    permission = models.ForeignKey(CompanyUsersPermission, on_delete=models.CASCADE)
    role = models.ForeignKey("owners.CompanyUsersRole", on_delete=models.CASCADE)
    active = models.BooleanField(default=True)


class CompanyUsersRolePermissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = CompanyUsersRolePermission
        fields = [
            'id', 'permission', 'role', 'active'
        ]

class CompanyUsersRolePermissionWithSlugSerializer(serializers.ModelSerializer):
    permission_slug = serializers.SlugRelatedField(
        read_only=True,
        source='permission',
        slug_field='slug'
     )

    class Meta:
        model = CompanyUsersRolePermission
        fields = [
            'id', 'permission', 'permission_slug', 'role', 'active'
        ]



class CompanyUsersRole(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    permissions = models.ManyToManyField(CompanyUsersPermission, through=CompanyUsersRolePermission)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)

    # функция проставления всех прав для созданной роли
    def set_default_permissions(self):
        permissions = CompanyUsersPermission.objects.all()
        for permission in permissions:
            CompanyUsersRolePermission.objects.create(
                permission=permission,
                role=self
            )

    def __str__(self):
        return self.name


@receiver(models.signals.post_save, sender=CompanyUsersRole)
def execute_after_save2(sender, instance, created, *args, **kwargs):
    if created:
        instance.set_default_permissions()


class CompanyUsersRoleSerializer(serializers.ModelSerializer):
    permissions = CompanyUsersRolePermissionSerializer(source='companyusersrolepermission_set', many=True)

    class Meta:
        model = CompanyUsersRole
        fields = [
            'id', 'name', 'permissions', 'company_id'
        ]


class CompanyUser(BaseAccount):
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=63)
    last_name = models.CharField(max_length=63)
    middle_name = models.CharField(max_length=63, null=True, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    password = models.CharField(max_length=255, validators=[validate_password])
    available_parking = models.ManyToManyField(Parking)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    created_by_user = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    role = models.ForeignKey(CompanyUsersRole, on_delete=models.SET_NULL, null=True, blank=True)
    avatar = models.CharField(max_length=128, null=True, blank=True)

    @property
    def session_class(self):
        return CompanyUserSession

    @property
    def type(self):
        return 'companyuser'

    def set_password(self, string):
        self.password = make_password(string)

    def password_is_sha256(self, string):
        return len(string) == 78

    def send_login_email(self):
        email_message = f'Доступ к личному кабинету (https://sandbox.parkpass.ru/owner-cabinet/) \n' \
                        f'Логин: {self.email}\n' \
                        f'Пароль: {self.password}\n'
        send_mail('ParkPass Кабинет. Регистрация пользователя', email_message, EMAIL_HOST_USER,
                  [self.email],
                  )

    def create_user(self, email, first_name, last_name, phone, password, available_parking, role_id, company, avatar):
        role = CompanyUsersRole.objects.get(id=role_id)
        user = CompanyUser.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            password=password,
            company=company,
            role=role
        )
        if avatar:
            fs = FileSystemStorage()
            extension = os.path.splitext(avatar.name)[1]
            filename = fs.save(f'valet_users_avatars/{str(uuid.uuid4())}{extension}', avatar)
            uploaded_file_url = fs.url(filename)
            user.avatar = uploaded_file_url
            user.save()

        # проставляем парковки
        for parking_id in available_parking:
            user.available_parking.add(Parking.objects.get(id=int(parking_id)))

        serializer = CompanyUserSerializer([user], many=True)

        return serializer.data[0]

    def update_user(self, id, email, first_name, last_name, phone, password, available_parking, company, role_id, avatar):
        role = CompanyUsersRole.objects.get(id=role_id)
        user = CompanyUser.objects.get(id=id)

        if (user.company_id != company.id):
            e = ValidationException(
                ValidationException.VALIDATION_ERROR,
                "its not allow to edit user from another company"
            )
            return e.to_dict()

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.phone = phone

        if avatar:
            fs = FileSystemStorage()
            extension = os.path.splitext(avatar.name)[1]
            filename = fs.save(f'valet_users_avatars/{str(uuid.uuid4())}{extension}', avatar)
            uploaded_file_url = fs.url(filename)
            user.avatar = uploaded_file_url
            user.save()

        for parking_id in available_parking:
            user.available_parking.add(Parking.objects.get(id=int(parking_id)))

        # удаляем связи
        for parking in user.available_parking.all():
            if str(parking.id) not in available_parking:
                user.available_parking.remove(parking.id)


        user.role = role

        if password:
            user.password = password

        user.save()

        serializer = CompanyUserSerializer([user], many=True)

        return serializer.data[0]

    def check_password(self, raw_password):
        def setter(r_password):
            self.set_password(r_password)
        return check_password(raw_password, self.password, setter)



    def __str__(self):
        return f'{self.first_name} {self.last_name}'



@receiver(models.signals.post_save, sender=CompanyUser)
def execute_after_save_user(sender, instance, created, *args, **kwargs):
    if instance.avatar:
        img = Image.open(MEDIA_ROOT + instance.avatar.replace('/api/media', '')) # Open image using self

        if img.height > 600 or img.width > 600:
            new_img = (600, 600)
            img.thumbnail(new_img)
            img.save(MEDIA_ROOT + instance.avatar.replace('/api/media', ''))  # saving image at the same path


class CompanyUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyUser
        fields = [
            'id', 'first_name', 'last_name', 'middle_name', 'email', 'phone', 'role_id', 'available_parking', 'company',
            'created_by_user', 'avatar'
        ]


@receiver(models.signals.post_save, sender=CompanyUser)
def execute_after_save(sender, instance, created, *args, **kwargs):
    password = instance.password

    if created:
        instance.send_login_email()

    if not instance.password_is_sha256(password) or created:
        instance.set_password(password)
        instance.save()


class CompanyUserSession(BaseAccountSession):
    owner = models.OneToOneField(CompanyUser, on_delete=models.CASCADE)

    @classmethod
    def get_account_by_token(cls, token):
        try:
            session = cls.objects.get(token=token)
            if session.is_expired():
                session.delete()
                return None
            return session.owner

        except ObjectDoesNotExist:
            return None
