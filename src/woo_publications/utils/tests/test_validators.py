from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils.translation import gettext

from woo_publications.publications.tests.factories import TopicFactory

from ..validators import (
    image_extension_validator,
    max_file_size_validator,
    max_file_width_and_height_validator,
)


class ImageExtensionValidatorsTestCase(TestCase):
    def test_happy_flow(self):
        topic = TopicFactory.create()
        image_extension_validator(topic.afbeelding)

    @override_settings(ALLOWED_IMG_EXTENSIONS=["gif"])
    def test_assert_file_extension_not_in_allowed_image_extensions(self):
        topic = TopicFactory.create()
        with self.assertRaisesMessage(
            ValidationError,
            gettext("unsupported image extension."),
        ):
            image_extension_validator(topic.afbeelding)


class MaxFileSizeValidatorsTestCase(TestCase):
    def test_happy_flow(self):
        topic = TopicFactory.create()
        max_file_size_validator(topic.afbeelding)

    @override_settings(MAX_FILE_SIZE=10)
    def test_size_larger_then_max(self):
        topic = TopicFactory.create()
        with self.assertRaisesMessage(
            ValidationError,
            gettext("File size exceeds max size of {max_file_size}.").format(
                max_file_size=10
            ),
        ):
            max_file_size_validator(topic.afbeelding)


class MaxFileWidthAndHeightValidatorsTestCase(TestCase):
    def test_happy_flow(self):
        topic = TopicFactory.create()
        max_file_width_and_height_validator(topic.afbeelding)

    @override_settings(MAX_FILE_WIDTH=10)
    def test_width_larger_then_max(self):
        topic = TopicFactory.create()
        with self.assertRaisesMessage(
            ValidationError,
            gettext("File width limit of {max_width} exceeded.").format(max_width=10),
        ):
            max_file_width_and_height_validator(topic.afbeelding)

    @override_settings(MAX_FILE_HEIGHT=10)
    def test_height_larger_then_max(self):
        topic = TopicFactory.create()
        with self.assertRaisesMessage(
            ValidationError,
            gettext("File height limit of {max_height} exceeded.").format(
                max_height=10
            ),
        ):
            max_file_width_and_height_validator(topic.afbeelding)
