import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

# Create your tests here.
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    Post,
    Comment,
    PostAnonymousAlias,
    PostLike,
    CommentLike,
    PostImage,
    Poll,
    PollOption,
    PollVote,
)

User = get_user_model()


class CommunityLikeTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            username="testuser",
            password="Test1234!",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            username="otheruser",
            password="Test1234!",
        )

        self.post = Post.objects.create(
            board_type=Post.BoardType.FREE,
            author=self.other_user,
            title="테스트 게시글",
            content="테스트 내용입니다.",
        )

        self.comment = Comment.objects.create(
            post=self.post,
            author=self.other_user,
            content="테스트 댓글입니다.",
        )

        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        self.post_like_url = (
            f"/community/posts/{self.post.id}/like"
        )
        self.comment_like_url = (
            f"/community/comments/{self.comment.id}/like"
        )

    def test_post_like_create_success(self):
        response = self.client.post(
            self.post_like_url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            PostLike.objects.filter(
                user=self.user,
                post=self.post,
            ).exists()
        )

        self.assertEqual(
            response.data["data"]["postId"],
            self.post.id,
        )

        self.assertEqual(
            response.data["data"]["likeCount"],
            1,
        )

        self.assertTrue(
            response.data["data"]["isLiked"]
        )

    def test_post_like_duplicate_fail(self):
        PostLike.objects.create(
            user=self.user,
            post=self.post,
        )

        response = self.client.post(
            self.post_like_url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            PostLike.objects.filter(
                user=self.user,
                post=self.post,
            ).count(),
            1,
        )

    def test_post_like_delete_success(self):
        PostLike.objects.create(
            user=self.user,
            post=self.post,
        )

        response = self.client.delete(
            self.post_like_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            PostLike.objects.filter(
                user=self.user,
                post=self.post,
            ).exists()
        )

    def test_post_like_delete_without_like_fail(self):
        response = self.client.delete(
            self.post_like_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_comment_like_create_success(self):
        response = self.client.post(
            self.comment_like_url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            CommentLike.objects.filter(
                user=self.user,
                comment=self.comment,
            ).exists()
        )

        self.assertEqual(
            response.data["data"]["commentId"],
            self.comment.id,
        )

        self.assertEqual(
            response.data["data"]["likeCount"],
            1,
        )

        self.assertTrue(
            response.data["data"]["isLiked"]
        )

    def test_comment_like_duplicate_fail(self):
        CommentLike.objects.create(
            user=self.user,
            comment=self.comment,
        )

        response = self.client.post(
            self.comment_like_url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            CommentLike.objects.filter(
                user=self.user,
                comment=self.comment,
            ).count(),
            1,
        )

    def test_comment_like_delete_success(self):
        CommentLike.objects.create(
            user=self.user,
            comment=self.comment,
        )

        response = self.client.delete(
            self.comment_like_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            CommentLike.objects.filter(
                user=self.user,
                comment=self.comment,
            ).exists()
        )

    def test_comment_like_delete_without_like_fail(self):
        response = self.client.delete(
            self.comment_like_url,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_post_detail_returns_like_info(self):
        PostLike.objects.create(
            user=self.user,
            post=self.post,
        )

        response = self.client.get(
            f"/community/posts/{self.post.id}"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["data"]["likeCount"],
            1,
        )

        self.assertTrue(
            response.data["data"]["isLiked"]
        )

    def test_post_list_returns_like_info(self):
        PostLike.objects.create(
            user=self.user,
            post=self.post,
        )

        response = self.client.get(
            f"/community/boards/{Post.BoardType.FREE}/posts"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        post_data = response.data["content"][0]

        self.assertEqual(
            post_data["likeCount"],
            1,
        )

        self.assertTrue(
            post_data["isLiked"]
        )

    def test_comment_list_returns_like_info(self):
        CommentLike.objects.create(
            user=self.user,
            comment=self.comment,
        )

        response = self.client.get(
            f"/community/posts/{self.post.id}/comments"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        comment_data = response.data["data"]["comments"][0]

        self.assertEqual(
            comment_data["likeCount"],
            1,
        )

        self.assertTrue(
            comment_data["isLiked"]
        )

    def test_unauthenticated_post_like_fail(self):
        self.client.credentials()

        response = self.client.post(
            self.post_like_url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_unauthenticated_comment_like_fail(self):
        self.client.credentials()

        response = self.client.post(
            self.comment_like_url,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class CommunityReplyTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="reply@example.com",
            username="replyuser",
            password="Test1234!",
        )

        self.other_user = User.objects.create_user(
            email="other-reply@example.com",
            username="otherreply",
            password="Test1234!",
        )

        self.post = Post.objects.create(
            board_type=Post.BoardType.FREE,
            author=self.user,
            title="대댓글 테스트 게시글",
            content="테스트 내용",
        )

        self.other_post = Post.objects.create(
            board_type=Post.BoardType.FREE,
            author=self.other_user,
            title="다른 게시글",
            content="다른 게시글 내용",
        )

        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        self.comment_list_url = (
            f"/community/posts/{self.post.id}/comments"
        )

    def test_parent_comment_create_success(self):
        response = self.client.post(
            self.comment_list_url,
            {
                "content": "일반 댓글입니다.",
                "isAnonymous": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        comment = Comment.objects.get(
            content="일반 댓글입니다."
        )

        self.assertIsNone(comment.parent)

    def test_reply_create_success(self):
        parent = Comment.objects.create(
            post=self.post,
            author=self.user,
            content="부모 댓글",
        )

        response = self.client.post(
            self.comment_list_url,
            {
                "content": "대댓글입니다.",
                "parentId": parent.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        reply = Comment.objects.get(
            content="대댓글입니다."
        )

        self.assertEqual(
            reply.parent_id,
            parent.id,
        )

        self.assertEqual(
            reply.post_id,
            self.post.id,
        )

    def test_reply_parent_not_found_fail(self):
        response = self.client.post(
            self.comment_list_url,
            {
                "content": "대댓글입니다.",
                "parentId": 999999,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_reply_to_other_post_comment_fail(self):
        parent = Comment.objects.create(
            post=self.other_post,
            author=self.other_user,
            content="다른 게시글 댓글",
        )

        response = self.client.post(
            self.comment_list_url,
            {
                "content": "잘못된 대댓글",
                "parentId": parent.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_reply_to_reply_fail(self):
        parent = Comment.objects.create(
            post=self.post,
            author=self.user,
            content="부모 댓글",
        )

        reply = Comment.objects.create(
            post=self.post,
            author=self.user,
            parent=parent,
            content="1단계 대댓글",
        )

        response = self.client.post(
            self.comment_list_url,
            {
                "content": "2단계 대댓글",
                "parentId": reply.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_comment_without_replies_hard_delete(self):
        comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            content="삭제할 댓글",
        )

        response = self.client.delete(
            f"/community/comments/{comment.id}"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Comment.objects.filter(
                id=comment.id
            ).exists()
        )

    def test_parent_comment_with_reply_soft_delete(self):
        parent = Comment.objects.create(
            post=self.post,
            author=self.user,
            content="삭제할 부모 댓글",
        )

        reply = Comment.objects.create(
            post=self.post,
            author=self.other_user,
            parent=parent,
            content="유지되어야 할 대댓글",
        )

        response = self.client.delete(
            f"/community/comments/{parent.id}"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        parent.refresh_from_db()

        self.assertTrue(
            parent.is_deleted
        )

        self.assertTrue(
            Comment.objects.filter(
                id=reply.id
            ).exists()
        )

        self.assertEqual(
            reply.parent_id,
            parent.id,
        )

    def test_deleted_parent_comment_response(self):
        parent = Comment.objects.create(
            post=self.post,
            author=self.user,
            content="원래 댓글 내용",
            is_deleted=True,
        )

        Comment.objects.create(
            post=self.post,
            author=self.other_user,
            parent=parent,
            content="대댓글",
        )

        response = self.client.get(
            self.comment_list_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        comments = response.data["data"]["comments"]

        parent_data = next(
            item
            for item in comments
            if item["id"] == parent.id
        )

        self.assertEqual(
            parent_data["content"],
            "삭제된 댓글입니다.",
        )

        self.assertTrue(
            parent_data["isDeleted"]
        )

    def test_deleted_comment_patch_fail(self):
        comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            content="삭제된 댓글",
            is_deleted=True,
        )

        response = self.client.patch(
            f"/community/comments/{comment.id}",
            {
                "content": "수정 시도",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        comment.refresh_from_db()

        self.assertEqual(
            comment.content,
            "삭제된 댓글",
        )

    def test_reply_to_deleted_parent_fail(self):
        parent = Comment.objects.create(
            post=self.post,
            author=self.user,
            content="삭제된 부모 댓글",
            is_deleted=True,
        )

        response = self.client.post(
            self.comment_list_url,
            {
                "content": "답글 작성 시도",
                "parentId": parent.id,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_parent_id_returned_in_comment_response(self):
        parent = Comment.objects.create(
            post=self.post,
            author=self.user,
            content="부모 댓글",
        )

        reply = Comment.objects.create(
            post=self.post,
            author=self.user,
            parent=parent,
            content="대댓글",
        )

        response = self.client.get(
            self.comment_list_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        comments = response.data["data"]["comments"]

        reply_data = next(
            item
            for item in comments
            if item["id"] == reply.id
        )

        self.assertEqual(
            reply_data["parentId"],
            parent.id,
        )

class CommunityPinnedPostTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            username="user",
            password="Test1234!",
        )

        self.admin = User.objects.create_user(
            email="admin@example.com",
            username="admin",
            password="Test1234!",
            is_staff=True,
        )

        self.free_post = Post.objects.create(
            board_type=Post.BoardType.FREE,
            author=self.user,
            title="자유 게시글",
            content="내용",
        )

        self.tip_pinned_post = Post.objects.create(
            board_type=Post.BoardType.TIP,
            author=self.admin,
            title="TIP 고정 공지",
            content="공지 내용",
            is_pinned=True,
        )

        self.worry_pinned_post = Post.objects.create(
            board_type=Post.BoardType.WORRY,
            author=self.admin,
            title="WORRY 고정 공지",
            content="공지 내용",
            is_pinned=True,
        )

    def authenticate(self, user):
        refresh = RefreshToken.for_user(user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

    def test_admin_can_pin_post(self):
        self.authenticate(self.admin)

        response = self.client.patch(
            f"/community/posts/{self.free_post.id}/pin",
            {
                "isPinned": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.free_post.refresh_from_db()

        self.assertTrue(
            self.free_post.is_pinned
        )

    def test_admin_can_unpin_post(self):
        self.free_post.is_pinned = True
        self.free_post.save()

        self.authenticate(self.admin)

        response = self.client.patch(
            f"/community/posts/{self.free_post.id}/pin",
            {
                "isPinned": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.free_post.refresh_from_db()

        self.assertFalse(
            self.free_post.is_pinned
        )

    def test_normal_user_cannot_pin_post(self):
        self.authenticate(self.user)

        response = self.client.patch(
            f"/community/posts/{self.free_post.id}/pin",
            {
                "isPinned": True,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_pinned_posts_are_included_across_board_types(self):
        response = self.client.get(
            "/community/boards/FREE/posts"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        posts = response.data["content"]

        post_ids = [
            post["id"]
            for post in posts
        ]

        self.assertIn(
            self.tip_pinned_post.id,
            post_ids,
        )

        self.assertIn(
            self.worry_pinned_post.id,
            post_ids,
        )

        self.assertIn(
            self.free_post.id,
            post_ids,
        )

    def test_pinned_posts_are_ordered_first(self):
        response = self.client.get(
            "/community/boards/FREE/posts"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        posts = response.data["content"]

        pinned_flags = [
            post["isPinned"]
            for post in posts
        ]

        first_normal_index = next(
            (
                index
                for index, is_pinned in enumerate(pinned_flags)
                if not is_pinned
            ),
            len(pinned_flags),
        )

        self.assertTrue(
            all(
                pinned_flags[index]
                for index in range(first_normal_index)
            )
        )

class CommunityLatestPostTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="latest@example.com",
            username="latestuser",
            password="Test1234!",
        )

        self.tip_post = Post.objects.create(
            board_type=Post.BoardType.TIP,
            author=self.user,
            title="꿀팁 글",
            content="꿀팁 내용",
        )

        self.worry_post = Post.objects.create(
            board_type=Post.BoardType.WORRY,
            author=self.user,
            title="고민 글",
            content="고민 내용",
        )

        self.free_post = Post.objects.create(
            board_type=Post.BoardType.FREE,
            author=self.user,
            title="자유 글",
            content="자유 내용",
        )

        self.url = "/community/posts"

    def test_latest_posts_include_all_board_types(self):
        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        posts = response.data["content"]

        post_ids = [
            post["id"]
            for post in posts
        ]

        self.assertIn(
            self.tip_post.id,
            post_ids,
        )
        self.assertIn(
            self.worry_post.id,
            post_ids,
        )
        self.assertIn(
            self.free_post.id,
            post_ids,
        )

    def test_latest_posts_return_board_type(self):
        response = self.client.get(
            self.url
        )

        posts = response.data["content"]

        board_types = {
            post["boardType"]
            for post in posts
        }

        self.assertIn(
            Post.BoardType.TIP,
            board_types,
        )
        self.assertIn(
            Post.BoardType.WORRY,
            board_types,
        )
        self.assertIn(
            Post.BoardType.FREE,
            board_types,
        )

    def test_pinned_post_is_ordered_first(self):
        pinned_post = Post.objects.create(
            board_type=Post.BoardType.TIP,
            author=self.user,
            title="고정 공지",
            content="공지입니다.",
            is_pinned=True,
        )

        response = self.client.get(self.url)

        posts = response.data["content"]

        self.assertEqual(posts[0]["id"], pinned_post.id,)
        self.assertTrue(posts[0]["isPinned"])

    def test_latest_posts_pagination(self):
        for index in range(25):
            Post.objects.create(
                board_type=Post.BoardType.FREE,
                author=self.user,
                title=f"게시글 {index}",
                content="내용",
            )

        response = self.client.get(f"{self.url}?page=0&size=20")

        self.assertEqual(response.status_code, status.HTTP_200_OK,)

        self.assertEqual(len(response.data["content"]), 20,)

        self.assertTrue(response.data["hasNext"])

    def test_latest_posts_stable_order_with_same_created_at(self):
        post1 = Post.objects.create(
            board_type=Post.BoardType.FREE,
            author=self.user,
            title="동일 시간 글 1",
            content="내용",
        )

        post2 = Post.objects.create(
            board_type=Post.BoardType.FREE,
            author=self.user,
            title="동일 시간 글 2",
            content="내용",
        )

        same_time = post1.created_at

        Post.objects.filter(id__in=[post1.id, post2.id]).update(created_at=same_time)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK,)

        posts = response.data["content"]

        matching_ids = [
            post["id"]
            for post in posts
            if post["id"] in [post1.id, post2.id]
        ]

        self.assertEqual(
            matching_ids,
            sorted([post1.id, post2.id], reverse=True,),
        )


class CommunityPollPatchTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="poll-author@example.com",
            username="pollauthor",
            password="Test1234!",
        )

        self.voter = User.objects.create_user(
            email="poll-voter@example.com",
            username="pollvoter",
            password="Test1234!",
        )

        self.post = Post.objects.create(
            board_type=Post.BoardType.FREE,
            author=self.user,
            title="설문 게시글",
            content="내용",
        )

        self.poll = Poll.objects.create(
            post=self.post,
            question="원래 질문",
            allow_multiple=False,
        )

        self.option_a = PollOption.objects.create(poll=self.poll, text="A", order=0)
        self.option_b = PollOption.objects.create(poll=self.poll, text="B", order=1)

        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

        self.url = f"/community/posts/{self.post.id}"

    def test_poll_patch_without_votes_succeeds(self):
        response = self.client.patch(
            self.url,
            {
                "poll": {
                    "question": "새 질문",
                    "allowMultiple": True,
                    "options": [{"text": "X"}, {"text": "Y"}, {"text": "Z"}],
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.poll.refresh_from_db()
        self.assertEqual(self.poll.question, "새 질문")
        self.assertTrue(self.poll.allow_multiple)

        option_texts = list(
            self.poll.options.order_by("order").values_list("text", flat=True)
        )
        self.assertEqual(option_texts, ["X", "Y", "Z"])

    def test_poll_patch_with_votes_fails_and_keeps_original(self):
        PollVote.objects.create(option=self.option_a, user=self.voter)

        response = self.client.patch(
            self.url,
            {
                "title": "제목만 바꾸려는 시도",
                "poll": {
                    "question": "바뀌면 안 되는 질문",
                    "options": [{"text": "X"}, {"text": "Y"}],
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.post.refresh_from_db()
        self.poll.refresh_from_db()

        self.assertNotEqual(self.post.title, "제목만 바꾸려는 시도")
        self.assertEqual(self.poll.question, "원래 질문")

        option_texts = list(
            self.poll.options.order_by("order").values_list("text", flat=True)
        )
        self.assertEqual(option_texts, ["A", "B"])

    def test_poll_patch_adds_poll_to_post_without_one(self):
        plain_post = Post.objects.create(
            board_type=Post.BoardType.FREE,
            author=self.user,
            title="설문 없는 글",
            content="내용",
        )

        response = self.client.patch(
            f"/community/posts/{plain_post.id}",
            {
                "poll": {
                    "question": "새로 추가된 설문",
                    "options": [{"text": "1번"}, {"text": "2번"}],
                },
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        plain_post.refresh_from_db()
        self.assertIsNotNone(getattr(plain_post, "poll", None))
        self.assertEqual(plain_post.poll.question, "새로 추가된 설문")

    def test_poll_patch_without_poll_field_leaves_poll_untouched(self):
        response = self.client.patch(
            self.url,
            {
                "title": "제목만 수정",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.post.refresh_from_db()
        self.poll.refresh_from_db()

        self.assertEqual(self.post.title, "제목만 수정")
        self.assertEqual(self.poll.question, "원래 질문")

    def test_poll_patch_multipart_json_string_parsed(self):
        image = SimpleUploadedFile(
            "poll.jpg", b"fake-image-bytes", content_type="image/jpeg"
        )

        response = self.client.patch(
            self.url,
            {
                "images": [image],
                "poll": json.dumps(
                    {
                        "question": "멀티파트 질문",
                        "options": [{"text": "가"}, {"text": "나"}],
                    }
                ),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.poll.refresh_from_db()
        self.assertEqual(self.poll.question, "멀티파트 질문")

class CommunityPostPatchTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="patch@example.com",
            username="patchuser",
            password="Test1234!",
        )

        self.other_user = User.objects.create_user(
            email="patch-other@example.com",
            username="patchother",
            password="Test1234!",
        )

        self.post = Post.objects.create(
            board_type=Post.BoardType.FREE,
            author=self.user,
            title="수정 전 제목",
            content="수정 전 내용",
        )

        self.image1 = PostImage.objects.create(
            post=self.post,
            image="community/posts/old1.jpg",
            order=0,
        )

        self.image2 = PostImage.objects.create(
            post=self.post,
            image="community/posts/old2.jpg",
            order=1,
        )

        refresh = RefreshToken.for_user(
            self.user
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=(
                f"Bearer {refresh.access_token}"
            )
        )

        self.url = (
            f"/community/posts/{self.post.id}"
        )

    def test_board_type_patch_success(self):
        response = self.client.patch(
            self.url,
            {
                "boardType": Post.BoardType.WORRY,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.post.refresh_from_db()

        self.assertEqual(
            self.post.board_type,
            Post.BoardType.WORRY,
        )

    def test_invalid_board_type_patch_fail(self):
        response = self.client.patch(
            self.url,
            {
                "boardType": "INVALID",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_keep_image_ids_deletes_unselected_images(self):
        response = self.client.patch(
            self.url,
            {
                "keepImageIds": json.dumps(
                    [self.image1.id]
                ),
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            PostImage.objects.filter(
                id=self.image1.id
            ).exists()
        )

        self.assertFalse(
            PostImage.objects.filter(
                id=self.image2.id
            ).exists()
        )

    def test_empty_keep_image_ids_deletes_all_images(self):
        response = self.client.patch(
            self.url,
            {
                "keepImageIds": json.dumps([]),
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            self.post.images.count(),
            0,
        )

    def test_missing_keep_image_ids_keeps_existing_images(self):
        response = self.client.patch(
            self.url,
            {
                "title": "제목만 수정",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            self.post.images.count(),
            2,
        )

    def test_add_new_image_without_keep_ids_keeps_old_images(self):
        new_image = SimpleUploadedFile(
            "new.jpg",
            b"new-image-bytes",
            content_type="image/jpeg",
        )

        response = self.client.patch(
            self.url,
            {
                "images": [new_image],
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            self.post.images.count(),
            3,
        )

    def test_keep_image_and_add_new_image(self):
        new_image = SimpleUploadedFile(
            "new2.jpg",
            b"new-image-bytes",
            content_type="image/jpeg",
        )

        response = self.client.patch(
            self.url,
            {
                "keepImageIds": json.dumps(
                    [self.image2.id]
                ),
                "images": [new_image],
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        images = list(
            self.post.images.order_by(
                "order",
                "id",
            )
        )

        self.assertEqual(
            len(images),
            2,
        )

        self.assertEqual(
            images[0].id,
            self.image2.id,
        )

        self.assertEqual(
            images[0].order,
            0,
        )

        self.assertEqual(
            images[1].order,
            1,
        )

    def test_other_post_image_id_fails(self):
        other_post = Post.objects.create(
            board_type=Post.BoardType.FREE,
            author=self.other_user,
            title="다른 게시글",
            content="다른 내용",
        )

        other_image = PostImage.objects.create(
            post=other_post,
            image="community/posts/other.jpg",
            order=0,
        )

        response = self.client.patch(
            self.url,
            {
                "keepImageIds": json.dumps(
                    [
                        self.image1.id,
                        other_image.id,
                    ]
                ),
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertTrue(
            PostImage.objects.filter(
                id=self.image1.id
            ).exists()
        )

        self.assertTrue(
            PostImage.objects.filter(
                id=self.image2.id
            ).exists()
        )

    def test_image_count_over_five_fails(self):
        for index in range(3):
            PostImage.objects.create(
                post=self.post,
                image=(
                    f"community/posts/"
                    f"extra{index}.jpg"
                ),
                order=index + 2,
            )

        new_image = SimpleUploadedFile(
            "sixth.jpg",
            b"sixth-image",
            content_type="image/jpeg",
        )

        response = self.client.patch(
            self.url,
            {
                "images": [new_image],
            },
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            self.post.images.count(),
            5,
        )

class MyCommentListTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="mycomment@example.com",
            username="mycommentuser",
            password="Test1234!",
        )

        self.other_user = User.objects.create_user(
            email="othercomment@example.com",
            username="othercommentuser",
            password="Test1234!",
        )

        self.post = Post.objects.create(
            board_type=Post.BoardType.WORRY,
            author=self.other_user,
            title="주변에 의지할 어른이 없다는 게",
            content="게시글 내용",
        )

        self.other_post = Post.objects.create(
            board_type=Post.BoardType.TIP,
            author=self.other_user,
            title="국민취업지원제도 후기",
            content="게시글 내용",
        )

        self.comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            content="저도 비슷한 시기가 있었어요.",
        )

        self.second_comment = Comment.objects.create(
            post=self.other_post,
            author=self.user,
            content="좋은 정보 감사합니다.",
        )

        Comment.objects.create(
            post=self.post,
            author=self.other_user,
            content="다른 사용자의 댓글",
        )

        refresh = RefreshToken.for_user(self.user)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}"
        )

        self.url = "/community/comments/mine"

    def test_my_comments_success(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        comments = response.data["content"]

        self.assertEqual(
            len(comments),
            2,
        )

    def test_my_comments_include_post_info(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        comments = response.data["content"]

        target = next(
            comment
            for comment in comments
            if comment["id"] == self.comment.id
        )

        self.assertEqual(
            target["content"],
            "저도 비슷한 시기가 있었어요.",
        )

        self.assertEqual(
            target["postId"],
            self.post.id,
        )

        self.assertEqual(
            target["postTitle"],
            "주변에 의지할 어른이 없다는 게",
        )

        self.assertEqual(
            target["boardType"],
            Post.BoardType.WORRY,
        )

        self.assertIn(
            "createdAt",
            target,
        )

    def test_my_comments_exclude_other_users_comments(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        comments = response.data["content"]

        contents = [
            comment["content"]
            for comment in comments
        ]

        self.assertNotIn(
            "다른 사용자의 댓글",
            contents,
        )

    def test_my_comments_ordered_by_latest(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        comments = response.data["content"]

        self.assertEqual(
            comments[0]["id"],
            self.second_comment.id,
        )

        self.assertEqual(
            comments[1]["id"],
            self.comment.id,
        )

    def test_my_comments_unauthenticated_fail(self):
        self.client.credentials()

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class CommentAnonymousSequenceTest(APITestCase):
    """게시글 안에서 작성자별로 발급되는 익명 번호."""

    def setUp(self):
        self.owner = self.create_user("anon-owner@example.com", "anonowner")
        self.first = self.create_user("anon-first@example.com", "anonfirst")
        self.second = self.create_user("anon-second@example.com", "anonsecond")

        self.post = Post.objects.create(
            author=self.owner,
            board_type=Post.BoardType.FREE,
            title="익명 번호 테스트 게시글",
            content="본문",
        )

        self.url = f"/community/posts/{self.post.id}/comments"

    def create_user(self, email, username):
        return User.objects.create_user(
            email=email,
            username=username,
            password="Test1234!",
        )

    def write(self, user, content, is_anonymous=True, parent_id=None):
        self.client.force_authenticate(user=user)

        payload = {"content": content, "isAnonymous": is_anonymous}

        if parent_id is not None:
            payload["parentId"] = parent_id

        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        return response.data["data"]

    def listing(self):
        self.client.force_authenticate(user=self.owner)

        return self.client.get(self.url).data["data"]["comments"]

    def delete(self, comment_id, user):
        self.client.force_authenticate(user=user)

        return self.client.delete(
            f"/community/comments/{comment_id}"
        ).status_code

    def test_sequence_starts_at_one_per_post(self):
        first = self.write(self.first, "첫 익명")
        second = self.write(self.second, "두 번째 익명")

        self.assertEqual(first["anonymousSequence"], 1)
        self.assertEqual(second["anonymousSequence"], 2)

    def test_same_author_keeps_the_same_number(self):
        first = self.write(self.first, "첫 댓글")
        again = self.write(self.first, "두 번째 댓글")

        self.assertEqual(first["anonymousSequence"], again["anonymousSequence"])

    def test_named_comment_has_no_sequence(self):
        comment = self.write(self.owner, "실명 댓글", is_anonymous=False)

        self.assertIsNone(comment["anonymousSequence"])

    def test_number_survives_hard_delete_of_every_comment(self):
        """댓글을 모두 지워도 번호는 남아, 다시 쓰면 같은 번호를 받는다."""
        first = self.write(self.first, "지울 댓글")

        self.assertEqual(
            self.delete(first["id"], self.first),
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Comment.objects.filter(post=self.post, author=self.first).exists()
        )

        again = self.write(self.first, "다시 쓴 댓글")

        self.assertEqual(again["anonymousSequence"], 1)

    def test_number_is_not_reused_by_another_author(self):
        """지운 사람의 번호를 다음 사람이 물려받지 않는다."""
        first = self.write(self.first, "지울 댓글")
        self.delete(first["id"], self.first)

        second = self.write(self.second, "다른 사람 댓글")

        self.assertEqual(second["anonymousSequence"], 2)

    def test_numbers_are_scoped_to_each_post(self):
        other_post = Post.objects.create(
            author=self.owner,
            board_type=Post.BoardType.FREE,
            title="다른 게시글",
            content="본문",
        )

        self.write(self.first, "첫 글의 익명")

        self.client.force_authenticate(user=self.second)
        response = self.client.post(
            f"/community/posts/{other_post.id}/comments",
            {"content": "다른 글의 첫 익명", "isAnonymous": True},
            format="json",
        )

        self.assertEqual(response.data["data"]["anonymousSequence"], 1)

    def test_soft_deleted_comment_keeps_its_number(self):
        parent = self.write(self.first, "답글 달릴 댓글")
        self.write(self.second, "답글", parent_id=parent["id"])
        self.delete(parent["id"], self.first)

        listed = next(
            item for item in self.listing() if item["id"] == parent["id"]
        )

        self.assertEqual(listed["content"], "삭제된 댓글입니다.")
        self.assertEqual(listed["anonymousSequence"], 1)

    def test_alias_is_not_issued_for_named_comments(self):
        self.write(self.first, "실명 댓글", is_anonymous=False)

        self.assertFalse(
            PostAnonymousAlias.objects.filter(
                post=self.post, author=self.first
            ).exists()
        )

    def test_comment_list_does_not_query_per_comment(self):
        """댓글 수가 늘어도 번호 조회 때문에 쿼리가 늘지 않는다."""
        for index in range(3):
            self.write(self.first, f"댓글 {index}")

        self.client.force_authenticate(user=self.owner)

        with self.assertNumQueries(3):
            self.client.get(self.url)

        self.write(self.second, "댓글 추가")

        self.client.force_authenticate(user=self.owner)

        with self.assertNumQueries(3):
            self.client.get(self.url)
