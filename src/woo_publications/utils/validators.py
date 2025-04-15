from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.fields.files import ImageFieldFile
from django.utils.translation import gettext_lazy as _


def max_file_width_and_height_validator(image: ImageFieldFile):
    max_height = settings.MAX_FILE_HEIGHT
    max_width = settings.MAX_FILE_WIDTH
    height = image.height
    width = image.width

    if width > max_width:
        raise ValidationError(
            _("File width limit of {max_width} exceeded.".format(max_width=max_width))
        )

    if height > max_height:
        raise ValidationError(
            _(
                "File height limit of {max_height} exceeded.".format(
                    max_height=max_height
                )
            )
        )


def max_file_size_validator(image: ImageFieldFile):
    max_file_size = settings.MAX_FILE_SIZE
    if image.size > max_file_size:
        raise ValidationError(
            _("File size exceeds max size of {max_file_size}.").format(
                max_file_size=max_file_size
            )
        )


def image_extension_validator(image: ImageFieldFile):
    assert image.name
    extension = image.name.split(".")[-1]
    if extension not in settings.ALLOWED_IMG_EXTENSIONS:
        raise ValidationError(_("unsupported image extension."))
