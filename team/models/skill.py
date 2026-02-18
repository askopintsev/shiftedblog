from django.db import models


class SkillGroup(models.Model):
    name = models.CharField(max_length=250)

    class Meta:
        app_label = "team"
        db_table = "team_skillgroup"

    def __str__(self):
        return self.name


class Skill(models.Model):
    name = models.CharField(max_length=250)
    rating = models.IntegerField(default=0)
    person = models.ForeignKey(
        "Person", on_delete=models.CASCADE, null=True, blank=True
    )
    group = models.ForeignKey(
        "SkillGroup", on_delete=models.CASCADE, null=True, blank=True
    )

    class Meta:
        app_label = "team"
        db_table = "team_skill"

    def __str__(self):
        return self.name
