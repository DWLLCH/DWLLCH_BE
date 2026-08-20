from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User, UserBlock


class UserBlockAPITest(APITestCase):
    """사용자 차단 등록/해제/목록 조회."""

    def setUp(self):
        self.user = self.create_user("blocker@example.com", "blocker")
        self.target = self.create_user("target@example.com", "target")
        self.another = self.create_user("another@example.com", "another")

        self.url = "/users/blocks"
        self.client.force_authenticate(user=self.user)

    def create_user(self, email, username):
        return User.objects.create_user(
            email=email,
            username=username,
            password="Test1234!",
        )

    def block(self, target_user_id):
        return self.client.post(
            self.url,
            {"targetUserId": target_user_id},
            format="json",
        )

    def test_block_user(self):
        response = self.block(self.target.id)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.data["data"]

        self.assertEqual(data["targetUserId"], self.target.id)
        self.assertEqual(data["targetUsername"], "target")
        self.assertTrue(
            UserBlock.objects.filter(
                user=self.user, target=self.target
            ).exists()
        )

    def test_cannot_block_self(self):
        response = self.block(self.user.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(UserBlock.objects.count(), 0)

    def test_cannot_block_twice(self):
        self.block(self.target.id)

        response = self.block(self.target.id)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(UserBlock.objects.count(), 1)

    def test_cannot_block_unknown_user(self):
        response = self.block(999999)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_block_requires_target_user_id(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unblock_user(self):
        self.block(self.target.id)

        response = self.client.delete(f"{self.url}/{self.target.id}")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UserBlock.objects.exists())

    def test_unblock_user_who_is_not_blocked(self):
        response = self.client.delete(f"{self.url}/{self.target.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_block_list_returns_only_my_blocks(self):
        self.block(self.target.id)

        UserBlock.objects.create(user=self.another, target=self.target)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.data["content"]

        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["targetUserId"], self.target.id)
        self.assertEqual(response.data["totalElements"], 1)

    def test_block_list_is_newest_first(self):
        self.block(self.target.id)
        self.block(self.another.id)

        content = self.client.get(self.url).data["content"]

        self.assertEqual(
            [item["targetUserId"] for item in content],
            [self.another.id, self.target.id],
        )

    def test_blocking_is_one_way(self):
        """내가 차단해도 상대의 차단 목록에는 남지 않는다."""
        self.block(self.target.id)

        self.client.force_authenticate(user=self.target)

        self.assertEqual(self.client.get(self.url).data["content"], [])

    def test_block_is_removed_when_target_account_is_deleted(self):
        self.block(self.target.id)

        self.target.delete()

        self.assertFalse(UserBlock.objects.exists())

    def test_endpoints_require_authentication(self):
        self.client.force_authenticate(user=None)

        self.assertEqual(
            self.client.get(self.url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.block(self.target.id).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.delete(f"{self.url}/{self.target.id}").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
