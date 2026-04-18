from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

urlpatterns = []
handler404 = "parking.views.custom_not_found"


@override_settings(
    DEBUG=False,
    ROOT_URLCONF="parking.tests_access_and_errors",
    ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
)
class NotFoundTemplateTests(SimpleTestCase):
    def test_public_not_found_uses_public_template(self):
        response = self.client.get("/duong-dan-khong-ton-tai/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")

    def test_manager_not_found_uses_manager_template(self):
        response = self.client.get("/manager/khong-ton-tai/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "parking/manager/404.html")

    @override_settings(FORCE_SCRIPT_NAME="/webgis")
    def test_manager_not_found_uses_manager_template_under_script_prefix(self):
        response = self.client.get("/manager/khong-ton-tai/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "parking/manager/404.html")

    def test_manager_like_prefix_uses_public_template(self):
        response = self.client.get("/managerx/khong-ton-tai/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")


class RevenueAccessTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.full_manager = user_model.objects.create_user(
            username="full_manager",
            password="testpass123",
            is_staff=True,
        )

    def test_public_revenue_route_not_available(self):
        response = self.client.get("/revenue/")

        self.assertIn(response.status_code, (404, 410))

    def test_manager_revenue_requires_login(self):
        response = self.client.get("/manager/revenue/")

        self.assertIn(response.status_code, (302, 403))

    def test_manager_revenue_accessible_for_full_manager(self):
        self.client.force_login(self.full_manager)

        response = self.client.get("/manager/revenue/")

        self.assertEqual(response.status_code, 200)

    def test_api_revenue_not_public(self):
        response = self.client.get("/api/revenue/")

        self.assertIn(response.status_code, (404, 403))
