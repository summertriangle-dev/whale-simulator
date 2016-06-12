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
import time

LOG_OTHER_REQUESTS = bool(os.getenv("LOG_OTHER_REQUESTS"))
HOOKS = {}
INTERCEPTS = {}
def hook(ep):
    def decorator(f):
        HOOKS[ep] = f
        return f
    return decorator

def intercept(ep):
    def decorator(f):
        INTERCEPTS[ep] = f
        return f
    return decorator

def runhooks(endpoint, msg):
    return HOOKS.get("/" + endpoint, lambda x: 0)(msg)

def runintercept(endpoint, req):
    return INTERCEPTS.get("/" + endpoint, lambda x: None)(req)

logged_message_t = namedtuple("logged_message_t", ("endpoint", "headers", "body_json"))

CLIENT_MSG = []
SERVER_MSG = []
runloop = asyncio.get_event_loop()
thesession = aiohttp.ClientSession()

def jse(ind):
    return json.dumps(ind, indent=2, ensure_ascii=0, sort_keys=1)

class ProxyState(object):
    def __init__(self):
        self.replays = {}

    def record_sid(self, server):
        if server["data_headers"]["result_code"] != 1:
            print("Not updating SID because result code isn't 1.")
            return

        prev = self.replays.get(server["data_headers"]["user_id"])
        self.replays[server["data_headers"]["user_id"]] = server["data_headers"]
        print("SID updated:", prev, server["data_headers"])

    async def proxy_do(self, request):
        actual_request_target = request.match_info["rurl"]
        to_url = "{0}://{1}/{2}".format(
            request.scheme, request.headers.get("Host"), actual_request_target
        )
        print("notice: request to", to_url)

        # Some normal HTTP content is on the API server too. Those should
        # be passed through untouched.
        is_crypted_request = "PARAM" in request.headers
        content = await request.content.read()

        if is_crypted_request:
            req = crypto.unpack_from_network(content, request.headers.get("UDID"))
            result = runintercept(actual_request_target, req)
            if result is not None:
                wrap = {"data": result}
                wrap["data_headers"] = self.replays[int(crypto.clean_udid(request.headers.get("USER_ID")))]
                bdy = crypto.pack_for_network(wrap, request.headers.get("UDID"))
                our_response = web.Response(status=200, headers={
                    "Content-Type": "application/x-msgpack",
                    "Connection": "close",
                }, body=bdy)

                CLIENT_MSG.append(logged_message_t(
                    actual_request_target,
                    jse(dict(request.headers)),
                    jse(req)
                ))
                SERVER_MSG.append(logged_message_t(
                    actual_request_target + " (Intercepted)",
                    jse(dict(our_response.headers)),
                    jse(wrap)
                ))

                return our_response

        payload_was_modified = 0
        async with thesession.post(to_url, headers=request.headers, data=content) as resp:
            bdy = await resp.content.read()

            if is_crypted_request:
                dat = crypto.unpack_from_network(bdy, request.headers.get("UDID"))
                self.record_sid(dat)

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

state = ProxyState()
proxy = web.Application(loop=runloop)
proxy.router.add_route("*", r"/{rurl:.*}", state.proxy_do)

@aiohttp_jinja2.template("results.html")
def result_index(request):
    """Pretty-print conversations between game and server."""
    convs = list(zip(CLIENT_MSG, SERVER_MSG))
    return {"conversations": convs}

@aiohttp_jinja2.template("configlanding.html")
def result_mvconfig(request):
    return {"chars": truth.get_chars(),
            "cards": truth.get_cards(),
            "current": THE_TEAM}

# default team is 5 Natsukis ;)
THE_TEAM = truth.natsuki5
def result_mvconfig_commit(request):
    THE_TEAM[:] = list(map(int, request.query_string.split("=", 1)[-1].split("%2C")))
    print("Set team:", THE_TEAM)
    return web.Response(status=302, headers={"Location": "/config"}, body=b"OK")

result = web.Application(loop=runloop)
result.router.add_route("GET", r"/", result_index)
result.router.add_route("GET", r"/config", result_mvconfig)
result.router.add_route("GET", r"/config_commit", result_mvconfig_commit)
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


@intercept("/live/start_view")
def skip_mv(request):
    return {"live_unit_member": truth.ssrteam_for_charas(THE_TEAM)}

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
