from django.db.models import (
    F,
    Q,
    Count,
    Exists,
    OuterRef,
    Value,
    BooleanField,
)
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from common.responses import success_response
from common.pagination import CommonPageNumberPagination

from .models import (
    Post,
    Comment,
    Report,
    Scrap,
    PostLike,
    CommentLike,
)
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateUpdateSerializer,
    PostPinSerializer,
    CommentSerializer,
    CommentCreateUpdateSerializer,
    ReportCreateSerializer,
    ScrapSerializer,
)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def post_list(request, board_type):
    if board_type not in Post.BoardType.values:
        raise ValidationError(
            {
                "boardType": (
                    f"boardType은 {', '.join(Post.BoardType.values)} "
                    "중 하나여야 합니다."
                )
            }
        )

    if request.method == "GET":
        posts = (
            Post.objects
            .select_related("author")
            .filter(
                Q(is_pinned=True)
                | Q(board_type=board_type)
            )
            .annotate(
                annotated_like_count=Count(
                    "likes",
                    distinct=True,
                ),
            )
            .order_by(
                "-is_pinned",
                "-created_at",
                "-id",
            )
        )

        if request.user.is_authenticated:
            posts = posts.annotate(
                annotated_is_liked=Exists(
                    PostLike.objects.filter(
                        post_id=OuterRef("pk"),
                        user=request.user,
                    )
                )
            )
        else:
            posts = posts.annotate(
                annotated_is_liked=Value(
                    False,
                    output_field=BooleanField(),
                )
            )

        paginator = CommonPageNumberPagination()
        page = paginator.paginate_queryset(
            posts,
            request,
        )

        serializer = PostListSerializer(
            page,
            many=True,
            context={"request": request},
        )

        return paginator.get_paginated_response(
            serializer.data
        )

    if not request.user.is_authenticated:
        raise PermissionDenied(
            "로그인이 필요합니다."
        )

    serializer = PostCreateUpdateSerializer(
        data=request.data
    )
    serializer.is_valid(
        raise_exception=True
    )

    post = serializer.save(
        author=request.user,
        board_type=board_type,
    )

    return success_response(
        data=PostDetailSerializer(
            post,
            context={"request": request},
        ).data,
        message="게시글이 등록되었습니다.",
        status_code=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def latest_post_list(request):
    posts = (
        Post.objects
        .select_related("author")
        .annotate(
            annotated_like_count=Count(
                "likes",
                distinct=True,
            ),
        )
        .order_by(
            "-is_pinned",
            "-created_at",
            "-id",
        )
    )

    if request.user.is_authenticated:
        posts = posts.annotate(
            annotated_is_liked=Exists(
                PostLike.objects.filter(
                    post_id=OuterRef("pk"),
                    user=request.user,
                )
            )
        )
    else:
        posts = posts.annotate(
            annotated_is_liked=Value(
                False,
                output_field=BooleanField(),
            )
        )

    paginator = CommonPageNumberPagination()
    page = paginator.paginate_queryset(
        posts,
        request,
    )

    serializer = PostListSerializer(
        page,
        many=True,
        context={"request": request},
    )

    return paginator.get_paginated_response(
        serializer.data
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def post_detail(request, post_id):
    post = get_object_or_404(
        Post,
        id=post_id,
    )

    if request.method == "GET":
        Post.objects.filter(
            id=post.id
        ).update(
            view_count=F("view_count") + 1
        )

        post.refresh_from_db()

        serializer = PostDetailSerializer(
            post,
            context={"request": request},
        )

        return success_response(
            data=serializer.data,
            message="게시글 상세 정보를 조회했습니다.",
        )

    if (
        not request.user.is_authenticated
        or post.author != request.user
    ):
        raise PermissionDenied(
            "본인이 작성한 게시글만 수정/삭제할 수 있습니다."
        )

    if request.method == "PATCH":
        serializer = PostCreateUpdateSerializer(
            post,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(
            raise_exception=True
        )
        serializer.save()

        return success_response(
            data=PostDetailSerializer(
                post,
                context={"request": request},
            ).data,
            message="게시글이 수정되었습니다.",
        )

    post.delete()

    return Response(
        status=status.HTTP_204_NO_CONTENT,
    )

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def post_pin(request, post_id):
    if not request.user.is_staff:
        raise PermissionDenied(
            "관리자만 게시글을 상단 고정할 수 있습니다."
        )

    post = get_object_or_404(
        Post,
        id=post_id,
    )

    serializer = PostPinSerializer(
        post,
        data=request.data,
    )
    serializer.is_valid(
        raise_exception=True
    )
    serializer.save()

    return success_response(
        data=PostDetailSerializer(
            post,
            context={"request": request},
        ).data,
        message=(
            "게시글이 상단에 고정되었습니다."
            if post.is_pinned
            else "게시글 상단 고정이 해제되었습니다."
        ),
    )

@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def comment_list(request, post_id):
    post = get_object_or_404(
        Post,
        id=post_id,
    )

    if request.method == "GET":
        comments = (
            post.comments
            .select_related("author", "parent")
            .annotate(
                annotated_like_count=Count(
                    "likes",
                    distinct=True,
                ),
            )
        )

        if request.user.is_authenticated:
            comments = comments.annotate(
                annotated_is_liked=Exists(
                    CommentLike.objects.filter(
                        comment_id=OuterRef("pk"),
                        user=request.user,
                    )
                )
            )
        else:
            comments = comments.annotate(
                annotated_is_liked=Value(
                    False,
                    output_field=BooleanField(),
                )
            )

        serializer = CommentSerializer(
            comments,
            many=True,
            context={"request": request},
        )

        return success_response(
            data={
                "comments": serializer.data
            },
            message="댓글 목록을 조회했습니다.",
        )

    if not request.user.is_authenticated:
        raise PermissionDenied(
            "로그인이 필요합니다."
        )

    serializer = CommentCreateUpdateSerializer(
        data=request.data
    )
    serializer.is_valid(
        raise_exception=True
    )

    parent_id = serializer.validated_data.pop(
        "parentId",
        None,
    )

    parent = None

    if parent_id is not None:
        parent = get_object_or_404(
            Comment,
            id=parent_id,
        )

        # 다른 게시글의 댓글에 답글 작성 방지
        if parent.post_id != post.id:
            raise ValidationError(
                {
                    "parentId": (
                        "같은 게시글의 댓글에만 "
                        "답글을 작성할 수 있습니다."
                    )
                }
            )

        # 대댓글의 대댓글 방지
        if parent.parent_id is not None:
            raise ValidationError(
                {
                    "parentId": (
                        "대댓글에는 답글을 작성할 수 없습니다."
                    )
                }
            )

        # 삭제된 부모 댓글에는 새 답글 작성 방지
        if parent.is_deleted:
            raise ValidationError(
                {
                    "parentId": (
                        "삭제된 댓글에는 답글을 작성할 수 없습니다."
                    )
                }
            )

    comment = serializer.save(
        author=request.user,
        post=post,
        parent=parent,
    )

    return success_response(
        data=CommentSerializer(
            comment,
            context={"request": request},
        ).data,
        message="댓글이 등록되었습니다.",
        status_code=status.HTTP_201_CREATED,
    )


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def comment_detail(request, comment_id):
    comment = get_object_or_404(
        Comment,
        id=comment_id,
    )

    if comment.author != request.user:
        raise PermissionDenied(
            "본인이 작성한 댓글만 수정/삭제할 수 있습니다."
        )

    if request.method == "PATCH":
        if comment.is_deleted:
            raise ValidationError(
                {
                    "detail": (
                        "삭제된 댓글은 수정할 수 없습니다."
                    )
                }
            )

        serializer = CommentCreateUpdateSerializer(
            comment,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(
            raise_exception=True
        )

        # 댓글 수정 과정에서 parent 변경은 허용하지 않음
        serializer.validated_data.pop(
            "parentId",
            None,
        )

        serializer.save()

        return success_response(
            data=CommentSerializer(
                comment,
                context={"request": request},
            ).data,
            message="댓글이 수정되었습니다.",
        )

    # 답글이 존재하면 부모 댓글은 DB에서 지우지 않고 soft delete
    if comment.replies.exists():
        comment.is_deleted = True
        comment.save(
            update_fields=[
                "is_deleted",
                "updated_at",
            ]
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )

    # 답글이 없으면 기존처럼 완전히 삭제
    comment.delete()

    return Response(
        status=status.HTTP_204_NO_CONTENT,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def post_report(request, post_id):
    post = get_object_or_404(
        Post,
        id=post_id,
    )

    serializer = ReportCreateSerializer(
        data=request.data
    )
    serializer.is_valid(
        raise_exception=True
    )

    serializer.save(
        reporter=request.user,
        target_type=Report.TargetType.POST,
        post=post,
    )

    return success_response(
        data=serializer.data,
        message="게시글이 신고되었습니다.",
        status_code=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def comment_report(request, comment_id):
    comment = get_object_or_404(
        Comment,
        id=comment_id,
    )

    serializer = ReportCreateSerializer(
        data=request.data
    )
    serializer.is_valid(
        raise_exception=True
    )

    serializer.save(
        reporter=request.user,
        target_type=Report.TargetType.COMMENT,
        comment=comment,
    )

    return success_response(
        data=serializer.data,
        message="댓글이 신고되었습니다.",
        status_code=status.HTTP_201_CREATED,
    )


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def post_like(request, post_id):
    post = get_object_or_404(
        Post,
        id=post_id,
    )

    if request.method == "POST":
        like, created = PostLike.objects.get_or_create(
            user=request.user,
            post=post,
        )

        if not created:
            raise ValidationError(
                {
                    "detail": (
                        "이미 좋아요한 게시글입니다."
                    )
                }
            )

        return success_response(
            data={
                "postId": post.id,
                "likeCount": post.likes.count(),
                "isLiked": True,
            },
            message="게시글에 좋아요를 등록했습니다.",
            status_code=status.HTTP_201_CREATED,
        )

    like = get_object_or_404(
        PostLike,
        user=request.user,
        post=post,
    )

    like.delete()

    return Response(
        status=status.HTTP_204_NO_CONTENT,
    )


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def comment_like(request, comment_id):
    comment = get_object_or_404(
        Comment,
        id=comment_id,
    )

    if request.method == "POST":
        like, created = CommentLike.objects.get_or_create(
            user=request.user,
            comment=comment,
        )

        if not created:
            raise ValidationError(
                {
                    "detail": (
                        "이미 좋아요한 댓글입니다."
                    )
                }
            )

        return success_response(
            data={
                "commentId": comment.id,
                "likeCount": comment.likes.count(),
                "isLiked": True,
            },
            message="댓글에 좋아요를 등록했습니다.",
            status_code=status.HTTP_201_CREATED,
        )

    like = get_object_or_404(
        CommentLike,
        user=request.user,
        comment=comment,
    )

    like.delete()

    return Response(
        status=status.HTTP_204_NO_CONTENT,
    )


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def post_scrap(request, post_id):
    post = get_object_or_404(
        Post,
        id=post_id,
    )

    if request.method == "POST":
        scrap, created = Scrap.objects.get_or_create(
            user=request.user,
            post=post,
        )

        if not created:
            raise ValidationError(
                {
                    "detail": (
                        "이미 스크랩한 게시글입니다."
                    )
                }
            )

        return success_response(
            data=ScrapSerializer(
                scrap
            ).data,
            message="게시글이 스크랩되었습니다.",
            status_code=status.HTTP_201_CREATED,
        )

    scrap = get_object_or_404(
        Scrap,
        user=request.user,
        post=post,
    )

    scrap.delete()

    return Response(
        status=status.HTTP_204_NO_CONTENT,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def scrap_list(request):
    scraps = Scrap.objects.filter(
        user=request.user
    )

    paginator = CommonPageNumberPagination()
    page = paginator.paginate_queryset(
        scraps,
        request,
    )

    serializer = ScrapSerializer(
        page,
        many=True,
    )

    return paginator.get_paginated_response(
        serializer.data
    )