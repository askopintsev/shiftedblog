# Generated by Django 3.1.7 on 2021-04-28 19:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0006_account_person'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='cover_image',
            field=models.ImageField(upload_to='img/post/2021/04/28'),
        ),
    ]