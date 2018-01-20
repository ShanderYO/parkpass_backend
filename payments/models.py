from django.db import models

# Create your models here.
from accounts.models import Account


class CreditCard(models.Model):
    id = models.AutoField(primary_key=True)
    #type = models.CharField("Type", blank=True, max_length=30)
    #owner = models.CharField("Owner", blank=True, max_length=100)
    number = models.CharField("Number", blank=True, max_length=30)
    #expiration_date_month = models.IntegerField(blank=True, null=True)
    #expiration_date_year = models.IntegerField(blank=True, null=True)

    is_default = models.BooleanField(default=False)
    created_at = models.DateField(auto_now_add=True)
    account = models.ForeignKey(Account, related_name = "credit_cards")

    def __unicode__(self):
        return u"%s / %s" % (self.number, "")# self.owner)

    class Meta:
        ordering = ["-id"]
        verbose_name = 'CreditCard'
        verbose_name_plural = 'CreditCards'

    @classmethod
    def get_card_by_account(cls, account):
        return CreditCard.objects.filter(account=account)
