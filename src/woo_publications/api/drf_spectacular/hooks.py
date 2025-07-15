from django.conf import settings


def remove_excluded_api_paths(endpoints):
    processed_endpoints = []
    for path, path_regex, method, callback in endpoints:
        if path.startswith(settings.EXCLUDED_API_PATH_PREFIXES):
            continue

        processed_endpoints.append((path, path_regex, method, callback))

    return processed_endpoints
