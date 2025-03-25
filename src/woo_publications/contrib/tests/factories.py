import factory
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.test.factories import ServiceFactory as _ServiceFactory


class ServiceFactory(_ServiceFactory):
    class Params:  # pyright: ignore
        # See ``docker/open-zaak/README.md`` for the test credentials and available
        # data.
        for_documents_api_docker_compose = factory.Trait(
            label="Open Zaak (docker-compose)",
            api_root="http://openzaak.docker.internal:8001/documenten/api/v1/",
            api_type=APITypes.drc,
            auth_type=AuthTypes.zgw,
            client_id="woo-publications-dev",
            secret="insecure-yQL9Rzh4eHGVmYx5w3J2gu",
        )
        for_gpp_search_docker_compose = factory.Trait(
            label="GPP-zoeken (docker-compose)",
            api_root="http://localhost:8002/api/v1/",
            api_type=APITypes.orc,
            auth_type=AuthTypes.api_key,
            header_key="Authorization",
            header_value="Token insecure-RySD8u5xkb9PH6AJtaZV4Y",
        )
