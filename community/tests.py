from django.test import TestCase

# Create your tests here.
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Post, Comment, PostLike, CommentLike


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