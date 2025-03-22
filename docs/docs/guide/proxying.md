# Proxying
Coming Soon

## Proxying with Autoproxy
With /plu/ral, you have two autoproxies, one global, and one per server.

Generally, you should use `/switch` for managing your global autoproxy, and `/autoproxy` for managing your server autoproxy, although you can use `/autoproxy` for both.

When /plu/ral tries to proxy a message, it will select the server autoproxy, if it exists, and the global autoproxy, if it doesn't, with one exception: if your server autoproxy member is in a group restricted to certain channels, and the message is not in one of those channels, /plu/ral will use the global autoproxy.

With this, you can have a roleplay character restricted to a roleplay channel, and still use your global autoproxy for general chatting.

Remember, if your autoproxy isn't working as expected, you can always use `/plu/ral debug` to see why.

### Modes
- Latch (default)
  - Using proxy tags will switch the current autoproxy member to that member
- Front:
  - Using proxy tags will send a message as that member, but NOT switch the current autoproxy member
- Locked:
  - Proxy tags are completely ignored, and the current autoproxy member is always used.

