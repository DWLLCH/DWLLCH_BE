from rest_framework import serializers

from .models import Post, Comment, Report, Scrap, PostImage


class PostListSerializer(serializers.ModelSerializer):
    boardType = serializers.CharField(source="board_type")
    authorName = serializers.SerializerMethodField()
    isAnonymous = serializers.BooleanField(source="is_anonymous")
    isPinned = serializers.BooleanField(source="is_pinned", read_only=True)
    viewCount = serializers.IntegerField(source="view_count")
    commentCount = serializers.SerializerMethodField()
    likeCount = serializers.SerializerMethodField()
    isLiked = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = Post
        fields = [
            "id",
            "boardType",
            "title",
            "authorName",
            "isAnonymous",
            "isPinned",
            "viewCount",
            "commentCount",
            "likeCount",
            "isLiked",
            "excerpt",
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

    def get_excerpt(self, obj):
        return obj.content[:100]


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ["id", "image", "order"]


class PostDetailSerializer(serializers.ModelSerializer):
    boardType = serializers.CharField(source="board_type")
    authorName = serializers.SerializerMethodField()
    isAnonymous = serializers.BooleanField(source="is_anonymous")
    allowNotification = serializers.BooleanField(source="allow_notification")
    isPinned = serializers.BooleanField(source="is_pinned", read_only=True)
    viewCount = serializers.IntegerField(source="view_count")
    commentCount = serializers.SerializerMethodField()
    likeCount = serializers.SerializerMethodField()
    isLiked = serializers.SerializerMethodField()
    isMine = serializers.SerializerMethodField()
    images = PostImageSerializer(many=True, read_only=True)
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
            "isPinned",
            "viewCount",
            "commentCount",
            "likeCount",
            "isLiked",
            "isMine",
            "images",
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

        return obj.likes.filter(
            user=request.user
        ).exists()

    def get_isMine(self, obj):
        request = self.context.get("request")

        return bool(
            request
            and request.user.is_authenticated
            and request.user == obj.author
        )


class PostCreateUpdateSerializer(serializers.ModelSerializer):
    isAnonymous = serializers.BooleanField(
        source="is_anonymous",
        required=False,
    )
    allowNotification = serializers.BooleanField(
        source="allow_notification",
        required=False,
    )

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "content",
            "isAnonymous",
            "allowNotification",
        ]
        read_only_fields = ["id"]


class PostPinSerializer(serializers.ModelSerializer):
    isPinned = serializers.BooleanField(
        source="is_pinned"
    )

    class Meta:
        model = Post
        fields = [
            "isPinned",
        ]


class CommentSerializer(serializers.ModelSerializer):
    authorId = serializers.IntegerField(
        source="author_id",
        read_only=True,
    )
    authorName = serializers.SerializerMethodField()
    isAnonymous = serializers.BooleanField(source="is_anonymous")
    likeCount = serializers.SerializerMethodField()
    isLiked = serializers.SerializerMethodField()
    isDeleted = serializers.BooleanField(
        source="is_deleted",
        read_only=True,
    )
    parentId = serializers.IntegerField(
        source="parent_id",
        read_only=True,
    )
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = Comment
        fields = [
            "id",
            "post",
            "parentId",
            "authorId",
            "authorName",
            "content",
            "isAnonymous",
            "isDeleted",
            "likeCount",
            "isLiked",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = [
            "id",
            "post",
            "parentId",
            "isDeleted",
            "createdAt",
            "updatedAt",
        ]

    def get_authorName(self, obj):
        if obj.author is None or not obj.author.is_active:
            return "탈퇴한 회원"

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

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.is_deleted:
            data["content"] = "삭제된 댓글입니다."

        return data


class CommentCreateUpdateSerializer(serializers.ModelSerializer):
    isAnonymous = serializers.BooleanField(
        source="is_anonymous",
        required=False,
    )
    parentId = serializers.IntegerField(
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Comment
        fields = [
            "content",
            "isAnonymous",
            "parentId",
        ]


class ReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["reason"]


class ScrapSerializer(serializers.ModelSerializer):
    postId = serializers.IntegerField(
        source="post.id",
        read_only=True,
    )
    postTitle = serializers.CharField(
        source="post.title",
        read_only=True,
    )
    boardType = serializers.CharField(
        source="post.board_type",
        read_only=True,
    )
    createdAt = serializers.DateTimeField(
        source="created_at"
    )

    class Meta:
        model = Scrap
        fields = [
            "id",
            "postId",
            "postTitle",
            "boardType",
            "createdAt",
        ]