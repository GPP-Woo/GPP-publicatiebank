from django.test import SimpleTestCase

from ..checks import check_docker_hostname_dns


class DockerHostNameCheckTests(SimpleTestCase):
    def test_hostname_resolves(self):
        # Must pass, otherwise CI is misconfigured.
        warnings = check_docker_hostname_dns(None)

        self.assertEqual(warnings, [])
