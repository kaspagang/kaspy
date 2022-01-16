import base64
import grpc
import time
from collections import defaultdict
from typing import Any, Callable, Dict, Iterator, Union
from requests import get
import base64
import uuid
from logging import DEBUG, INFO, getLogger, basicConfig

from kaspy.streams import P2PRequestStream, RequestStream, SubcribeStream
from kaspy.network.node import UNKNOWEN, Node, node_acquirer
from kaspy.protos.messages_pb2 import KaspadMessage, _KASPADMESSAGE
from kaspy.protos.messages_pb2_grpc import P2PStub, RPCStub
from kaspy.defines import MAINNET, P2P_DEF_PORTS, P2P_SERVICE, RPC_DEF_PORTS, RPC_SERVICE, CONNECTED, CLOSED, DISCONNECTED, USER_AGENT
from kaspy.log_handler.log_messages import client as cli_lm
from kaspy.utils.version_comparer import version as ver
from kaspy.excepts.exceptions import CLientClosed, ClientDisconnected, CommandIsNotSubcribable, InvalidCommand, RPCResponseException, RPCServiceUnavailable, SubscriptionCannotBeUnsubscribed


#basicConfig(level=INFO)
#basicConfig(level=DEBUG)
LOG = getLogger('[KASPA_CLI]')


class _KaspaClient(object): None #just a class towards wich all clients can be tested

       
class BaseClient(_KaspaClient):
    
    def __init__(self) -> None:
        self.node = Node
        self.service = None
        self._is_connected = lambda : True if self._chan else False
        self.server_status = str #hold server status from grpc.RpcErrors
        self.client_status = str #hold client status : CONNECTED, DISCONNECTED or CLOSED
        self._subscriptions = defaultdict(dict) #hold subscription streams
        self.request_stream = RequestStream
        self.restablish_new_connection  = None
        self._retry_count = None
        self._retry_wait = None
        self._auto_conn_params = None
        self.service
    
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

    def connect(self, host: str, port: Union[int, str], idle_timeout: Union[float, int, None] = None, 
                retry_count: float = None, retry_wait:float = None) -> None:
        self._retry_count = retry_count if retry_count else 0
        self._retry_wait = retry_wait if retry_wait else 0
        self.node = Node(host, port)
        LOG.info(cli_lm.CONN_ESTABLISHING(self.node))
        self.request_stream = RequestStream(node=self.node, stub=self._get_service_stub(), idle_timeout=idle_timeout)
        self.request_stream.start()
        LOG.info(cli_lm.CONN_ESTABLISHED(self.node))
    
    def auto_connect(*args, **kwargs) -> NotImplementedError:
        '''**NotImplemented** 
        
        The procdure required to filter for nodes between RPC and P2P are too different to warrent `auto_connect` on the BaseClient.
        use `auto_connect` with `RPCClient`, `P2PClient`, or `DualClient` instead'''
        raise NotImplementedError 
    
    
    # disconnecting /closing opperations
    
    def disconnect(self) -> None:
        for sub in self._subscriptions.values():
            sub.disconnect()
        self.client_status = DISCONNECTED
        self.request_stream.disconnect()
    
    def close(self) -> None:
        self.close_all_streams()
        self.request_stream.close()
    
    # Subscription operations 
    def _is_subscription(self, command: str):
        if command.startswith('notify'): 
            return True
        else: 
            return False
    
    def _sub_req_to_sub_message(self, command: str):
        sub_msg =  command.replace('Request', 'Notification')[6:]
        return sub_msg[0].lower() + sub_msg[1:]
    
    def subscribe(self, command: str,  callback: Callable[[dict], Any], payload: Union[dict, str, None] = None, idle_timeout: Union[float, None] = None) -> None:
        #if self._is_subscription_request(command):
        self._subscriptions[command] = SubcribeStream(self.node, command, payload, callback, 
                                                          self._get_service_stub(), idle_timeout=idle_timeout)
        self._subscriptions[command].start()
        #else:
            #raise CommandIsNotSubcribable(self.node, command)
    
    def unsubscribe(self, command: str) -> None:
        self._subscriptions[command].close()
        del self._subscriptions[command]
    
    def close_all_streams(self):
        for sub in self._subscriptions.values():
            sub.close()
        self._subscriptions = defaultdict(dict)
    
    # checks
    def _is_subscription_request(self, command: str):
        return command.startswith('notify')
    
    def _verify_connection(self, command : Union[str, None]) -> Union[bool, Exception]:
        if self.client_status == CONNECTED:
            return True
        elif self.client_status == DISCONNECTED:
            raise ClientDisconnected(self.node, command)
        elif self.client_status == CLOSED:
            raise CLientClosed(self.node, command)
        
    # Serializations

    def _serialize_response_to_json(self, response : KaspadMessage) -> str:
        raise NotImplementedError
    
    # helpers
    
    def _get_message_name(self, serialized_msg : dict):
        return next(iter(serialized_msg.keys()))
    
    def _get_service_stub(self):
        return RPCStub if self.service == RPC_SERVICE else P2PStub
    
    # standard interactions
    
    def send(self, command : str, payload : Union[dict, str, None] = None) -> None:
        self._verify_connection(command)
        LOG.info(cli_lm.MSG_SENDING(command, self.node))
        self.request_stream.put((command, payload))
    
    def recv(self, timeout: Union[float, int, None] = 2) -> Iterator[Union[dict, str]]:
        try:
            return self.request_stream.get(timeout)
        except grpc.RpcError as e:
            self._response_error_handler(str(e.code()), e.details())
        except TimeoutError as te:
            self._retry_connection(te)
            
    
    def request(self, command : str, payload: Union[dict, str, None] = None, timeout: Union[float, int, None] = None) -> Union[dict, str]:
        self.send(command, payload)
        resp = self.recv(timeout)
        LOG.info(cli_lm.MSG_RECIVED(
            self._get_message_name(resp),
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
    def _retry_connection(self, err, counter = 0):
        if counter == self._retry_count:
            if self.restablish_new_connection:
                self.auto_connect(*self._auto_conn_params) #save input from last auto_connect call
            raise err
        time.sleep(self._retry_wait)
        self.connect(self.node.ip, self.node.port)
        try:
            self.request('getInfoRequest') # test the connection
        except Exception as e:
            LOG.debug(e)
            self._retry_connection(err, counter=counter+1)

    def _response_error_handler(self, code : str, details : str):
        #for now raise until we have proper error handling. 
        if code == 'UNAVAILABLE': #only real exception I am catching during testing, I doubt there is anything we can do on the client side. 
            err = RPCServiceUnavailable(self.node, code, details)
            if self._retry_count:
                LOG.debug(err)
                self._retry_connection(err)
            else:
                raise err
        #will add error handling as issues arise - for now I will leave it as is.
        else:
            err = RPCResponseException(self.node, code, details)
            if self._retry_count:
                LOG.debug(err)
                self._retry_connection(err)
            raise err
    
    def _requests_error_handler(self, command : str, payload : dict):
        #for now raise until we have proper error handling. 
        raise InvalidCommand(self.node, command) 
    
class RPCClient(BaseClient):
    def __init__(self) -> None:
        '''kaspa client for RPC services'''
        super().__init__()
        self.service = RPC_SERVICE
        self.request_stream = P2PRequestStream
    
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
                    conn_timeout: Union[float, None] = 10, idel_timeout: float = None, max_latency: Union[float, None] =  None, 
                    retry_count = None, retry_wait = None, new_conn_on_err: bool = False) -> None:
        '''auto connect to a RPC node'''
        if new_conn_on_err:
            self._auto_conn_params = tuple(locals().values(),)[1:] # for possible later use in self._retry_connection
            print(self._auto_conn_params)
        port = RPC_DEF_PORTS[subnetwork]
        self.restablish_new_connection = new_conn_on_err
        for node in node_acquirer.yield_open_nodes(port = port):
            self.connect(node.ip, port, idel_timeout, retry_count, retry_wait)
            latency = self.kaspad_check_port(min(filter(bool, [conn_timeout, max_latency]), default=None))
            if not latency:
                self.close()
                continue
            if latency:
                if max_latency:
                    if latency > max_latency:
                        self.close()
                        continue
            try:
                if subnetwork:
                    if self.kaspad_network(conn_timeout) != subnetwork:
                        self.close()
                        continue
                if min_kaspad_version:
                    if isinstance(min_kaspad_version, str): 
                        min_kaspad_version = ver.parse_from_string(min_kaspad_version)
                    if self.kaspad_version(conn_timeout) <= min_kaspad_version:
                        print(self.kaspad_version(conn_timeout),  min_kaspad_version)
                        self.close()
                        continue
            except (RPCServiceUnavailable, TimeoutError) as e:
                LOG.debug(e)
                self.close()
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
        self.service = P2P_SERVICE
        self.id = str(uuid.uuid4())
        self.request_stream = P2PRequestStream
        self.external_ip =  get('https://api.ipify.org').text 
        raise NotImplementedError # unstable, unfinished
        
    # some more funcs to query for P2P server info
    
    def _byte_ip_to_ip(self, ip):
        if ip.startswith('AAAAAAAAAAAAA'):
            return  '.'.join(str(c) for c in base64.b64decode(ip))
        
    def _heartbeat(self):
        raise NotImplementedError
    
    def _handshake(self, timeouts):
        # Perform handshake according to https://github.com/kaspanet/docs/blob/main/Reference/API/P2P.md
        version_msg = self.recv(timeouts)['version'] # get version msg from kaspad
        self.node.protocol = ver(version_msg['protocolVersion'], 0, 0)
        self.node.version = ver.parse_from_string(version_msg['userAgent'].rsplit('/')[-2])
        self.node.network = version_msg['network'].split('-')[-1]
        self.send('verack') # Verify we got their version
        my_version = {
            'protocolVersion': version_msg['protocolVersion'], 
            'services': '37', 
            'timestamp': f'{int(time.time()*1000)}',
            'address': {
                'timestamp': f'{int(time.time()*1000)}', 
                'ip': self.external_ip, 
                'port': version_msg['address']['port']
                }, 
            'id': self.id,
            'userAgent': USER_AGENT, # NKOTB
            'network': version_msg['network'], 
                }
        self.send('version', my_version) #send our version
        print(self.recv(timeouts)) # get their versack
        self.send('addresses') # send empty addresses
        print(self.recv(timeouts))# get their addresses
        # now we have completed the handshake...
        pass
    
    def connect(self, host : str , port : int, filter_inv: bool = True, handshake_timeouts: float =None):
        super().connect(host, port)
        if filter_inv:
            self.request_stream.filter = set(('invRelayBlock', 'invTransactions'))
        self._handshake(handshake_timeouts)
    
    def auto_connect(self, disable_relay_tx: bool = True, min_protocol_version: Union[ver, str, None] = None, subnetwork: Union[str, None] = MAINNET,
            min_kaspad_version: Union[ver, str, None] = None, timeout: Union[float, None] = 5, 
            max_latency: Union[float, None] =  None, new_conn_on_err: bool = False):
        '''auto connect to a P2P node'''
        port = P2P_DEF_PORTS[subnetwork]
        self.restablish_new_connection = new_conn_on_err
        for node in node_acquirer.yield_open_nodes(port = port):
            try:
                self.connect(node.ip, port, disable_relay_tx, timeout)
                latency = self.kaspad_check_port(min(filter(bool, [timeout, max_latency]), default=None))
                if not latency: 
                    continue
                if latency:
                    if max_latency:
                        if latency > max_latency:
                            continue
            except (RPCServiceUnavailable, TimeoutError) as e:
                LOG.debug(e)
                continue
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
        raise NotImplementedError #only barebones idea.
    
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
    