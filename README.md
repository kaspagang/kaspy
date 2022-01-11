# kaspy

Python implementation of a kaspa-grpc client

## work in progress...

## To Do 
~~Fix breaking issue~~

~~Clean up, lots of unused code left in place.~~

- Implement error handling and timeouts
- Implement Host and Client health checks
- Implement Streaming Callback handling of notification messages
- Implement P2P communication
- Documentation
- Add to pip
- Allow for commandline use
- ...
- Async Implementation
    
## Basic Documentaion:

### Sending a `request()` 

```python

# Import the kaspa client
from kaspy.client import kaspa_client
    
    #Initialize a client instance
    client = kaspa_client() 
    
    #Connect to a predefined host
    client.connect(host='<ip>', port='<port>') 
    
    #OR
    
    #Connect to a a publicaly broadcasted node from the dns_seed_servers.
    client.auto_connect() #note: it may take a while to find a responsive node
    
    #define the command you want to send
    command = 'getInfoRequest'
    
    #build the payload for the command
    payload = {} 
    
    #send the request to the server and retrive the response
    resp  = client.request(command=command, payload=payload)
````
for more references on commands and payloads see:

https://github.com/kaspanet/kaspad/blob/master/infrastructure/network/netadapter/server/grpcserver/protowire/rpc.md 

for conversions to KaspaMessage command names reference:

https://github.com/kaspagang/kaspy/blob/master/kaspy/protos/messages.proto
  
**Donations welcome @ kaspa:qzyjckdvgyxgwqj8zztw7qkqylsp864fyquzg8ykmmwkz58snu85zlk0mfy89**

## Authors

[@D-Stacks](https://github.com/D-Stacks)

## Requirements
- grpc
- google
