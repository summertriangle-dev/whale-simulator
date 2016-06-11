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

Installing a response modifier is pretty easy. Have a look at `proxy.py`.

The sample hook replaces each card in your MV lineup with a SSR version of
the same idol, if available.

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
