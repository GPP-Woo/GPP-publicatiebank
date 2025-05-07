from textwrap import dedent

from drf_spectacular.utils import OpenApiParameter

AUDIT_USER_ID_PARAMETER = OpenApiParameter(
    name="Audit-User-ID",
    type=str,
    location=OpenApiParameter.HEADER,
    required=True,
    description=dedent(
        """
        The system identifier that uniquely identifies the user performing the action.
        Ideally, this is obtained from some Identity and Access Management
        infrastructure. With OpenID Connect, this would typically be the `sub` claim.
        """
    ),
)
AUDIT_USER_REPRESENTATION_PARAMETER = OpenApiParameter(
    name="Audit-User-Representation",
    type=str,
    location=OpenApiParameter.HEADER,
    required=True,
    description=dedent(
        """
        The display name of the user performing the action, to make them recognizable.
        """
    ),
)
AUDIT_REMARKS_PARAMETER = OpenApiParameter(
    name="Audit-Remarks",
    type=str,
    location=OpenApiParameter.HEADER,
    required=True,
    description=dedent(
        """
        Any additional information describing the action performed by the user.
        """
    ),
)

ALL_AUDIT_PARAMETERS = [
    AUDIT_USER_ID_PARAMETER,
    AUDIT_USER_REPRESENTATION_PARAMETER,
    AUDIT_REMARKS_PARAMETER,
]
