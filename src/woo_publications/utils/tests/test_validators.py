from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.images import ImageFile
from django.template.defaultfilters import filesizeformat
from django.test import SimpleTestCase, override_settings
from django.utils.translation import gettext as _

from PIL import Image

from ..validators import max_img_size_validator, max_img_width_and_height_validator


class MaxFileSizeValidatorsTests(SimpleTestCase):
    def test_happy_flow(self):
        image_file = ImageFile(BytesIO(), name="example.png")
        assert isinstance(image_file.file, BytesIO)
        Image.new("RGBA", (16, 16), (255, 0, 0, 255)).save(
            image_file.file, format="PNG"
        )

        max_img_size_validator(image_file)

    @override_settings(MAX_IMG_SIZE=10)
    def test_size_larger_then_max(self):
        image_file = ImageFile(BytesIO(), name="example.png")
        assert isinstance(image_file.file, BytesIO)
        Image.new("RGBA", (16, 16), (255, 0, 0, 255)).save(
            image_file.file, format="PNG"
        )

        expected_error = _("File size exceeds max size of {max_img_size}.").format(
            max_img_size=filesizeformat(10)
        )
        with self.assertRaises(ValidationError) as exc_cm:
            max_img_size_validator(image_file)
        self.assertEqual(exc_cm.exception.message, expected_error)


class MaxFileWidthAndHeightValidatorsTests(SimpleTestCase):
    def test_happy_flow(self):
        image_file = ImageFile(BytesIO(), name="example.png")
        assert isinstance(image_file.file, BytesIO)
        Image.new("RGBA", (16, 16), (255, 0, 0, 255)).save(
            image_file.file, format="PNG"
        )

        max_img_width_and_height_validator(image_file)

    @override_settings(MAX_IMG_WIDTH=10)
    def test_width_larger_then_max(self):
        image_file = ImageFile(BytesIO(), name="example.png")
        assert isinstance(image_file.file, BytesIO)
        Image.new("RGBA", (16, 16), (255, 0, 0, 255)).save(
            image_file.file, format="PNG"
        )

        expected_error = _(
            "The image dimensions exceed the maximum dimensions of "
            "{max_width}x{max_height}."
        ).format(max_width=10, max_height=600)
        with self.assertRaises(ValidationError) as exc_cm:
            max_img_width_and_height_validator(image_file)
        self.assertEqual(exc_cm.exception.message, expected_error)

    @override_settings(MAX_IMG_HEIGHT=10)
    def test_height_larger_then_max(self):
        image_file = ImageFile(BytesIO(), name="example.png")
        assert isinstance(image_file.file, BytesIO)
        Image.new("RGBA", (16, 16), (255, 0, 0, 255)).save(
            image_file.file, format="PNG"
        )

        expected_error = _(
            "The image dimensions exceed the maximum dimensions of "
            "{max_width}x{max_height}."
        ).format(max_width=600, max_height=10)
        with self.assertRaises(ValidationError) as exc_cm:
            max_img_width_and_height_validator(image_file)
        self.assertEqual(exc_cm.exception.message, expected_error)
