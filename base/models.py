from parkpass import settings
from django.db import models


class Terminal(models.Model):
    terminal_key = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    is_selected = models.BooleanField(default=False)

    def __unicode__(self):
        return "Terminal %s" % self.terminal_key

    def save(self, *args, **kwargs):
        if self.is_selected:
            old_active_terminals = Terminal.objects.filter(is_selected=True).exclude(id=self.id)

            for old_active_terminal in old_active_terminals:
                old_active_terminal.is_selected = False
                old_active_terminal.save()

            settings.TINKOFF_TERMINAL_KEY = self.terminal_key
            settings.TINKOFF_TERMINAL_PASSWORD = self.password

        super(Terminal, self).save(*args, **kwargs)