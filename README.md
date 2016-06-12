## Whale Simulator

A simple man-in-the-middle proxy. Requires Python 3.5 and aiohttp.
Don't use this software to cheat! Consider gitting gud instead.

As always, thanks to marcan for his ever-useful apiclient.

### Run it

Get a game DB and place it next to truth.py as `truth.mdb`. Later is better,
because there will be more SSRs to use.

```bash
$ virtualenv .env
$ source .env/bin/activate
$ pip install -r requirements.txt
$ sudo python3 proxy.py
```

And you're ready to go. For some reason it doesn't even require secret keys.

The proxy logs captured requests for later viewing at http://127.0.0.1:81 .
Red is a client message, green is a server response.

### Messing with responses

The proxy lets you modify responses in two ways: hooks and intercepts. The
main difference between the two is that hooked requests are still sent to
the server, while intercepted requests are generated directly by the proxy.
Intercepted/hooked requests will be marked with `(Intercepted)` and
`(Modified)` in the server log, respectively.

From a hook, you must modify the `msg` parameter *in-place*, then return
a true value for the proxy to send your modified payload back to the
client. You can return `msg`, but it's not required. Sample:

```python
@hook("/some/endpoint")
def modify(msg):
    msg["data"]["hello"] = "world"
    return 1
```

Intercepts will not work unless there was a successful prior request to the
server. This usually won't cause a problem unless you are intercepting
`/load/check` (normally the first request made by the client).

An intercept function gets the client request passed in. Sample:

```python
@intercept("/some/endpoint")
def genresponse(client_request):
    return {
        "hello": "world"
    }
```

**If you return None, the request will be sent to the server normally. Be
careful.**

From an intercept, you must return a payload dictionary that will be
crypted and sent back to the client. Don't wrap it with a `data` key, the
proxy will do this for you.

```python
Incorrect:                         |   Correct:
{                                  |   {
    "data": {                      |       "live_unit_member": [
        "live_unit_member": [      |           300217,
            300217,                |           200247,
            200247,                |           200197,
            200197,                |           200213,
            200213,                |           200107
            200107                 |       ]
        ]                          |   }
    }                              |
}                                  |
```

**There can only be one hook and intercept for a particular endpoint,
and a hook defined later will override any hooks before it. Additionally,
intercepts take precedence over hooks, no matter the order in which
they are defined.**

Outgoing requests cannot be hooked without keys.

### Pointing your device at the proxy

#### Method 1: Hosts file

This requires a rooted/jailbroken device. Just open up /etc/hosts and add the
line:

    <your computer's IP> game.starlight-stage.jp

Clear the device's DNS cache if needed and off you go.

#### Method 2: DNS proxy

The primary advantage of this over a host-file edit is that it doesn't need a
jailbroken device.

`dns-proxy` from npm is recommended. A sample configuration
file in included; take a look at `.dnsproxyrc`. Once the DNS server is running,
point your device's network settings to it.
