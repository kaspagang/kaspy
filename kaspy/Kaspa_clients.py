import grpc
import json
import time
from threading import Event, Lock, Thread
from collections import defaultdict
from typing import Iterable, Iterator, Union
from queue import SimpleQueue

from google.protobuf import json_format
from logging import INFO, getLogger, basicConfig

from .network.node import Node, node_acquirer
from .protos.messages_pb2 import KaspadMessage, _KASPADMESSAGE
from .protos.messages_pb2_grpc import P2PStub, RPCStub
from .defines import LATEST_KASPAD_VERSION, MAINNET, P2P_DEF_PORTS, P2P_SERVICE, RPC_DEF_PORTS, RPC_SERVICE
from .log_handler.log_messages import client as cli_lm
from .utils.version_comparer import version as ver
from .excepts.exceptions import CLientClosed, ClientDisconnected, InvalidCommand, RPCResponseException


basicConfig(level=INFO)
LOG = getLogger('[KASPA_CLI]')

CONNECTED = 'connected' #connection is open for send / recv
DISCONNECTED = 'disconnected' # disables send / recv, waits for queued send / recv data to pass, keeps spin thread waiting in background for possible reconnection
CLOSED = 'closed' # terminates the connection immediatly, does not wait for queued data, kills spin thread. does not expect a reconnection attempt. 

STATES = (CONNECTED,DISCONNECTED,CLOSED) 

TERMINATE = 'terminate'

class _KaspaClient(object): None #just a class towards wich all clients can be tested
       
class BaseClient(_KaspaClient):
    
    def __init__(self) -> None:
        self._stub = Union[RPCStub, P2PStub]
        self._chan = grpc
        self.node = Node
        self.service = str #the service the client is connected to either: RPC_SERVICE or P2P_SERVICE is valid
        self._is_connected = lambda : True if self._chan else False
        self.server_status = str #hold server status from grpc.RpcErrors
        self.client_status = str #hold client status : CONNECTED, DISCONNECTED or CLOSED
        self.subscriptions = defaultdict(dict) #hold subscription streams
        
        #for threading
        self._requests = SimpleQueue() # `_requests` holds all messages queued to be sent
        self._responses = SimpleQueue() # responses pertain to reqeust messages
        self._subscitptions = dict  #hold subsciptions -> key : subscription name, value -> Response Queue
        self._activate_stream = Event()
        self._streamer = Thread(target=self._stream, daemon=True)
    
    def disconnect(self) -> None:
        self.client_status = DISCONNECTED
        self._activate_stream.clear()
        self._requests.put(DISCONNECTED) #finish getting all requests until DISCONENCT is injected into the request_iterator 
    
    def close(self, ser) -> None:
        self.client_status = CLOSED
        self._requests._queue.appendleft(CLOSED) #hacky: skip the queue with CLOSED
        self._chan.close()
    
    def subscribe(self, command : str, payload: Union[dict, str, None] = None) -> None:
        raise NotImplementedError
    
    def unsubscribe(self) -> None:
        raise NotImplementedError
    
    def is_notification_response(self, serialized_resp : Union[dict, str]) -> bool: 
        raise NotImplementedError
    
    def _verify_connection(self, command : Union[str, None]) -> Union[bool, Exception]:
        if self.client_status == CONNECTED:
            return True
        elif self.client_status == DISCONNECTED:
            raise ClientDisconnected(self.node, command)
        elif self.client_status == CLOSED:
            raise CLientClosed(self.node, command)

    def _cancel(self) -> None:
        raise NotImplementedError

    def _serialize_response_to_json(self, response : KaspadMessage) -> str:
        raise NotImplementedError

    def _serialize_request(self, command : str, payload : Union[dict, str]) -> KaspadMessage:
        assert command == _KASPADMESSAGE.fields_by_name[command].name #this is important so we don't execute arbitary python code in this function
        kaspa_msg = KaspadMessage()
        app_msg = eval(f'kaspa_msg.{command}') #should not use eval - but seems like the easiest way for now.
        if payload:
            if isinstance(payload, dict):
                json_format.ParseDict(payload, app_msg)
            if isinstance(payload, str):
                json_format.Parse(payload, app_msg)
        app_msg.SetInParent()
        return kaspa_msg
    
    def _serialize_response_to_dict(self, response: KaspadMessage) -> dict:
        return json_format.MessageToDict(response)
    
    def _stream(self) -> None:
        self._activate_stream.wait()
        try:
            for resp in self._stub.MessageStream(req for req in self._requests_iterator()):
                self._responses.put(resp)              
        
        except grpc.RpcError as e: 
            
            # in our case a _MultiThreadedRendezvous raises itself, which requires further parsing
            # for details on this behaviour, see issue: https://github.com/grpc/grpc/issues/25334
            # for help parsing, see source code: https://github.com/grpc/grpc/blob/master/src/python/grpcio/grpc/_channel.py?functions.php#L652
            # explainations of the indivdual codes, see documentation = https://grpc.github.io/grpc/core/md_doc_statuscodes.html
            
            # Closing the channel should raise an RpcError:
            if self.server_status == CLOSED: # Catch this case
                pass # let thread return None and finish 
            
            # Else we handle errors:
            self._response_error_handler(e.code(), e.details())                
                    
    def _requests_iterator(self) -> Iterator[Union[KaspadMessage, None]]:
        while True:
            req = self._requests.get()
            if req == DISCONNECTED:
                self._requests.put(req)
            yield req
    
    def send(self, command : str, payload : Union[dict, str, None] = None, timeout: float = None) -> None:
        self._verify_connection(command)
        LOG.info(cli_lm.MSG_SENDING(command, self.node))
        self._requests.put(self._serialize_request(command, payload))
    
    def recv(self) -> Iterator[Union[dict, str]]:
        return self._serialize_response_to_dict(self._responses.get())
    
    def request(self, command : str, payload: Union[dict, str, None] = None, timeout: float = None) -> Union[dict, str]:
        self.send(command, payload, timeout)
        resp = self.recv()
        LOG.info(cli_lm.MSG_RECIVED(
            next(iter(resp.keys())),
            command,
            self.node
                    ))
        return resp
    
    def reconnect(self):
        self._activate_stream.set()

    def connect(self, host: str, port: Union[int, str]) -> None:
        self.node = Node(host, port)
        LOG.info(cli_lm.CONN_ESTABLISHING(self.node))
        self._chan = grpc.insecure_channel(f'{self.node}')
        self._stub = RPCStub(self._chan)
        self._streamer.start() if not self._streamer.is_alive() else None
        self._activate_stream.set()
        LOG.info(cli_lm.CONN_ESTABLISHED(self.node))
    
    def auto_connect(*args, **kwargs) -> NotImplementedError:
        '''**NotImplemented** 
        
        The parameters required to filter for nodes between RPC and P2P are too different to warrent `auto_connect` on the BaseClient.
        use `auto_connect` with `RPCClient`, `P2PClient`, or `DualClient` instead'''
        raise NotImplementedError 
        '''
        Connect to a node, broadcasted by the dns seed servers with the specified kwargs 
        '''

        
    # some funcs to query for server info
    
    def kaspa_open_services(self):
        '''query default open ports for all subnetworks and services'''
        self._verify_connection() # this goes through sockets, so needs own _verify connection
        raise NotImplementedError
    
    def kaspad_check_port(self, timeout: Union[float, None]) -> Union[float, None]:
        '''checks port is open within timeout -> returns latency, or none if port is not reachable'''
        self._verify_connection('latency') #this goes through sockets, so needs own _verify connection
        return self.node.port_open(timeout)
    
    # Error handling:

    def _response_error_handler(self, code : str, details : str):
        #for now raise until we have proper error handling. 
        raise RPCResponseException(self.node, code, details)
    
    def _requests_error_handler(self, command : str, payload : dict):
        #for now raise until we have proper error handling. 
        raise InvalidCommand(self.node, command)
        
    
class RPCClient(BaseClient):
    def __init__(self) -> None:
        '''kaspa client for RPC services'''
        super().__init__()
    
    # some more funcs to query for RPC server info
    
    def kaspad_version(self) -> ver:
        '''Query the kaspad version the host is running''' 
        return ver.parse_from_string(self.request('getInfoRequest')['getInfoResponse']['serverVersion'])
        
    def kaspad_network(self) -> str:
        '''Querx the kaspad network the host is running'''
        return self.request('getCurrentNetworkRequest')['getCurrentNetworkResponse']['currentNetwork'].lower()

    def auto_connect(self, min_kaspad_version: Union[ver, str, None] = None, subnetwork: Union[str, None] = MAINNET,
                         timeout: Union[float, None] = 10, max_latency: Union[float, None] =  None):
        '''auto connect to a RPC node'''
        port = RPC_DEF_PORTS[subnetwork]
        for node in node_acquirer.yield_open_nodes(port = port):
            self.connect(node.ip, port)
            latency = self.kaspad_check_port(timeout)
            if latency:
                if max_latency:
                    if latency > max_latency:
                        continue
            if subnetwork:
                if self.kaspad_network() != subnetwork:
                    continue
            if min_kaspad_version:
                if isinstance(min_kaspad_version, str): 
                    min_kaspad_version = ver.parse_from_string(min_kaspad_version)
                if self.kaspad_version() <= min_kaspad_version:
                    print(self.kaspad_version(),  min_kaspad_version)
                    continue
            break
        
class P2PClient(BaseClient):
    '''
    still need to read up on p2p message docs if i were to find them, or read through the kaspad codebase
    --> VersionMessage seems promising for all infos needed to auto_connect.
    '''
    
    def __init__(self) -> None:
        '''kaspa client for P2P services'''
        super().__init__(self)
        raise NotImplementedError
        
    # some more funcs to query for P2P server info
    
    def kaspad_protocol_version(self) -> ver:
        self._verify_connection() # this goes through sockets, so needs own _verify_connection
        raise NotImplementedError
    
    def auto_connect(self, min_protocol_version: Union[ver, str, None] = None, subnetwork: Union[str, None] = None,
                         timeout: Union[float, None] = None, max_latency: Union[float, None] =  None):
        '''auto connect to a P2P node'''
        port = P2P_DEF_PORTS[subnetwork]
        for node in node_acquirer.yield_open_nodes(port = port):
            self.connect(node, port)
            latency = self.kaspad_check_port(int(timeout))
            if latency:
                if latency > max_latency:
                    continue
            if min_protocol_version:
                if isinstance(min_protocol_version, str): 
                    min_protocol_version = ver.parse_from_string(min_protocol_version)
                if self.kaspad_protocol_version() < min_protocol_version:
                    continue
            break

class DualClient(_KaspaClient):
        
    '''connects to both rpc and p2p ports, perserves request -> response order'''
    
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