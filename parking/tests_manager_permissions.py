from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .auth_utils import LIMITED_MANAGER_GROUP


class ManagerPermissionsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.full_manager = user_model.objects.create_user(
            username="full_manager_perm",
            password="testpass123",
            is_staff=True,
        )
        self.limited_manager = user_model.objects.create_user(
            username="limited_manager_perm",
            password="testpass123",
        )
        self.target_user = user_model.objects.create_user(
            username="target_user_perm",
            password="testpass123",
        )

        self.limited_group, _ = Group.objects.get_or_create(name=LIMITED_MANAGER_GROUP)
        self.other_group, _ = Group.objects.get_or_create(name="other_group")
        self.limited_manager.groups.add(self.limited_group)

    def test_permissions_page_requires_login(self):
        response = self.client.get(reverse("manager_permissions"))

        self.assertEqual(response.status_code, 302)

    def test_permissions_page_rejects_limited_manager(self):
        self.client.force_login(self.limited_manager)

        response = self.client.get(reverse("manager_permissions"))

        self.assertEqual(response.status_code, 302)

    def test_permissions_page_accessible_for_full_manager(self):
        self.client.force_login(self.full_manager)

        response = self.client.get(reverse("manager_permissions"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Phân quyền tài khoản")

    def test_permissions_update_rejects_invalid_group_input(self):
        self.client.force_login(self.full_manager)

        response = self.client.post(
            reverse("manager_permissions_update", kwargs={"user_id": self.target_user.id}),
            {"group_ids": ["abc"]},
            follow=True,
        )

        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.groups.filter(name=LIMITED_MANAGER_GROUP).exists())
        self.assertContains(response, "Nhóm quyền không hợp lệ")

    def test_permissions_update_rejects_unknown_group_id(self):
        self.client.force_login(self.full_manager)

        response = self.client.post(
            reverse("manager_permissions_update", kwargs={"user_id": self.target_user.id}),
            {"group_ids": [str(self.other_group.id)]},
            follow=True,
        )

        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.groups.filter(id=self.other_group.id).exists())
        self.assertContains(response, "Nhóm quyền không hợp lệ")

    def test_permissions_update_blocks_self_escalation(self):
        self.client.force_login(self.full_manager)

        response = self.client.post(
            reverse("manager_permissions_update", kwargs={"user_id": self.full_manager.id}),
            {"group_ids": [str(self.limited_group.id)]},
            follow=True,
        )

        self.full_manager.refresh_from_db()
        self.assertFalse(self.full_manager.groups.filter(name=LIMITED_MANAGER_GROUP).exists())
        self.assertContains(response, "Ban khong the tu cap nhat phan quyen cua chinh minh")

    def test_permissions_update_sets_allowed_group(self):
        self.client.force_login(self.full_manager)

        response = self.client.post(
            reverse("manager_permissions_update", kwargs={"user_id": self.target_user.id}),
            {"group_ids": [str(self.limited_group.id)]},
            follow=True,
        )

        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.groups.filter(name=LIMITED_MANAGER_GROUP).exists())
        self.assertContains(response, f"Da cap nhat phan quyen cho {self.target_user.username}")
