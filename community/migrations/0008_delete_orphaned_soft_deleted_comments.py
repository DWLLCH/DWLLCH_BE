# -*- coding: utf-8 -*-
"""답글이 모두 사라진 소프트삭제 댓글을 정리한다.

답글 삭제 시 부모를 정리하지 않던 동안 쌓인 데이터가 대상이다.
화면에는 "삭제된 댓글입니다" 만 남아 아무도 지울 수 없는 상태로 보인다.

부모를 지우면 그 부모의 부모가 다시 같은 상태가 될 수 있어,
더 지울 것이 없을 때까지 반복한다.

reverse 는 지운 댓글을 되살리지 못한다.
"""

from django.db import migrations


def delete_orphaned_soft_deleted_comments(apps, schema_editor):
    Comment = apps.get_model("community", "Comment")

    while True:
        parent_ids = Comment.objects.filter(parent__isnull=False).values("parent_id")

        orphans = Comment.objects.filter(is_deleted=True).exclude(id__in=parent_ids)

        deleted, _ = orphans.delete()
        if not deleted:
            break


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0007_poll_polloption_pollvote"),
    ]

    operations = [
        migrations.RunPython(
            delete_orphaned_soft_deleted_comments,
            migrations.RunPython.noop,
        ),
    ]
