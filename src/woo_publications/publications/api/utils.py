from collections.abc import Iterator
from functools import lru_cache

from django.utils.translation import gettext_lazy as _

from django_fsm import FSMField, Transition


@lru_cache
def _get_fsm_help_text(fsm_field: FSMField) -> str:
    _transitions: Iterator[Transition] = fsm_field.get_all_transitions(fsm_field.model)
    transitions = "\n".join(
        f'* `"{transition.source}"` -> `"{transition.target}"`'
        for transition in _transitions
    )
    return _(
        "\n\nThe possible state transitions are: \n\n{transitions}.\n\n"
        "Note that some transitions may be limited by business logic."
    ).format(transitions=transitions)
