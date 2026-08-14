from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from common.responses import success_response
from common.pagination import CommonPageNumberPagination

from .models import Post, Comment, Report, Scrap
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateUpdateSerializer,
    CommentSerializer,
    CommentCreateUpdateSerializer,
    ReportCreateSerializer,
    ScrapSerializer,
)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def post_list(request, board_type):
    if request.method == "GET":
        posts = Post.objects.select_related("author").filter(board_type=board_type)
        paginator = CommonPageNumberPagination()
        page = paginator.paginate_queryset(posts, request)
        serializer = PostListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    if not request.user.is_authenticated:
        raise PermissionDenied("로그인이 필요합니다.")

    serializer = PostCreateUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    post = serializer.save(author=request.user, board_type=board_type)
    return success_response(
        data=PostDetailSerializer(post, context={"request": request}).data,
        message="게시글이 등록되었습니다.",
        status_code=status.HTTP_201_CREATED,
    )


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "GET":
        Post.objects.filter(id=post.id).update(view_count=F("view_count") + 1)
        post.refresh_from_db()
        serializer = PostDetailSerializer(post, context={"request": request})
        return success_response(
            data=serializer.data,
            message="게시글 상세 정보를 조회했습니다.",
        )

    if not request.user.is_authenticated or post.author != request.user:
        raise PermissionDenied("본인이 작성한 게시글만 수정/삭제할 수 있습니다.")

    if request.method == "PATCH":
        serializer = PostCreateUpdateSerializer(post, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=PostDetailSerializer(post, context={"request": request}).data,
            message="게시글이 수정되었습니다.",
        )

    post.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def comment_list(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "GET":
        comments = post.comments.all()
        serializer = CommentSerializer(comments, many=True)
        return success_response(
            data={"comments": serializer.data},
            message="댓글 목록을 조회했습니다.",
        )

    if not request.user.is_authenticated:
        raise PermissionDenied("로그인이 필요합니다.")

    serializer = CommentCreateUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    comment = serializer.save(author=request.user, post=post)
    return success_response(
        data=CommentSerializer(comment).data,
        message="댓글이 등록되었습니다.",
        status_code=status.HTTP_201_CREATED,
    )


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def comment_detail(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if comment.author != request.user:
        raise PermissionDenied("본인이 작성한 댓글만 수정/삭제할 수 있습니다.")

    if request.method == "PATCH":
        serializer = CommentCreateUpdateSerializer(comment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=CommentSerializer(comment).data,
            message="댓글이 수정되었습니다.",
        )

    comment.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def post_report(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    serializer = ReportCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
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
    comment = get_object_or_404(Comment, id=comment_id)

    serializer = ReportCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
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
def post_scrap(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "POST":
        scrap, created = Scrap.objects.get_or_create(user=request.user, post=post)
        if not created:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"detail": "이미 스크랩한 게시글입니다."})
        return success_response(
            data=ScrapSerializer(scrap).data,
            message="게시글이 스크랩되었습니다.",
            status_code=status.HTTP_201_CREATED,
        )

    scrap = get_object_or_404(Scrap, user=request.user, post=post)
    scrap.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def scrap_list(request):
    scraps = Scrap.objects.filter(user=request.user)
    paginator = CommonPageNumberPagination()
    page = paginator.paginate_queryset(scraps, request)
    serializer = ScrapSerializer(page, many=True)
    return paginator.get_paginated_response(serializer.data)