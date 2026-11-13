"""
Tests for features/reports.feature (backend scenarios that live in the report module).

The invoice queries themselves live in the pip-installed reportcsu package and are not
tested here. These tests cover the report runner (report.views.report), which must use the
file name the query provides (Y-Note-SAS/openimis-be-report_py PR #2 and #3).

Run: python manage.py test report.test_features_reports --keepdb
"""
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from core.test_helpers import create_right_only_user, create_security_tree, get_test_token

REPORT_QUERY_RIGHT = 131200  # gql_query_report_perms

INVOICE_FILENAME = "Facture_CMA_DOUMAINTANG_2025-12-01_2026-02-04_2026-02-04T11-04-30"


def _fake_report_config(data):
    return {
        "name": "invoice_csu",
        "default_report": "{}",
        "python_query": lambda user, **kwargs: data,
        "permission": None,
    }


@mock.patch("report.views.generate_report", return_value=b"%PDF-fake")
@mock.patch("report.views.get_report_definition", return_value="{}")
class ReportFileNameFeatureTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tree = create_security_tree("FRPT")
        cls.user = create_right_only_user("frpt_rep", [REPORT_QUERY_RIGHT], [cls.tree.d1.id])

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {get_test_token(self.user)}")

    def tearDown(self):
        cache.clear()

    def _run(self, data):
        with mock.patch("report.views.ReportConfig.get_report",
                        return_value=_fake_report_config(data)):
            return self.client.get(f"/{settings.SITE_ROOT()}report/invoice_csu/pdf/")

    # Scenario: The report runner uses the file name provided by the report query (@redmine-34859)
    def test_report_uses_filename_from_query(self, _definition, _generate):
        response = self._run({"report_filename": INVOICE_FILENAME})
        self.assertEqual(200, response.status_code)
        self.assertIn(f'filename="{INVOICE_FILENAME}.pdf"', response["Content-Disposition"])

    # Scenario: Without a file name from the query, the report name is used (@redmine-34859)
    def test_report_falls_back_to_report_name(self, _definition, _generate):
        response = self._run({"some": "data"})
        self.assertEqual(200, response.status_code)
        self.assertIn('filename="invoice_csu.pdf"', response["Content-Disposition"])
