from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from woo_publications.api.tests.mixins import TokenAuthMixin
from woo_publications.logging.models import TimelineLogProxy

from .factories import InformationCategoryFactory, OrganisationFactory, ThemeFactory

AUDIT_HEADERS = {
    "AUDIT_USER_REPRESENTATION": "username",
    "AUDIT_USER_ID": "id",
    "AUDIT_REMARKS": "remark",
}


class InformationCategoryLoggingTests(TokenAuthMixin, APITestCase):
    def test_retrieve_logging(self):
        information_category = InformationCategoryFactory.create()
        detail_url = reverse(
            "api:informationcategory-detail",
            kwargs={"uuid": str(information_category.uuid)},
        )

        response = self.client.get(detail_url, headers=AUDIT_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        log_records = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
            information_category
        )
        self.assertEqual(log_records.count(), 1)


class OrganisationLoggingTests(TokenAuthMixin, APITestCase):
    def test_retrieve_logging(self):
        organisation = OrganisationFactory.create()
        detail_url = reverse(
            "api:organisation-detail",
            kwargs={"uuid": str(organisation.uuid)},
        )

        response = self.client.get(detail_url, headers=AUDIT_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        log_records = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
            organisation
        )
        self.assertEqual(log_records.count(), 1)


class ThemeLoggingTests(TokenAuthMixin, APITestCase):
    def test_retrieve_logging(self):
        theme = ThemeFactory.create()
        detail_url = reverse(
            "api:theme-detail",
            kwargs={"uuid": str(theme.uuid)},
        )

        response = self.client.get(detail_url, headers=AUDIT_HEADERS)

        assert response.status_code == status.HTTP_200_OK
        log_records = TimelineLogProxy.objects.for_object(  # pyright: ignore[reportAttributeAccessIssue]
            theme
        )
        self.assertEqual(log_records.count(), 1)
