import tempfile
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.images import ImageFile
from django.test import TestCase, override_settings
from django.utils.translation import gettext_lazy as _

from PIL import Image

from ..models import Topic


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class TopicModelTest(TestCase):
    def test_image_file_upload_extension_allowed(self):
        image_file = ImageFile(BytesIO(), name="example.png")
        assert isinstance(image_file.file, BytesIO)
        Image.new("RGBA", (16, 16), (255, 0, 0, 255)).save(
            image_file.file, format="PNG"
        )

        topic = Topic()
        topic.afbeelding.save("example.png", image_file)
        topic.officiele_titel = "test"
        topic.full_clean()
        topic.save()

        topic.refresh_from_db()
        self.assertEqual(topic.afbeelding.name, "topics/example.png")

    def test_image_file_upload_extension_not_allowed(self):
        image_file = ImageFile(BytesIO(), name="example.txt")
        assert isinstance(image_file.file, BytesIO)
        Image.new("RGBA", (16, 16), (255, 0, 0, 255)).save(
            image_file.file, format="PNG"
        )

        validator_message = _(
            "File extension “%(extension)s” is not allowed. "
            "Allowed extensions are: %(allowed_extensions)s."
        ) % {
            "extension": "txt",
            "allowed_extensions": ", ".join(settings.ALLOWED_IMG_EXTENSIONS),
            "value": "example.txt",
        }

        topic = Topic()
        topic.afbeelding.save("example.txt", image_file)
        topic.officiele_titel = "test"

        with self.assertRaisesMessage(ValidationError, validator_message):
            topic.full_clean()
