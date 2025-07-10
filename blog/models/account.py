from django.db import models


class AccountGroup(models.Model):
    name = models.CharField(max_length=250)

    class Meta:
        app_label = 'blog'

    def __str__(self):
        return self.name


class Account(models.Model):
    name = models.CharField(max_length=250)
    url = models.CharField(max_length=250)
    icon = models.FileField(upload_to='img/template/')
    group = models.ForeignKey('AccountGroup', on_delete=models.CASCADE, null=True, blank=True)
    person = models.ForeignKey('Person', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        app_label = 'blog'

    def __str__(self):
        return self.name
