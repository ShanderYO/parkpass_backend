from __future__ import unicode_literals

import binascii
import hashlib
import hmac
import os

from django.db import models


class Partner(models.Model):
    name = models.CharField(max_length=255, unique=True)
    canonical_name = models.CharField(max_length=255, unique=True)
    secret = models.TextField()

    def __unicode__(self):
        return "%s" % self.name

    def save(self, *args, **kwargs):
        if not self.pk:
            if not kwargs.get("not_generate_secret", False):
                self.generate_secret()
            else:
                del kwargs["not_generate_secret"]
        super(Partner, self).save(*args, **kwargs)

    def generate_secret(self):
        self.secret = binascii.hexlify(os.urandom(32)).decode()

    def sign(self, data):
        return hmac.new(str(self.secret), data, hashlib.sha512)
