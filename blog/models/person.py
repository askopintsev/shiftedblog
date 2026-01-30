from django.db import models


class Person(models.Model):
    avatar = models.ImageField(upload_to="img/template/")
    name = models.CharField(max_length=250)
    greeting = models.TextField()
    biography = models.TextField()

    class Meta:
        app_label = "blog"

    def __str__(self):
        return self.name
