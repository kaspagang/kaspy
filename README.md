# kaspy

Python implementation of a kaspa-grpc client

## WORK IN PROGRESS...

**only for experimental use - until stable**

## Authors

[@D-Stacks](https://github.com/D-Stacks)

## Requirements
    grpc
    google

### Breaking Issues

`ResponseAsNoneType` --> custom exception

As far as I can debug it is caused by running `response = next(iter(MessageStream(iter([request,]))), None)` 
thus, not reciving a response by calling `next` on the response_iterator results in `None`, the underlying Exception
is actually a `StopIteration()`. The irksome thing about this is that:
1) One message may cause a response to go through, but the next one may fail. This causes unreliable communication to servers and makes it impossible to establish a reliable connection.
2) some messages seem to ge through near always, for example `addPeerRequest` was very stable during some tests, others are more prone to this error

Some things I tried:
passing `timeout` or `wait_for_ready` i.e. `response = next(iter(MessageStream(iter([request,], timeout=10, wait_for_ready=True))), None)` does not solve the problem

## Issues
    - version checking not working properly

## To Do 
    - Fix breaking issue
    - Clean up, lots of unused code left in place. 
    - Implement error handling
    - Documentation
    - Allow for commandline use
  

## Basic Documentaion:

### `kaspa_client()`

returns a new kaspa client instance


`.connect()`

establishes a connection to a node

    args:
        address : str
            host_address in format: `'<ip>:<port>'`

`.auto_connect()`

connects to a random node on the kaspa network
    args : None

`.request()`

send command + payload, retrive response in json format
    
    args:
        command : str
            The message to send to the kaspa RPC node
        payload : Union[dict, str] 
            payload of the message (can be either be a python dict or json message)

    returns: 
        A json response object corrosponding to the command
