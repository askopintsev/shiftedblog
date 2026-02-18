# Add gallery_key to support multiple galleries and [gallery:N] placement in body

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("editor", "0004_add_post_gallery_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="postgalleryimage",
            name="gallery_key",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Gallery number. Use [gallery:1] in the body for this gallery, [gallery:2] for the next, etc.",
            ),
        ),
        migrations.AlterModelOptions(
            name="postgalleryimage",
            options={"ordering": ["gallery_key", "order", "id"]},
        ),
    ]
