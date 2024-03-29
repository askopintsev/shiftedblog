# Generated by Django 3.1.7 on 2021-07-27 16:29

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0010_skill_rating'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='cover_description',
            field=models.CharField(default=django.utils.timezone.now, max_length=250),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='post',
            name='short_description',
            field=models.CharField(default=django.utils.timezone.now, max_length=300),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='post',
            name='cover_image',
            field=models.ImageField(upload_to='img/post/2021/07/27'),
        ),
    ]
