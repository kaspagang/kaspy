# kaspy

Python implementation of a kaspa-grpc client.

## work in progress...

**Breaking changes will occur without prior notice!**

## Installaton:

```bash
pip install kaspy
```

## Basic Documentaion:

### Connecting to a RPC server with `connect()` or `auto_connect()`:

```python

# Import the kaspa client
from kaspy.kaspa_clients import RPCClient

#Initialize a client instance
client = RPCClient() 

#Connect to a predefined host
client.connect(host='<ip>', port='<port>') 

#OR

#Connect to a a publicaly broadcasted node from the dns_seed_servers.
client.auto_connect() #note: it may take a while to find a responsive nodes, timeout should be issued to not get stuck searching
```

### Sending a `request()`:

*continued...*
```python
#define the command you want to send
command = 'getInfoRequest'

#build the payload for the command
payload = {} #in our case we don't need to send additional information 

#send the request to the server and retrive the response
resp  = client.request(command=command, payload=payload)

print(resp) # print response
```

### Subscribing to a stream with `subscribe()`:

*continued...*
```python 

command = 'notifyVirtualSelectedParentChainChangedRequest'

payload = {}

def callback_func(notification : dict) # create a callback function to process the notifications
    print(notification)

#send the request to the server and retrive the response
resp  = client.subscribe(command=command, payload=payload, callback=callback_func)

import time
time.sleep(5) # do stuff

client.unsubscribe(command) #unsubscribe to the stream
```

### Disenganging the service with `close()` or `disconnect()`

*continued...*
```python

client.disconnect() # finishes sending all requests and responses in Que, halts all operations, but keeps the channel open.

client.close() # closes the channel completely

```

for more references on commands and payloads see:

https://github.com/kaspanet/kaspad/blob/master/infrastructure/network/netadapter/server/grpcserver/protowire/rpc.md 

for conversions to KaspaMessage command names reference:

https://github.com/kaspagang/kaspy/blob/master/kaspy/protos/messages.proto
## known issues:

- `GLIBC_2.33' not found` : https://github.com/kaspagang/kaspy/issues/4 **[Workaround]**

## To Do:
~~Fix breaking issue~~

~~Clean up, lots of unused code left in place.~~

~~Implement error handling and timeouts~~

~~Implement Streaming Callback handling of notification messages~~

~~add to pip~~

~~Implement auto-reconnect options to client~~

- Implement P2P communication 
- 2nd cleanup
- Documentation
- Allow for commandline use
- ...
- Async Implementation

## Requirements
- grpc
- google

## Contribute
feel free to open a pull request. 

## Authors 
[@D-Stacks](https://github.com/D-Stacks)

**Donations welcome @ kaspa:qzyjckdvgyxgwqj8zztw7qkqylsp864fyquzg8ykmmwkz58snu85zlk0mfy89**

