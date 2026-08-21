"""Team public about page tests."""

import io
from typing import cast

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from team.models import Account, AccountGroup, Person, Skill, SkillGroup


def _minimal_jpeg_upload(name: str = "avatar.jpg") -> SimpleUploadedFile:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(40, 80, 120)).save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


class AboutPageTests(TestCase):
    def test_about_groups_accounts_and_lists_skills(self):
        person = Person.objects.create(
            avatar=_minimal_jpeg_upload(),
            name="Ada",
            greeting="Hello",
            biography="Bio",
        )
        group = AccountGroup.objects.create(name="Social")
        other = AccountGroup.objects.create(name="Code")
        Account.objects.create(
            name="Telegram",
            url="https://t.me/example",
            icon=_minimal_jpeg_upload("tg.jpg"),
            group=group,
            person=person,
        )
        Account.objects.create(
            name="GitHub",
            url="https://github.com/example",
            icon=_minimal_jpeg_upload("gh.jpg"),
            group=other,
            person=person,
        )
        Account.objects.create(
            name="Habr",
            url="https://habr.com/example",
            icon=_minimal_jpeg_upload("habr.jpg"),
            group=group,
            person=person,
        )
        skill_group = SkillGroup.objects.create(name="Lang")
        Skill.objects.create(name="Python", rating=5, person=person, group=skill_group)

        response = self.client.get(reverse("team:about"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hello")
        grouped = cast(dict, response.context["grouped_accounts"])
        self.assertEqual(len(grouped["Social"]), 2)
        self.assertEqual(len(grouped["Code"]), 1)
