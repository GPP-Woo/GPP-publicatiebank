from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.images import ImageFile
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext as _


def max_img_width_and_height_validator(image: ImageFile):
    max_width = settings.MAX_IMG_WIDTH
    max_height = settings.MAX_IMG_HEIGHT

    if (image.width > max_width) or (image.height > max_height):
        raise ValidationError(
            _(
                "The image dimensions exceed the maximum dimensions of "
                "{max_width}x{max_height}."
            ).format(max_width=max_width, max_height=max_height)
        )


def max_img_size_validator(image: ImageFile):
    max_img_size = settings.MAX_IMG_SIZE
    if image.size > max_img_size:
        raise ValidationError(
            _("File size exceeds max size of {max_img_size}.").format(
                max_img_size=filesizeformat(max_img_size)
            )
        )
