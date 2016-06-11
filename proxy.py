import asyncio
import aiohttp
import jinja2
import aiohttp_jinja2
from collections import namedtuple
from aiohttp import web
import crypto
import truth
import json
import os

LOG_OTHER_REQUESTS = bool(os.getenv("LOG_OTHER_REQUESTS"))
HOOKS = {}
def hook(ep):
    def decorator(f):
        HOOKS[ep] = f
        return f
    return decorator

def runhooks(endpoint, msg):
    return HOOKS.get("/" + endpoint, lambda x: 0)(msg)

logged_message_t = namedtuple("logged_message_t", ("endpoint", "headers", "body_json"))

CLIENT_MSG = []
SERVER_MSG = []
runloop = asyncio.get_event_loop()
thesession = aiohttp.ClientSession()

def jse(ind):
    return json.dumps(ind, indent=2, ensure_ascii=0, sort_keys=1)

async def proxy_do(request):
    actual_request_target = request.match_info["rurl"]
    to_url = "{0}://{1}/{2}".format(
        request.scheme, request.headers.get("Host"), actual_request_target
    )
    print("notice: request to", to_url)

    # Some normal HTTP content is on the API server too. Those should
    # be passed through untouched.
    is_crypted_request = "PARAM" in request.headers
    content = await request.content.read()

    payload_was_modified = 0
    async with thesession.post(to_url, headers=request.headers, data=content) as resp:
        bdy = await resp.content.read()

        if is_crypted_request:
            dat = crypto.unpack_from_network(bdy, request.headers.get("UDID"))
            payload_was_modified = runhooks(actual_request_target, dat)
            if payload_was_modified:
                # repack it
                bdy = crypto.pack_for_network(dat, request.headers.get("UDID"))

        mutable_h = dict(resp.headers)
        if "TRANSFER-ENCODING" in mutable_h:
            # Causes issues (because we don't send chunked data back to client),
            # so get rid of this header
            del mutable_h["TRANSFER-ENCODING"]

        our_response = web.Response(status=resp.status, headers=mutable_h, body=bdy)

    if is_crypted_request:
        CLIENT_MSG.append(logged_message_t(
            actual_request_target,
            jse(dict(request.headers)),
            jse(crypto.unpack_from_network(content, request.headers.get("UDID")))
        ))
        SERVER_MSG.append(logged_message_t(
            actual_request_target + (" (Modified)" if payload_was_modified else ""),
            jse(dict(resp.headers)),
            jse(crypto.unpack_from_network(our_response.body, request.headers.get("UDID")))))
    elif LOG_OTHER_REQUESTS:
        CLIENT_MSG.append(logged_message_t(
            actual_request_target,
            jse(dict(request.headers)),
            jse({"_": "Payload unavailable - not an API request."})
        ))
        SERVER_MSG.append(logged_message_t(
            actual_request_target,
            jse(dict(resp.headers)),
            jse({"_": "Payload unavailable - not an API request."})
        ))

    return our_response

proxy = web.Application(loop=runloop)
proxy.router.add_route("*", r"/{rurl:.*}", proxy_do)

@aiohttp_jinja2.template("results.html")
def result_index(request):
    """Pretty-print conversations between game and server."""
    convs = list(zip(CLIENT_MSG, SERVER_MSG))
    return {"conversations": convs}

result = web.Application(loop=runloop)
result.router.add_route("GET", r"/", result_index)
result.router.add_static("/static/", "./static")
aiohttp_jinja2.setup(result, loader=jinja2.FileSystemLoader('.'))

# Insert hooks here. Have fun and don't cheat!
# Hooks take and mutate a msg parameter. Return truthy if you modified the msg.
# Install hooks with @hook(endpoint).

@hook("/live/start_view")
def use_ssr_models(msg):
    ssrteam = truth.to_ssr_team(msg["data"]["live_unit_member"])
    # ssrteam = truth.ssrteam_for_charas(truth.valkyria)
    msg["data"]["live_unit_member"] = ssrteam
    return 1

def begin(host="0.0.0.0", port=80, sdt=60.0):
    """Start the servers. The proxy will listen on 'port', and
       the results service will listen on 'port + 1'."""
    prox_handler = proxy.make_handler()
    resu_handler = result.make_handler()
    loop = proxy.loop

    psrv = loop.run_until_complete(loop.create_server(prox_handler, host, port))
    rsrv = loop.run_until_complete(loop.create_server(resu_handler, host, port + 1))
    print("Proxy starts on port", port)
    print("Results start on port", port + 1)

    try:
        loop.run_forever()
    except KeyboardInterrupt:  # pragma: no branch
        pass
    finally:
        psrv.close()
        rsrv.close()
        loop.run_until_complete(psrv.wait_closed())
        loop.run_until_complete(proxy.shutdown())
        loop.run_until_complete(prox_handler.finish_connections(sdt))
        loop.run_until_complete(proxy.cleanup())

        loop.run_until_complete(rsrv.wait_closed())
        loop.run_until_complete(result.shutdown())
        loop.run_until_complete(resu_handler.finish_connections(sdt))
        loop.run_until_complete(result.cleanup())
        loop.close()

begin()
