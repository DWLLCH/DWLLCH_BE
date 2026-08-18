import json

from django.db.models import (
    F,
    Q,
    Count,
    Exists,
    OuterRef,
    Value,
    BooleanField,
)
from django.db import transaction
from django.http import QueryDict
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
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
    PostImage,
    Poll, PollOption, PollVote,
)
from .serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateUpdateSerializer,
    PostPinSerializer,
    CommentSerializer,
    CommentCreateUpdateSerializer,
    MyCommentSerializer,
    ReportCreateSerializer,
    ScrapSerializer,
    PollSerializer,
)

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGE_COUNT = 5
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]


def validate_image_file(image_file):
    if image_file.content_type not in ALLOWED_IMAGE_TYPES:
        raise ValidationError(
            {"images": f"{image_file.name}: JPEG, PNG, WEBP 형식만 업로드 가능합니다."}
        )
    if image_file.size > MAX_IMAGE_SIZE:
        raise ValidationError(
            {"images": f"{image_file.name}: 이미지 크기는 5MB 이하여야 합니다."}
        )


def parse_post_request_data(request):
    """
    multipart/form-data 요청에서 JSON 문자열로 전달되는
    poll, keepImageIds 필드를 Python 객체로 변환한다.
    """
    data = request.data

    if not isinstance(data, QueryDict):
        return data

    data = data.dict()

    poll_raw = data.get("poll")

    if poll_raw:
        try:
            data["poll"] = json.loads(poll_raw)
        except (TypeError, ValueError):
            raise ValidationError(
                {
                    "poll": (
                        "poll은 올바른 JSON 문자열이어야 합니다."
                    )
                }
            )

    if "keepImageIds" in data:
        keep_image_ids_raw = data.get("keepImageIds")

        try:
            keep_image_ids = json.loads(keep_image_ids_raw)
        except (TypeError, ValueError):
            raise ValidationError(
                {
                    "keepImageIds": (
                        "keepImageIds는 올바른 JSON 배열이어야 합니다."
                    )
                }
            )

        if not isinstance(keep_image_ids, list):
            raise ValidationError(
                {
                    "keepImageIds": (
                        "keepImageIds는 배열 형태여야 합니다."
                    )
                }
            )

        data["keepImageIds"] = keep_image_ids

    return data

def apply_poll_update(post, poll_data):
    """게시글의 설문을 poll_data로 교체한다. 이미 투표가 있으면 수정을 막고,
    설문이 없던 게시글이면 새로 만든다."""
    existing_poll = getattr(post, "poll", None)

    if existing_poll:
        if PollVote.objects.filter(option__poll=existing_poll).exists():
            raise ValidationError({"poll": "투표가 진행된 설문은 수정할 수 없습니다."})

        existing_poll.question = poll_data["question"]
        existing_poll.allow_multiple = poll_data.get("allow_multiple", False)
        existing_poll.save()
        existing_poll.options.all().delete()
        poll = existing_poll
    else:
        poll = Poll.objects.create(
            post=post,
            question=poll_data["question"],
            allow_multiple=poll_data.get("allow_multiple", False),
        )

    for order, option_data in enumerate(poll_data["options"]):
        PollOption.objects.create(poll=poll, text=option_data["text"], order=order)

def apply_post_image_update(
    post,
    keep_image_ids,
    new_images,
):
    """
    게시글 수정 시 이미지 유지/삭제/추가를 처리한다.

    keep_image_ids가 None:
        기존 이미지를 모두 유지

    keep_image_ids가 []:
        기존 이미지를 모두 삭제

    keep_image_ids가 [1, 3]:
        해당 id 이미지만 유지

    new_images:
        유지 이미지 뒤에 신규 이미지 추가
    """

    existing_images = list(
        post.images.order_by("order", "id")
    )

    existing_image_ids = {
        image.id
        for image in existing_images
    }

    if keep_image_ids is None:
        kept_images = existing_images

    else:
        requested_ids = set(keep_image_ids)

        invalid_ids = (
            requested_ids
            - existing_image_ids
        )

        if invalid_ids:
            raise ValidationError(
                {
                    "keepImageIds": (
                        "해당 게시글에 속하지 않는 "
                        f"이미지 id가 포함되어 있습니다: "
                        f"{sorted(invalid_ids)}"
                    )
                }
            )

        kept_images = [
            image
            for image in existing_images
            if image.id in requested_ids
        ]

    for image_file in new_images:
        validate_image_file(image_file)

    final_image_count = (
        len(kept_images)
        + len(new_images)
    )

    if final_image_count > MAX_IMAGE_COUNT:
        raise ValidationError(
            {
                "images": (
                    f"이미지는 최대 "
                    f"{MAX_IMAGE_COUNT}장까지 "
                    "등록할 수 있습니다."
                )
            }
        )

    # keepImageIds가 전달된 경우에만
    # 기존 이미지 삭제 여부를 판단한다.
    if keep_image_ids is not None:
        keep_ids = [
            image.id
            for image in kept_images
        ]

        delete_queryset = post.images.all()

        if keep_ids:
            delete_queryset = (
                delete_queryset.exclude(
                    id__in=keep_ids
                )
            )

        delete_queryset.delete()

    # 유지 이미지 순서 재정렬
    for order, image in enumerate(kept_images):
        if image.order != order:
            image.order = order
            image.save(
                update_fields=["order"]
            )

    # 신규 이미지는 기존 이미지 뒤에 추가
    start_order = len(kept_images)

    for offset, image_file in enumerate(
        new_images
    ):
        PostImage.objects.create(
            post=post,
            image=image_file,
            order=start_order + offset,
        )

@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
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

    serializer = PostCreateUpdateSerializer(data=parse_post_request_data(request))
    serializer.is_valid(raise_exception=True)

    poll_data = serializer.validated_data.pop("poll", None)

    serializer.validated_data.pop("keepImageIds", None)

    images = request.FILES.getlist("images")

    if len(images) > MAX_IMAGE_COUNT:
        raise ValidationError(
            {"images": f"이미지는 최대 {MAX_IMAGE_COUNT}장까지 업로드 가능합니다."}
        )

    for image_file in images:
        validate_image_file(image_file)

    post = serializer.save(
        author=request.user,
        board_type=board_type,
    )

    for order, image_file in enumerate(images):
        PostImage.objects.create(post=post, image=image_file, order=order)

    if poll_data:
        poll = Poll.objects.create(
            post=post,
            question=poll_data["question"],
            allow_multiple=poll_data.get("allow_multiple", False),
        )
        for order, option_data in enumerate(poll_data["options"]):
            PollOption.objects.create(poll=poll, text=option_data["text"], order=order)

    return success_response(
        data=PostDetailSerializer(post, context={"request": request}).data,
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
@parser_classes([MultiPartParser, FormParser, JSONParser])
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
            data=parse_post_request_data(request),
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True
        )

        poll_provided = (
            "poll"
            in serializer.validated_data
        )

        poll_data = (
            serializer.validated_data.pop(
                "poll",
                None,
            )
        )

        keep_image_ids_provided = (
            "keepImageIds"
            in serializer.validated_data
        )

        keep_image_ids = (
            serializer.validated_data.pop(
                "keepImageIds",
                None,
            )
        )

        new_images = (
            request.FILES.getlist("images")
        )

        with transaction.atomic():
            serializer.save()

            if poll_provided:
                apply_poll_update(
                    post,
                    poll_data,
                )

            if (
                keep_image_ids_provided
                or new_images
            ):
                apply_post_image_update(
                    post=post,
                    keep_image_ids=(
                        keep_image_ids
                        if keep_image_ids_provided
                        else None
                    ),
                    new_images=new_images,
                )

        post.refresh_from_db()

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

        if parent.post_id != post.id:
            raise ValidationError(
                {
                    "parentId": (
                        "같은 게시글의 댓글에만 "
                        "답글을 작성할 수 있습니다."
                    )
                }
            )

        if parent.parent_id is not None:
            raise ValidationError(
                {
                    "parentId": (
                        "대댓글에는 답글을 작성할 수 없습니다."
                    )
                }
            )

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

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_posts(request):
    posts = Post.objects.filter(author=request.user).order_by("-created_at")
    paginator = CommonPageNumberPagination()
    page = paginator.paginate_queryset(posts, request)
    serializer = PostListSerializer(page, many=True, context={"request": request})
    return paginator.get_paginated_response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_comments(request):
    comments = (
        Comment.objects
        .filter(author=request.user)
        .select_related("post", "author")
        .order_by("-created_at", "-id")
    )

    paginator = CommonPageNumberPagination()
    page = paginator.paginate_queryset(comments, request)

    serializer = MyCommentSerializer(page, many=True)

    return paginator.get_paginated_response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def poll_vote(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    poll = get_object_or_404(Poll, post=post)

    option_ids = request.data.get("optionIds")

    if not option_ids or not isinstance(option_ids, list):
        raise ValidationError({"optionIds": "선택지 id 목록을 배열로 보내주세요."})

    if not poll.allow_multiple and len(option_ids) > 1:
        raise ValidationError({"optionIds": "이 설문은 단일 선택만 가능합니다."})

    options = PollOption.objects.filter(poll=poll, id__in=option_ids)

    if options.count() != len(set(option_ids)):
        raise ValidationError({"optionIds": "유효하지 않은 선택지가 포함되어 있습니다."})

    already_voted = PollVote.objects.filter(option__poll=poll, user=request.user).exists()
    if already_voted:
        raise ValidationError({"detail": "이미 투표하셨습니다."})

    for option in options:
        PollVote.objects.create(option=option, user=request.user)

    return success_response(
        data=PollSerializer(poll, context={"request": request}).data,
        message="투표가 완료되었습니다.",
        status_code=status.HTTP_201_CREATED,
    )