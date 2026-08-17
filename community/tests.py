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