"""
Copied/vendored validators from vng_api_common.validators which can't be imported
on Python 3.12+.

TODO: replace again once vng_api_common is 3.12 compatible, until the time being we
don't bother with translating validation error messages.
"""

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

RSIN_LENGTH = 9

validate_digits = RegexValidator(
    regex="^[0-9]+$", message="Waarde moet numeriek zijn.", code="only-digits"
)


def validate_rsin(value):
    """
    Validates that a string value is a valid RSIN number by applying the
    '11-proef' checking.

    :param value: String object representing a presumably good RSIN number.
    """
    # Initial sanity checks.
    validate_digits(value)
    if len(value) != RSIN_LENGTH:
        raise ValidationError(
            f"RSIN moet {RSIN_LENGTH} tekens lang zijn.", code="invalid-length"
        )

    # 11-proef check.
    total = 0
    for multiplier, char in enumerate(reversed(value), start=1):
        if multiplier == 1:
            total += -multiplier * int(char)
        else:
            total += multiplier * int(char)

    if total % 11 != 0:
        raise ValidationError("Onjuist RSIN nummer.", code="invalid")
