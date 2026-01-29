# Generated manually to fix published field to be nullable

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog', '0007_remove_post_series_postseries_post_series'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='published',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
    ]
