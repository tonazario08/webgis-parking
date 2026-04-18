from django.test import SimpleTestCase, override_settings

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
