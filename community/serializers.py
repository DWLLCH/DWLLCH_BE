from rest_framework import serializers

from .models import (
    Post,
    Comment,
    PostAnonymousAlias,
    Report,
    Scrap,
    PostImage,
    Poll,
    PollOption,
    PollVote,
)


class PollOptionCreateSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=100)


class PollCreateSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=100)
    allowMultiple = serializers.BooleanField(source="allow_multiple", required=False, default=False)
    options = PollOptionCreateSerializer(many=True)

    def validate_options(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("선택지는 2개 이상이어야 합니다.")
        if len(value) > 10:
            raise serializers.ValidationError("선택지는 최대 10개까지 가능합니다.")
        return value


class PostListSerializer(serializers.ModelSerializer):
    boardType = serializers.CharField(source="board_type")
    authorId = serializers.IntegerField(
        source="author_id",
        read_only=True,
    )
    authorName = serializers.SerializerMethodField()
    isAnonymous = serializers.BooleanField(source="is_anonymous")
    isPinned = serializers.BooleanField(source="is_pinned", read_only=True)
    viewCount = serializers.IntegerField(source="view_count")
    commentCount = serializers.SerializerMethodField()
    likeCount = serializers.SerializerMethodField()
    isLiked = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = Post
        fields = [
            "id",
            "boardType",
            "title",
            "authorId",
            "authorName",
            "isAnonymous",
            "isPinned",
            "viewCount",
            "commentCount",
            "likeCount",
            "isLiked",
            "excerpt",
            "thumbnail",
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

    def get_thumbnail(self, obj):
        request = self.context.get("request")
        first_image = obj.images.order_by("order").first()
        if not first_image:
            return None
        url = first_image.image.url
        if request:
            return request.build_absolute_uri(url)
        return url


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ["id", "image", "order"]


class PostDetailSerializer(serializers.ModelSerializer):
    boardType = serializers.CharField(source="board_type")
    authorId = serializers.IntegerField(
        source="author_id",
        read_only=True,
    )
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
    poll = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = Post
        fields = [
            "id",
            "boardType",
            "title",
            "content",
            "authorId",
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
            "poll",
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

    def get_poll(self, obj):
        poll = getattr(obj, "poll", None)
        if not poll:
            return None
        return PollSerializer(poll, context=self.context).data

class PostCreateUpdateSerializer(serializers.ModelSerializer):
    boardType = serializers.ChoiceField(
        source="board_type",
        choices=Post.BoardType.choices,
        required=False,
    )

    isAnonymous = serializers.BooleanField(
        source="is_anonymous",
        required=False,
    )

    allowNotification = serializers.BooleanField(
        source="allow_notification",
        required=False,
    )

    poll = PollCreateSerializer(
        required=False,
        write_only=True,
    )

    keepImageIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Post
        fields = [
            "id",
            "boardType",
            "title",
            "content",
            "isAnonymous",
            "allowNotification",
            "poll",
            "keepImageIds",
        ]
        read_only_fields = ["id"]

    def validate_keepImageIds(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "중복된 이미지 id가 포함되어 있습니다."
            )

        return value

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
    anonymousSequence = serializers.SerializerMethodField()
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
            "anonymousSequence",
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

    def get_anonymousSequence(self, obj):
        """게시글 안에서 이 작성자에게 발급된 익명 번호. 실명 댓글이면 None."""
        if not obj.is_anonymous:
            return None

        # 목록 조회는 게시글 단위로 미리 모아둔 값을 쓴다(댓글마다 조회하지 않도록).
        sequences = self.context.get("anonymous_sequences")

        if sequences is not None:
            return sequences.get(obj.author_id)

        alias = PostAnonymousAlias.objects.filter(
            post_id=obj.post_id,
            author_id=obj.author_id,
        ).first()

        return alias.sequence if alias else None

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


class MyCommentSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.is_deleted:
            data["content"] = "삭제된 댓글입니다."

        return data
    
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
        source="created_at",
        read_only=True,
    )

    class Meta:
        model = Comment
        fields = [
            "id",
            "content",
            "postId",
            "postTitle",
            "boardType",
            "createdAt",
        ]

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


class ReportSerializer(serializers.ModelSerializer):
    targetType = serializers.CharField(source="target_type", read_only=True)
    postId = serializers.IntegerField(source="post_id", read_only=True)
    commentId = serializers.IntegerField(source="comment_id", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Report
        fields = [
            "id",
            "targetType",
            "postId",
            "commentId",
            "reason",
            "createdAt",
        ]


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


class PollOptionSerializer(serializers.ModelSerializer):
    voteCount = serializers.SerializerMethodField()

    class Meta:
        model = PollOption
        fields = ["id", "text", "voteCount"]

    def get_voteCount(self, obj):
        if hasattr(obj, "annotated_vote_count"):
            return obj.annotated_vote_count
        return obj.votes.count()


class PollSerializer(serializers.ModelSerializer):
    allowMultiple = serializers.BooleanField(source="allow_multiple")
    options = PollOptionSerializer(many=True, read_only=True)
    totalVoters = serializers.SerializerMethodField()
    myVotedOptionIds = serializers.SerializerMethodField()

    class Meta:
        model = Poll
        fields = ["id", "question", "allowMultiple", "options", "totalVoters", "myVotedOptionIds"]

    def get_totalVoters(self, obj):
        return PollVote.objects.filter(option__poll=obj).values("user_id").distinct().count()

    def get_myVotedOptionIds(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return []
        return list(
            PollVote.objects.filter(option__poll=obj, user=request.user).values_list("option_id", flat=True)
        )