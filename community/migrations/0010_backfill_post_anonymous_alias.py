# -*- coding: utf-8 -*-
"""이미 달려 있는 익명 댓글에 번호를 소급 발급한다.

번호가 없으면 기존 익명 댓글이 전부 번호 없이 내려간다.
게시글마다 첫 익명 댓글을 단 순서대로 1 부터 매겨, 지금까지 화면에 보이던
순서와 최대한 같게 만든다.

reverse 는 발급한 번호를 지운다.
"""

from django.db import migrations


def backfill_aliases(apps, schema_editor):
    Comment = apps.get_model("community", "Comment")
    PostAnonymousAlias = apps.get_model("community", "PostAnonymousAlias")

    existing = set(
        PostAnonymousAlias.objects.values_list("post_id", "author_id")
    )
    next_sequence = {}

    for post_id, sequence in PostAnonymousAlias.objects.values_list(
        "post_id", "sequence"
    ):
        next_sequence[post_id] = max(next_sequence.get(post_id, 0), sequence)

    new_aliases = []

    comments = (
        Comment.objects
        .filter(is_anonymous=True, author__isnull=False)
        .order_by("created_at", "id")
        .values_list("post_id", "author_id")
    )

    for post_id, author_id in comments:
        if (post_id, author_id) in existing:
            continue

        existing.add((post_id, author_id))
        next_sequence[post_id] = next_sequence.get(post_id, 0) + 1

        new_aliases.append(
            PostAnonymousAlias(
                post_id=post_id,
                author_id=author_id,
                sequence=next_sequence[post_id],
            )
        )

    PostAnonymousAlias.objects.bulk_create(new_aliases)


def clear_aliases(apps, schema_editor):
    PostAnonymousAlias = apps.get_model("community", "PostAnonymousAlias")
    PostAnonymousAlias.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0009_postanonymousalias"),
    ]

    operations = [
        migrations.RunPython(backfill_aliases, clear_aliases),
    ]
