# -*- coding: utf-8 -*-
"""기존 브리핑에 카드 색상/아이콘 기본값을 채운다.

0002 는 모든 기존 행에 필드 기본값(blue/document)을 넣는다.
여기서는 카테고리에 맞는 조합으로 덮어써서, FE 카드가 콘텐츠와 어울리는
비주얼을 갖도록 한다. 개별 브리핑에 더 어울리는 값은 이후 어드민에서 조정한다.

특정 id 에 값을 박지 않고 카테고리 규칙으로 처리하므로,
배포 환경에 어떤 브리핑이 들어 있든 동일하게 적용된다.
"""

from django.db import migrations


# category -> (color, icon)
CARD_VISUAL_BY_CATEGORY = {
    "FINANCE": ("green", "money"),
    "HOUSING": ("blue", "home"),
    "EMPLOYMENT": ("red", "graduation"),
}

DEFAULT_CARD_VISUAL = ("blue", "document")


def fill_card_visual(apps, schema_editor):
    Briefing = apps.get_model("briefing", "Briefing")

    for category, (color, icon) in CARD_VISUAL_BY_CATEGORY.items():
        Briefing.objects.filter(category=category).update(color=color, icon=icon)


def reset_card_visual(apps, schema_editor):
    Briefing = apps.get_model("briefing", "Briefing")

    color, icon = DEFAULT_CARD_VISUAL
    Briefing.objects.update(color=color, icon=icon)


class Migration(migrations.Migration):

    dependencies = [
        ("briefing", "0002_briefing_color_briefing_icon"),
    ]

    operations = [
        migrations.RunPython(fill_card_visual, reset_card_visual),
    ]
