from rest_framework import serializers

from .models import Post, Comment, Report, Scrap


class PostListSerializer(serializers.ModelSerializer):
    boardType = serializers.CharField(source="board_type")
    authorName = serializers.SerializerMethodField()
    isAnonymous = serializers.BooleanField(source="is_anonymous")
    viewCount = serializers.IntegerField(source="view_count")
    commentCount = serializers.SerializerMethodField()
    likeCount = serializers.SerializerMethodField()
    isLiked = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = Post
        fields = [
            "id",
            "boardType",
            "title",
            "authorName",
            "isAnonymous",
            "viewCount",
            "commentCount",
            "likeCount",
            "isLiked",
            "createdAt",
        ]

    def get_authorName(self, obj):
        return "익명" if obj.is_anonymous else obj.author.username

    def get_commentCount(self, obj):
        return obj.comments.count()

    def get_likeCount(self, obj):
        if hasattr(obj, "annotated_like_count"):
            return obj.annotated_like_count

        return obj.likes.count()

    def get_isLiked(self, obj):
        if hasattr(obj, "annotated_is_liked"):
            return obj.annotated_is_liked

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return False

        return obj.likes.filter(
            user=request.user
        ).exists()


class PostDetailSerializer(serializers.ModelSerializer):
    boardType = serializers.CharField(source="board_type")
    authorName = serializers.SerializerMethodField()
    isAnonymous = serializers.BooleanField(source="is_anonymous")
    allowNotification = serializers.BooleanField(source="allow_notification")
    viewCount = serializers.IntegerField(source="view_count")
    commentCount = serializers.SerializerMethodField()
    likeCount = serializers.SerializerMethodField()
    isLiked = serializers.SerializerMethodField()
    isMine = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = Post
        fields = [
            "id",
            "boardType",
            "title",
            "content",
            "authorName",
            "isAnonymous",
            "allowNotification",
            "viewCount",
            "commentCount",
            "likeCount",
            "isLiked",
            "isMine",
            "createdAt",
            "updatedAt",
        ]

    def get_authorName(self, obj):
        return "익명" if obj.is_anonymous else obj.author.username

    def get_commentCount(self, obj):
        return obj.comments.count()

    def get_likeCount(self, obj):
        return obj.likes.count()

    def get_isLiked(self, obj):
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return False

        return obj.likes.filter(user=request.user).exists()

    def get_isMine(self, obj):
        request = self.context.get("request")
        return bool(
            request
            and request.user.is_authenticated
            and request.user == obj.author
        )


class PostCreateUpdateSerializer(serializers.ModelSerializer):
    isAnonymous = serializers.BooleanField(source="is_anonymous", required=False)
    allowNotification = serializers.BooleanField(source="allow_notification", required=False)

    class Meta:
        model = Post
        fields = ["id", "title", "content", "isAnonymous", "allowNotification"]
        read_only_fields = ["id"]


class CommentSerializer(serializers.ModelSerializer):
    authorName = serializers.SerializerMethodField()
    isAnonymous = serializers.BooleanField(source="is_anonymous")
    likeCount = serializers.SerializerMethodField()
    isLiked = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = Comment
        fields = [
            "id",
            "post",
            "authorName",
            "content",
            "isAnonymous",
            "likeCount",
            "isLiked",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = [
            "id",
            "post",
            "createdAt",
            "updatedAt",
        ]

    def get_authorName(self, obj):
        return "익명" if obj.is_anonymous else obj.author.username

    def get_likeCount(self, obj):
        if hasattr(obj, "annotated_like_count"):
            return obj.annotated_like_count

        return obj.likes.count()

    def get_isLiked(self, obj):
        if hasattr(obj, "annotated_is_liked"):
            return obj.annotated_is_liked

        request = self.context.get("request")

        if not request or not request.user.is_authenticated:
            return False

        return obj.likes.filter(
            user=request.user
        ).exists()


class CommentCreateUpdateSerializer(serializers.ModelSerializer):
    isAnonymous = serializers.BooleanField(source="is_anonymous", required=False)

    class Meta:
        model = Comment
        fields = ["content", "isAnonymous"]


class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["reason"]


class ScrapSerializer(serializers.ModelSerializer):
    postId = serializers.IntegerField(source="post.id", read_only=True)
    postTitle = serializers.CharField(source="post.title", read_only=True)
    boardType = serializers.CharField(source="post.board_type", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = Scrap
        fields = ["id", "postId", "postTitle", "boardType", "createdAt"]