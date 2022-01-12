import grpc
from threading import Event, Thread
from collections import defaultdict
from typing import Any, Callable, Iterator, Union
from queue import Empty, SimpleQueue

from google.protobuf import json_format
from logging import DEBUG, INFO, getLogger, basicConfig

from .network.node import UNKNOWEN, Node, node_acquirer
from .protos.messages_pb2 import KaspadMessage, _KASPADMESSAGE
from .protos.messages_pb2_grpc import P2PStub, RPCStub
from .defines import MAINNET, P2P_DEF_PORTS, P2P_SERVICE, RPC_DEF_PORTS, RPC_SERVICE, CONNECTED, CLOSED, DISCONNECTED
from .log_handler.log_messages import client as cli_lm
from .utils.version_comparer import version as ver
from .excepts.exceptions import CLientClosed, ClientDisconnected, InvalidCommand, RPCResponseException, RPCServiceUnavailable


basicConfig(level=INFO)
basicConfig(level=DEBUG)
LOG = getLogger('[KASPA_CLI]')


class _KaspaClient(object): None #just a class towards wich all clients can be tested
       
class BaseClient(_KaspaClient):
    
    def __init__(self) -> None:
        self._stub = Union[RPCStub, P2PStub]
        self._chan = grpc
        self.node = Node
        self._is_connected = lambda : True if self._chan else False
        self.server_status = str #hold server status from grpc.RpcErrors
        self.client_status = str #hold client status : CONNECTED, DISCONNECTED or CLOSED
        self.subscriptions = defaultdict(dict) #hold subscription streams
        
        #for threading
        self._activate_stream = Event()
        self._streamer = Thread(target=self._stream, daemon=True)
       
        #ques
        self._requests = SimpleQueue() # `_requests` holds all messages queued to be sent
        #self._recv = SimpleQueue() #holds all 
        self._responses = SimpleQueue() # responses pertain to reqeust messages
        self._subscitptions = defaultdict(SimpleQueue)
        self._timeout = None
    
    # display node infos through the client:
    
    @property
    def host_latency(self):
        return self.node.latency(5) #not sure what is a good default but we get stuck if we don't supply and port is closed
    
    @property 
    def host_subnetwork(self):
        return self.node.network
    
    @property
    def host_version(self):
        return self.node.version
    
    @property
    def host(self):
        return self.node.__str__()
    
    @property
    def host_port(self):
        return self.node.port
    
    @property
    def host_ip(self):
        return self.node.ip
    
    
    # connecting opperations
    
    def reconnect(self):
        self._activate_stream.set()

    def connect(self, host: str, port: Union[int, str], idle_timeout: Union[float, int, None] = None) -> None:
        self.set_idle_timeout(idle_timeout)
        self.node = Node(host, port)
        LOG.info(cli_lm.CONN_ESTABLISHING(self.node))
        self._chan = grpc.insecure_channel(f'{self.node}')
        self._stub = RPCStub(self._chan)
        self._streamer.start() if not self._streamer.is_alive() else None
        self._activate_stream.set()
        LOG.info(cli_lm.CONN_ESTABLISHED(self.node))
    
    def auto_connect(*args, **kwargs) -> NotImplementedError:
        '''**NotImplemented** 
        
        The procdure required to filter for nodes between RPC and P2P are too different to warrent `auto_connect` on the BaseClient.
        use `auto_connect` with `RPCClient`, `P2PClient`, or `DualClient` instead'''
        raise NotImplementedError 
    
    
    # disconnecting /closing opperations
    
    def disconnect(self) -> None:
        '''
        halts all requests until the server is finished responding, keeps the channel open but halts the spin thread. 
        reconnection is possible with reconnect
        '''
        self.client_status = DISCONNECTED
        self._activate_stream.clear()
        self._requests.put(DISCONNECTED) #finish getting all requests until DISCONENCT is injected into the request_iterator 
    
    def close(self) -> None:
        '''closes the connection abruptly and completely reconnection not possible unless calling connect'''
        self.client_status = CLOSED
        self._requests._queue.appendleft(CLOSED) #hacky: skip the queue with CLOSED
        self._chan.close()
    
    # Subscription operations 
    
    def subscribe(self, command : str,  callback: Callable[[dict], Any], payload: Union[dict, str, None] = None) -> None:
        '''
        sends a thread to execute the callback func whenever a response pertaining to the subscription is retrived
        note: if subcribed to a service responses are NOT routed through the recv() function.  
        '''
        raise NotImplementedError
    
    def unsubscribe(self) -> None:
        '''unsubscribes to a subscription'''
        raise NotImplementedError
    
    def _subreq_to_unsubres(self, command : str) -> None:
        '''
        get the unsubscribe command corrosponding to the subscribe command
        --> make server stop sending for the subscription.
        '''
        raise NotImplementedError
    
        
    def _subreq_to_subres(self, command : str):
        '''
        find the KaspadMessage name of the response corrosponding to the subscribe command
        --> needed in order to filter the responses and find messages corrosponding to the subscription request
        '''
        raise NotImplementedError
    
    # checks
    def _is_subscription_request(self, command):
        '''
        verify command is subscribeable i.e. we expect to server to push responses when the command is sent.
        --> for error handling
        '''
        raise NotImplementedError
    
    def _verify_connection(self, command : Union[str, None]) -> Union[bool, Exception]:
        if self.client_status == CONNECTED:
            return True
        elif self.client_status == DISCONNECTED:
            raise ClientDisconnected(self.node, command)
        elif self.client_status == CLOSED:
            raise CLientClosed(self.node, command)
    
    # timeouts
    
    def set_idle_timeout(self, timeout : float):
        '''
        set the amount of idle time allowed for the connection
        --> should be set before conection is established.
        '''
        self._timeout = timeout   
    
    # Serializations

    def _serialize_response_to_json(self, response : KaspadMessage) -> str:
        raise NotImplementedError

    def _serialize_request(self, command : str, payload : Union[dict, str]) -> KaspadMessage:
        if command == _KASPADMESSAGE.fields_by_name[command].name: # this is important so we don't execute arbitary python code in this function
            kaspa_msg = KaspadMessage()
            app_msg = eval(f'kaspa_msg.{command}') #should not use eval - but seems like the easiest way for now.
            if payload:
                if isinstance(payload, dict):
                    json_format.ParseDict(payload, app_msg)
                if isinstance(payload, str):
                    json_format.Parse(payload, app_msg)
            app_msg.SetInParent()
            return kaspa_msg
        else:
            raise InvalidCommand(self.node, command)
    
    def _serialize_response_to_dict(self, response: KaspadMessage) -> dict:
        return json_format.MessageToDict(response)
    
    # Spin thread opperations:
    
    def _stream(self) -> None:
        self._activate_stream.wait()
        try:
            for resp in self._stub.MessageStream(request_iterator = (req for req in self._requests_iterator()), timeout=self._timeout):
                self._response_router(resp)
        
        except grpc.RpcError as e: 
            
            # in our case a _MultiThreadedRendezvous raises itself, which requires further parsing
            # for details on this behaviour, see issue: https://github.com/grpc/grpc/issues/25334
            # for help parsing, see source code: https://github.com/grpc/grpc/blob/master/src/python/grpcio/grpc/_channel.py?functions.php#L652
            # explainations of the indivdual codes, see documentation = https://grpc.github.io/grpc/core/md_doc_statuscodes.html
            
            # Closing the channel should raise an RpcError:
            if self.server_status == CLOSED: # Catch this case
                pass # let thread return None and finish 
            
            else: # Else we handle errors:
                self._response_error_handler(str(e.code()).rsplit('.')[-1], e.details())                
                    
    def _requests_iterator(self) -> Iterator[Union[KaspadMessage, None]]:
        while True:
            req = self._requests.get()
            if req == DISCONNECTED:
                self._activate_stream.clear()
                self._streamer()
            yield self._serialize_request(req[0], req[1])
    
    def _response_router(self, resp : str) -> dict:
        #route responses to appropriate subscription, recv, or response que  
        resp = self._serialize_response_to_dict(resp)
        self._responses.put(resp)
    
    # standard interactions
    
    def send(self, command : str, payload : Union[dict, str, None] = None) -> None:
        self._verify_connection(command)
        LOG.info(cli_lm.MSG_SENDING(command, self.node))
        self._requests.put((command, payload))
    
    def recv(self, timeout: Union[float, int, None] = 2) -> Iterator[Union[dict, str]]:
        try:
            resp = self._responses.get(block = True, timeout=timeout)
            return resp
        except Empty:
            raise TimeoutError
        
    def request(self, command : str, payload: Union[dict, str, None] = None, timeout: Union[float, int, None] = None) -> Union[dict, str]:
        self.send(command, payload)
        resp = self.recv(timeout)
        LOG.info(cli_lm.MSG_RECIVED(
            next(iter(resp.keys())),
            command,
            self.node
                    ))
        return resp
        
    # some funcs to query for server info
    
    def kaspa_open_services(self):
        '''query default open ports for all subnetworks and services'''
        self._verify_connection() # this goes through sockets, so needs own _verify connection
        raise NotImplementedError
    
    def kaspad_check_port(self, timeout: Union[float, None]) -> Union[float, None]:
        '''checks port is open within timeout -> returns latency, or none if port is not reachable'''
        self._verify_connection('latency') #this goes through sockets, so needs own _verify connection
        return self.node.latency(timeout)
    
    # Error handling:

    def _response_error_handler(self, code : str, details : str):
        #for now raise until we have proper error handling. 
        if code == 'UNAVAILABLE': #only real exception I am catching during testing, I doubt there is anything we can do on the client side. 
            raise RPCServiceUnavailable(self.node, code, details)
        #will add error handling as issues arise - for now I will leave it as is. 
        raise RPCResponseException(self.node, code, details)
    
    def _requests_error_handler(self, command : str, payload : dict):
        #for now raise until we have proper error handling. 
        raise InvalidCommand(self.node, command) 
    
class RPCClient(BaseClient):
    def __init__(self) -> None:
        '''kaspa client for RPC services'''
        super().__init__()
    
    # some more funcs to query for RPC server info
    
    def kaspad_version(self, timeout) -> ver:
        '''Query the kaspad version the host is running''' 
        if self.node.version == UNKNOWEN:
            self.node.version = ver.parse_from_string(self.request('getInfoRequest', timeout=timeout)['getInfoResponse']['serverVersion'])
        return self.node.version
        
    def kaspad_network(self, timeout) -> str:
        '''Querx the kaspad network the host is running'''
        if self.node.network == UNKNOWEN:
            self.node.network = self.request('getCurrentNetworkRequest', timeout=timeout)['getCurrentNetworkResponse']['currentNetwork'].lower()
        return self.node.network

    def auto_connect(self, min_kaspad_version: Union[ver, str, None] = None, subnetwork: Union[str, None] = MAINNET,
                         timeout: Union[float, None] = 10, max_latency: Union[float, None] =  None):
        '''auto connect to a RPC node'''
        port = RPC_DEF_PORTS[subnetwork]
        for node in node_acquirer.yield_open_nodes(port = port):
            self.connect(node.ip, port)
            latency = self.kaspad_check_port(min(filter(bool, [timeout, max_latency]), default=None))
            if latency:
                if max_latency:
                    if latency > max_latency:
                        continue
            try:
                if subnetwork:
                    if self.kaspad_network(timeout) != subnetwork:
                        continue
                if min_kaspad_version:
                    if isinstance(min_kaspad_version, str): 
                        min_kaspad_version = ver.parse_from_string(min_kaspad_version)
                    if self.kaspad_version(timeout) <= min_kaspad_version:
                        print(self.kaspad_version(timeout),  min_kaspad_version)
                        continue
            except (RPCServiceUnavailable, TimeoutError) as e:
                LOG.debug(e)
                continue
            break
        
class P2PClient(BaseClient):
    '''
    still need to read up on p2p message docs if i were to find them, or read through the kaspad codebase
    --> VersionMessage seems promising for all infos needed to auto_connect.
    --> perform handshake 
    --> intiate a heartbeats to signal we are still alive  
    '''
    
    def __init__(self) -> None:
        '''kaspa client for P2P services'''
        super().__init__()
        #raise NotImplementedError
        
    # some more funcs to query for P2P server info
    
    def _handshake(self) -> str:
        #perform handshake according to https://github.com/kaspanet/docs/blob/main/Reference/API/P2P.md
        pass
    
    def _heartbeat(self, ping_msg):
        #play ping -> pong according to https://github.com/kaspanet/docs/blob/main/Reference/API/P2P.md
        pass
    
    def connect(self, host : str , port : int):
        super().connect(host, port)
        self._handshake()

    
    def auto_connect(self, min_protocol_version: Union[ver, str, None] = None, subnetwork: Union[str, None] = MAINNET,
            min_kaspad_version: Union[ver, str, None] = None, timeout: Union[float, None] = 5, 
            max_latency: Union[float, None] =  None):
        '''auto connect to a P2P node'''
        port = P2P_DEF_PORTS[subnetwork]
        for node in node_acquirer.yield_open_nodes(port = port):
            self.connect(node.ip, port)
            latency = self.kaspad_check_port(min(filter(bool, [timeout, max_latency]), default=None))
            if latency:
                if max_latency:
                    if latency > max_latency:
                        continue
            try:
                version_msg = self.recv(timeout)['version']
            
            except (RPCServiceUnavailable, TimeoutError) as e:
                LOG.debug(e)
                continue
            self.node.protocol = version_msg['protocolVersion']
            self.node.network =  version_msg['network'].split('-')[-1]
            self.node.version = ver.parse_from_string(version_msg['userAgent'].split('/')[-1])
            if min_protocol_version:
                if isinstance(min_protocol_version, str): 
                    min_protocol_version = ver.parse_from_string(min_protocol_version)
                if self.node.protocol < min_protocol_version:
                    continue
            if subnetwork:
                if subnetwork != self.node.network:
                    continue
            if min_kaspad_version:
                if isinstance(min_kaspad_version, str):
                    min_kaspad_version = ver.parse_from_string(self.node.version)
                if self.node.version < min_kaspad_version:
                    continue 
            break

class DualClient(_KaspaClient):
        
    '''Unsure if it will be ever implemented: idea is that it connects to both rpc and p2p ports, and perserves request -> response order'''
    
    def __init__(self) -> None:
        self.rpc_client = RPCClient
        self.p2p_client = P2PClient
        raise NotImplementedError
    
    @property
    def client_status(self):
        if self.rpc_client.client_status == self.p2p_client.client_status:
            return self.rpc_client.client_status
        else:
            raise Exception       
    
    def _request_to_service(self, request: str) -> str:
        if _KASPADMESSAGE.fields_by_name[request].number < 50:
            return P2P_SERVICE
        elif _KASPADMESSAGE.fields_by_name[request].number > 1000:
            return RPC_SERVICE
    
    def connect(self, host : str, rpc_port : Union[str, int], p2p_port: Union[str,int]) -> None:
        self.rpc_client.connect(host=host, port=int(rpc_port))
        self.p2p_client.connect(host=host, port=int(p2p_port))
    
    def disconnect(self):
        self.rpc_client.disconnect()
        self.p2p_client.disconnect()
    
    def close(self):
        self.rpc_client.close()
        self.p2p_client.close()
        
    def send():
        raise NotImplementedError
    
    def recv():
        raise NotImplementedError
    
    def auto_connect(self, min_kaspad_version: Union[ver, str, None] = None, min_protocol_version: Union[ver, str, None] = None,
                     subnetwork: Union[str, None] = None, timeout: Union[float, None] = None, 
                     max_latency: Union[float, None] =  None) -> None:
        raise NotImplementedError
    