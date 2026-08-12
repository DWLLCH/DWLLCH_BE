from rest_framework import serializers

from .models import Post


class PostListSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "board_type",
            "title",
            "author_name",
            "is_anonymous",
            "view_count",
            "comment_count",
            "created_at",
        ]

    def get_author_name(self, obj):
        return "익명" if obj.is_anonymous else obj.author.username

    def get_comment_count(self, obj):
        return obj.comments.count()


class PostDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "board_type",
            "title",
            "content",
            "author_name",
            "is_anonymous",
            "allow_notification",
            "view_count",
            "comment_count",
            "is_mine",
            "created_at",
            "updated_at",
        ]

    def get_author_name(self, obj):
        return "익명" if obj.is_anonymous else obj.author.username

    def get_comment_count(self, obj):
        return obj.comments.count()

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and request.user == obj.author)


class PostCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = [
            "id",
            "board_type",
            "title",
            "content",
            "is_anonymous",
            "allow_notification",
        ]
        read_only_fields = ["id"]

class CommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "post",
            "author_name",
            "content",
            "is_anonymous",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "post", "created_at", "updated_at"]

    def get_author_name(self, obj):
        if obj.is_anonymous:
            return "익명"
        return obj.author.username


class CommentCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["content", "is_anonymous"]

class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["reason"]

class ScrapSerializer(serializers.ModelSerializer):
    post_id = serializers.IntegerField(source="post.id", read_only=True)
    post_title = serializers.CharField(source="post.title", read_only=True)
    board_type = serializers.CharField(source="post.board_type", read_only=True)

    class Meta:
        model = Scrap
        fields = ["id", "post_id", "post_title", "board_type", "created_at"]