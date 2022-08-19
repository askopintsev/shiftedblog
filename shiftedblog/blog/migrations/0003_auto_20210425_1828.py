# Generated by Django 3.1.7 on 2021-04-25 15:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0002_account_person_skill'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='icon',
            field=models.ImageField(upload_to='img/template/'),
        ),
        migrations.AlterField(
            model_name='person',
            name='account',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='blog.account'),
        ),
        migrations.AlterField(
            model_name='person',
            name='avatar',
            field=models.ImageField(upload_to='img/template/'),
        ),
        migrations.AlterField(
            model_name='person',
            name='greeting',
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name='person',
            name='skill',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='blog.skill'),
        ),
        migrations.AlterField(
            model_name='post',
            name='cover_image',
            field=models.ImageField(upload_to='img/post/2021/04/25'),
        ),
    ]
