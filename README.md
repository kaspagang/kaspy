# kaspy

Python implementation of a kaspa-grpc client

## WORK IN PROGRESS...

**only for experimental use - Not stable**

please see: https://github.com/kaspagang/kaspy/issues/1 if you want to make it useable!

## Authors

[@D-Stacks](https://github.com/D-Stacks)

## Requirements
- grpc
- google
    
## Basic Documentaion:

```python

# Import the kaspa client
from kaspy.client import kaspa_client
    
    #Initialize a client instance
    client = kaspa_client() 
    
    #Connect to a predefined host
    client.connect(host='<ip>', port='<>') 
    
    #OR
    
    #Connect to a a publicaly broadcasted node from the dns_seed_servers.
    client.auto_connect() #note: it may take a while to find a responsive node
    
    #define the command you want to send
    command = 'getInfoRequest'
    
    #build the payload for the command
    payload = {} 
    
    #send the request to the server and retrive the response
    resp  = client.request(command=command, payload=payload)
    ```
  
for more references on commands and payloads see:
https://github.com/kaspanet/kaspad/blob/master/infrastructure/network/netadapter/server/grpcserver/protowire/rpc.md 
for conversions to KaspaMessage command names reference:
https://github.com/kaspagang/kaspy/blob/master/kaspy/protos/messages.proto
    

some settings you can apply for `auto_connect`

```python 
from kaspy.defines import TESTNET, DEVNET, MAINNET, SIMNET
form kaspy.settings import sub_networks, kaspa_version

sub_networks = [MAINNET, DEVNET] #subnetworks to connect to
kaspa_version = 'v0.11.7' #min kaspa version to connect to
```

## Issues:

### Breaking Issues:

- https://github.com/kaspagang/kaspy/issues/1

### Minor Issues:

- Version checking not working properly
- Deal with `KaspaNetwork` when it is not in use (i.e. shut it down)
    
## To Do 
    - Fix breaking issue
    - Fix issues
    - Clean up, lots of unused code left in place. 
    - Implement error handling
    - Documentation
    - Allow for commandline use
  

