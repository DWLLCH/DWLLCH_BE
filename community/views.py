from django.db.models import F
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Post
from .serializers import (
    PostCreateUpdateSerializer,
    PostDetailSerializer,
    PostListSerializer,
)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def post_list(request):
    if request.method == "GET":
        posts = Post.objects.select_related("author").all()

        board_type = request.query_params.get("board_type")
        if board_type:
            posts = posts.filter(board_type=board_type)

        serializer = PostListSerializer(posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    serializer = PostCreateUpdateSerializer(data=request.data)
    if serializer.is_valid():
        post = serializer.save(author=request.user)
        return Response(
            PostDetailSerializer(post, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == "GET":
        Post.objects.filter(id=post.id).update(view_count=F("view_count") + 1)
        post.refresh_from_db()
        serializer = PostDetailSerializer(post, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    if post.author != request.user:
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
