from django.conf import settings
from django.db import IntegrityError, models, transaction


class Post(models.Model):
    class BoardType(models.TextChoices):
        TIP = "TIP", "꿀팁"
        LATEST = "LATEST", "최신"
        WORRY = "WORRY", "고민"
        FREE = "FREE", "자유"

    board_type = models.CharField(max_length=20, choices=BoardType.choices)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    title = models.CharField(max_length=100)
    content = models.TextField()
    is_anonymous = models.BooleanField(default=False)
    allow_notification = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False)
    
    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )

    content = models.CharField(max_length=500)
    is_anonymous = models.BooleanField(default=False)

    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author} - {self.content[:20]}"


class PostAnonymousAlias(models.Model):
    """게시글 안에서 한 작성자에게 발급한 익명 번호.

    "익명1", "익명2" 처럼 게시글마다 1 부터 매긴다.
    번호를 Comment 에 두면 답글 없는 댓글이 완전삭제될 때 함께 사라져,
    새로고침하면 같은 사람이 다른 번호를 받게 된다.
    그래서 댓글과 수명을 분리해 따로 보관한다.
    """

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="anonymous_aliases",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_anonymous_aliases",
    )
    sequence = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["post", "author"],
                name="unique_post_anonymous_author",
            ),
            models.UniqueConstraint(
                fields=["post", "sequence"],
                name="unique_post_anonymous_sequence",
            ),
        ]

    def __str__(self):
        return f"익명{self.sequence}"

    @classmethod
    def issue(cls, post, author):
        """(게시글, 작성자) 조합의 번호를 돌려준다. 없으면 새로 발급한다.

        동시에 첫 익명 댓글이 달리면 같은 번호를 계산할 수 있다.
        (post, sequence) 유니크 제약으로 한쪽만 성공하므로, 실패하면 다시 시도한다.
        """
        alias = cls.objects.filter(post=post, author=author).first()

        if alias is not None:
            return alias.sequence

        for _ in range(5):
            last = cls.objects.filter(post=post).aggregate(
                models.Max("sequence")
            )["sequence__max"]

            try:
                with transaction.atomic():
                    alias = cls.objects.create(
                        post=post,
                        author=author,
                        sequence=(last or 0) + 1,
                    )
            except IntegrityError:
                alias = cls.objects.filter(post=post, author=author).first()

                if alias is not None:
                    return alias.sequence

                continue

            return alias.sequence

        raise IntegrityError("익명 번호를 발급하지 못했습니다.")


class Report(models.Model):
    class TargetType(models.TextChoices):
        POST = "POST", "게시글"
        COMMENT = "COMMENT", "댓글"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    target_type = models.CharField(max_length=10, choices=TargetType.choices)
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, null=True, blank=True, related_name="reports"
    )
    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, null=True, blank=True, related_name="reports"
    )
    reason = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            # 한 사람이 같은 대상을 여러 번 신고하면 누적 건수를 기준으로
            # 노출을 판단할 수 없다. 대상별로 1회만 접수한다.
            models.UniqueConstraint(
                fields=["reporter", "post"],
                condition=models.Q(post__isnull=False),
                name="unique_post_report_per_reporter",
            ),
            models.UniqueConstraint(
                fields=["reporter", "comment"],
                condition=models.Q(comment__isnull=False),
                name="unique_comment_report_per_reporter",
            ),
        ]

    def __str__(self):
        return f"{self.reporter} reported {self.target_type}"

class Scrap(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="scraps",
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="scraps",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "post"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} scrapped {self.post}"

class PostLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_likes",
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "post"]

    def __str__(self):
        return f"{self.user} liked {self.post}"


class CommentLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comment_likes",
    )
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name="likes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "comment"]

    def __str__(self):
        return f"{self.user} liked comment {self.comment.id}"

class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="community/posts/")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.post.title} - image {self.order}"

class Poll(models.Model):
    post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name="poll")
    question = models.CharField(max_length=100)
    allow_multiple = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question


class PollOption(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text


class PollVote(models.Model):
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="poll_votes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["option", "user"]