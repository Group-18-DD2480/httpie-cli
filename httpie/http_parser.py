import argparse
from time import monotonic
from typing import Callable, Iterable

import requests
# noinspection PyPackageRequirements
import urllib3

from httpie.client import (
    build_requests_session, 
    dump_request,
    ensure_path_as_is, 
    make_request_kwargs, make_send_kwargs, 
    make_send_kwargs_mergeable_from_env,
    max_headers,
    transform_headers
)
from . import __version__
from .cli.constants import HTTP_OPTIONS
from .context import Environment
from .encoding import UTF8
from .models import RequestsMessage
from .sessions import get_httpie_session
from .uploads import (
    compress_request,
)
from .utils import get_expired_cookies


urllib3.disable_warnings()

FORM_CONTENT_TYPE = f'application/x-www-form-urlencoded; charset={UTF8}'
JSON_CONTENT_TYPE = 'application/json'
JSON_ACCEPT = f'{JSON_CONTENT_TYPE}, */*;q=0.5'
DEFAULT_UA = f'HTTPie/{__version__}'

IGNORE_CONTENT_LENGTH_METHODS = frozenset([HTTP_OPTIONS])

def collect_messages(
    env: Environment,
    args: argparse.Namespace,
    request_body_read_callback: Callable[[bytes], None] = None,
) -> Iterable[RequestsMessage]:
    httpie_session = None
    httpie_session_headers = None
    if args.session or args.session_read_only:
        httpie_session = get_httpie_session(
            env=env,
            config_dir=env.config.directory,
            session_name=args.session or args.session_read_only,
            host=args.headers.get('Host'),
            url=args.url,
        )
        httpie_session_headers = httpie_session.headers

    request_kwargs = make_request_kwargs(
        env,
        args=args,
        base_headers=httpie_session_headers,
        request_body_read_callback=request_body_read_callback
    )
    send_kwargs = make_send_kwargs(args)
    send_kwargs_mergeable_from_env = make_send_kwargs_mergeable_from_env(args)
    requests_session = build_requests_session(
        ssl_version=args.ssl_version,
        ciphers=args.ciphers,
        verify=bool(send_kwargs_mergeable_from_env['verify'])
    )

    if httpie_session:
        httpie_session.update_headers(request_kwargs['headers'])
        requests_session.cookies = httpie_session.cookies
        if args.auth_plugin:
            # Save auth from CLI to HTTPie session.
            httpie_session.auth = {
                'type': args.auth_plugin.auth_type,
                'raw_auth': args.auth_plugin.raw_auth,
            }
        elif httpie_session.auth:
            # Apply auth from HTTPie session
            request_kwargs['auth'] = httpie_session.auth

    if args.debug:
        # TODO: reflect the split between request and send kwargs.
        dump_request(request_kwargs)

    request = requests.Request(**request_kwargs)
    prepared_request = requests_session.prepare_request(request)
    transform_headers(request, prepared_request)
    if args.path_as_is:
        prepared_request.url = ensure_path_as_is(
            orig_url=args.url,
            prepped_url=prepared_request.url,
        )
    if args.compress and prepared_request.body:
        compress_request(
            request=prepared_request,
            always=args.compress > 1,
        )
    response_count = 0
    expired_cookies = []
    while prepared_request:
        yield prepared_request
        if not args.offline:
            send_kwargs_merged = requests_session.merge_environment_settings(
                url=prepared_request.url,
                **send_kwargs_mergeable_from_env,
            )
            with max_headers(args.max_headers):
                response = requests_session.send(
                    request=prepared_request,
                    **send_kwargs_merged,
                    **send_kwargs,
                )
            response._httpie_headers_parsed_at = monotonic()
            expired_cookies += get_expired_cookies(
                response.headers.get('Set-Cookie', '')
            )

            response_count += 1
            if response.next:
                if args.max_redirects and response_count == args.max_redirects:
                    raise requests.TooManyRedirects
                if args.follow:
                    prepared_request = response.next
                    if args.all:
                        yield response
                    continue
            yield response
        break

    if httpie_session:
        if httpie_session.is_new() or not args.session_read_only:
            httpie_session.cookies = requests_session.cookies
            httpie_session.remove_cookies(expired_cookies)
            httpie_session.save()
