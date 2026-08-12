from django.db.models import F
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Post, Comment, Report, Scrap
from .serializers import (
    PostCreateUpdateSerializer,
    PostDetailSerializer,
    PostListSerializer,
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
        serializer = PostListSerializer(posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if not request.user.is_authenticated:
        return Response(
            {"detail": "로그인이 필요합니다."}, status=status.HTTP_401_UNAUTHORIZED
        )

    serializer = PostCreateUpdateSerializer(data=request.data)
    if serializer.is_valid():
        post = serializer.save(author=request.user, board_type=board_type)
        return Response(
            PostDetailSerializer(post, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "GET":
        Post.objects.filter(id=post.id).update(view_count=F("view_count") + 1)
        post.refresh_from_db()
        serializer = PostDetailSerializer(post, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    if not request.user.is_authenticated or post.author != request.user:
        return Response(
            {"detail": "본인이 작성한 게시글만 수정/삭제할 수 있습니다."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "PATCH":
        serializer = PostCreateUpdateSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                PostDetailSerializer(post, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    post.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def comment_list(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "GET":
        comments = post.comments.all()
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    if not request.user.is_authenticated:
        return Response(
            {"detail": "로그인이 필요합니다."}, status=status.HTTP_401_UNAUTHORIZED
        )

    serializer = CommentCreateUpdateSerializer(data=request.data)
    if serializer.is_valid():
        comment = serializer.save(author=request.user, post=post)
        return Response(
            CommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def comment_detail(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if comment.author != request.user:
        return Response(
            {"detail": "본인이 작성한 댓글만 수정/삭제할 수 있습니다."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.method == "PATCH":
        serializer = CommentCreateUpdateSerializer(comment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    comment.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def post_report(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    serializer = ReportCreateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(
            reporter=request.user,
            target_type=Report.TargetType.POST,
            post=post,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def comment_report(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    serializer = ReportCreateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(
            reporter=request.user,
            target_type=Report.TargetType.COMMENT,
            comment=comment,
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def post_scrap(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "POST":
        scrap, created = Scrap.objects.get_or_create(user=request.user, post=post)
        if not created:
            return Response(
                {"detail": "이미 스크랩한 게시글입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ScrapSerializer(scrap)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    scrap = Scrap.objects.filter(user=request.user, post=post).first()
    if not scrap:
        return Response(
            {"detail": "스크랩하지 않은 게시글입니다."},
            status=status.HTTP_404_NOT_FOUND,
        )
    scrap.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def scrap_list(request):
    scraps = Scrap.objects.filter(user=request.user)
    serializer = ScrapSerializer(scraps, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)