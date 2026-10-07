import inspect
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType
from typing import override

import requests.exceptions
from maykin_common.vcr import VCRMixin as _VCRMixin, _VCRTestCase
from vcr.cassette import Cassette


class _CassetteLoadedContextManager(AbstractContextManager):
    """
    A wrapper around a VCR cassette context manager which only activates the
    ``before_record_request`` hook once the cassette has been loaded.
    """

    def __init__(self, underlying: AbstractContextManager, state: dict[str, bool]):
        self._underlying = underlying
        self._state = state

    def __enter__(self) -> Cassette:
        cassette = self._underlying.__enter__()
        self._state["cassette_loaded"] = True
        return cassette

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return self._underlying.__exit__(exc_type, exc_value, traceback)


class VCRMixin(_VCRMixin):
    @override
    def _get_cassette_library_dir(self):
        class_name = self.__class__.__qualname__
        path = Path(inspect.getfile(self.__class__))
        return str(path.parent / "vcr_cassettes" / path.stem / class_name)

    @override
    def vcr_raises(
        self: "_VCRTestCase",
        exception: Callable[[], Exception] = requests.exceptions.RequestException,
    ) -> AbstractContextManager[Cassette]:
        """
        A context manager to use instead of ``self.use_cassette()`` to have the VCR
        instance raise the specified exception for requests made while the cassette
        is active.

        The ``before_record_request`` hook is also called for all the
        already-recorded interactions when the cassette is loaded, so the exception
        is only raised once the cassette has been fully loaded.
        """
        # TODO: Move this fix upstream
        kwargs = self._get_vcr_kwargs()
        hook = kwargs.get("before_record_request") or (lambda _: None)
        state: dict[str, bool] = {"cassette_loaded": False}

        def raise_exception(request):
            hook(request)
            if state["cassette_loaded"]:
                raise exception()

        clean_vcr = self._get_vcr(**kwargs | {"before_record_request": raise_exception})
        underlying = clean_vcr.use_cassette(self._get_cassette_name())
        assert isinstance(underlying, AbstractContextManager)
        return _CassetteLoadedContextManager(underlying, state)
