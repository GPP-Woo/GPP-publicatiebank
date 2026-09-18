from django.db import models


def start_end_date_constraint(start_date: str, end_date: str) -> models.CheckConstraint:
    return models.CheckConstraint(
        condition=models.Q(**{f"{end_date}__gte": models.F(start_date)}),
        name=f"{end_date}_cannot_be_before_{end_date}",
        violation_error_message="The start date ({start_date}) has to happen before "
        f"(or be the same as) end date ({end_date}).",
    )
