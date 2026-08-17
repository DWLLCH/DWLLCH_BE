from django.conf import settings
from django.db import models


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