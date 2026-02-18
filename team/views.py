from django.shortcuts import render

from team.models import Person


def about(request):
    person = Person.objects.first()

    if not person:
        return render(
            request,
            "editor/about.html",
            {"person": None, "skills": None, "grouped_accounts": None},
        )

    skills = person.skill_set.all()
    accounts = person.account_set.all()
    grouped_accounts = {}
    for account in accounts:
        if account.group.name in grouped_accounts:
            grouped_accounts[account.group.name].append(account)
        else:
            grouped_accounts[account.group.name] = [account]

    return render(
        request,
        "editor/about.html",
        {"person": person, "skills": skills, "grouped_accounts": grouped_accounts},
    )
