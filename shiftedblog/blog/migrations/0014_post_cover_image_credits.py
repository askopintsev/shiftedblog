# Generated by Django 3.1.7 on 2022-06-23 14:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0013_auto_20220623_1125'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='cover_image_credits',
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
    ]