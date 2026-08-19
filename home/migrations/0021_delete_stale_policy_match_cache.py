# -*- coding: utf-8 -*-
"""집합 단위로 저장돼 있던 정책 매칭 캐시 행을 정리한다.

정책 매칭 캐시가 CurationMatchCache(cache_type="POLICY_MATCH") 에서
정책 단위인 PolicyMatchCache 로 옮겨가면서 기존 행은 더 이상 읽히지 않는다.
남겨두면 CacheType 에 없는 값이 DB 에만 떠도는 상태가 되므로 지운다.

reverse 는 지운 행을 되살리지 못한다. 캐시라서 다시 채워지면 그만이다.
"""

from django.db import migrations


def delete_stale_policy_match_cache(apps, schema_editor):
    CurationMatchCache = apps.get_model("home", "CurationMatchCache")
    CurationMatchCache.objects.filter(cache_type="POLICY_MATCH").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0020_alter_curationmatchcache_cache_type_policymatchcache"),
    ]

    operations = [
        migrations.RunPython(
            delete_stale_policy_match_cache,
            migrations.RunPython.noop,
        ),
    ]
