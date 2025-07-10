from uuid import uuid4

from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.test import SimpleTestCase

from woo_publications.contrib.tests.factories import ServiceFactory
from woo_publications.utils.tests.vcr import VCRMixin

from ..client import FilePart, PartsDownloader, get_client

MOCK_SERVICE = ServiceFactory.build(api_root="http://localhost/")


class PartsDownloaderTests(VCRMixin, SimpleTestCase):
    def test_empty_parts(self):
        downloader = PartsDownloader(parts=[], file_name="test.bin", total_size=438)

        with get_client(service=MOCK_SERVICE) as client:
            result = downloader.download(client=client, source_url="file/0")

        self.assertEqual(list(result), [])

    def test_return_in_memory_part_for_small_files(self):
        downloader = PartsDownloader(
            parts=[
                FilePart(
                    uuid=uuid4(),
                    order=1,
                    size=10,
                    completed=False,
                )
            ],
            file_name="test.bin",
            total_size=10,
            small_file_size_limit=100,
        )

        with get_client(service=MOCK_SERVICE) as client:
            result = downloader.download(client=client, source_url="file/10")

        parts_and_files = list(result)
        self.assertEqual(len(parts_and_files), 1)
        _, file = parts_and_files[0]
        self.assertIsInstance(file, InMemoryUploadedFile)

    def test_create_temp_files_for_large_downloads(self):
        downloader = PartsDownloader(
            parts=[
                FilePart(
                    uuid=uuid4(),
                    order=1,
                    size=20,
                    completed=False,
                ),
                FilePart(
                    uuid=uuid4(),
                    order=2,
                    size=5,
                    completed=False,
                ),
            ],
            file_name="test.bin",
            total_size=25,
            small_file_size_limit=10,
        )

        with get_client(service=MOCK_SERVICE) as client:
            result = downloader.download(client=client, source_url="file/25")

        parts_and_files = list(result)
        self.assertEqual(len(parts_and_files), 2)

        with self.subTest(part=1):
            file_1 = parts_and_files[0][1]

            self.assertIsInstance(file_1, TemporaryUploadedFile)
            self.assertEqual(file_1.size, 20)

        with self.subTest(part=2):
            file_2 = parts_and_files[1][1]

            self.assertIsInstance(file_2, TemporaryUploadedFile)
            self.assertEqual(file_2.size, 5)

    def test_dont_write_files_for_completed_parts(self):
        downloader = PartsDownloader(
            parts=[
                FilePart(
                    uuid=uuid4(),
                    order=1,
                    size=25,
                    completed=True,
                ),
                FilePart(
                    uuid=uuid4(),
                    order=2,
                    size=25,
                    completed=False,
                ),
            ],
            file_name="test.bin",
            total_size=50,
            small_file_size_limit=100,
        )

        with get_client(service=MOCK_SERVICE) as client:
            result = downloader.download(client=client, source_url="file/50")

        parts_and_files = list(result)
        self.assertEqual(len(parts_and_files), 2)

        self.assertEqual(parts_and_files[0][1].size, 0)
        self.assertEqual(parts_and_files[1][1].size, 25)

    def test_with_chunks_smaller_than_part_sizes(self):
        downloader = PartsDownloader(
            parts=[
                FilePart(
                    uuid=uuid4(),
                    order=1,
                    size=25,
                    completed=True,
                ),
                FilePart(
                    uuid=uuid4(),
                    order=2,
                    size=25,
                    completed=False,
                ),
            ],
            file_name="test.bin",
            total_size=50,
            small_file_size_limit=100,
            chunk_size=1,
        )

        with get_client(service=MOCK_SERVICE) as client:
            result = downloader.download(client=client, source_url="file/50")

        parts_and_files = list(result)
        self.assertEqual(len(parts_and_files), 2)

        self.assertEqual(parts_and_files[0][1].size, 0)
        self.assertEqual(parts_and_files[1][1].size, 25)
