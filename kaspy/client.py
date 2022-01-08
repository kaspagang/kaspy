from threading import Event, Lock, Thread
import time

import grpc
import json
from google.protobuf import json_format
from logging import INFO, getLogger, basicConfig

from .network.node import Node, node_acquirer
from .protos.messages_pb2 import KaspadMessage, _KASPADMESSAGE
from .protos.messages_pb2_grpc import RPCStub
from .defines import MAINNET, KASPAD_VERSION
from .defines import log_messages as lm, RPC, P2P
from .exceptions import exceptions as e
from .utils.version_control import version as ver
from queue import SimpleQueue

basicConfig(level=INFO)
LOG = getLogger('[KASPA_CLI]')


class ServerStatus:
    '''
    register and handle changes in server status
    '''

    def __init__(self):
        raise NotImplementedError

class CLientStatus:
    '''
    register and handle changes in client status
    '''

    def __init__(self):
        raise NotImplementedError
    
class kaspa_client:
    
    def __init__(self):
        self._RPCstub = RPCStub
        self._P2Pstub = NotImplemented
        self._chan = None
        self.node = Node
        self._is_connected = lambda : True if self._chan else False
        
        #for threading
        self._requests = SimpleQueue()
        self._responses = SimpleQueue()
        self._subscitptions = NotImplemented
        self._notifications = NotImplemented
        self._activate_stream = Event()
        self._lock = Lock()
        self._streamer = Thread(target=self._stream, daemon=True).start()
        
    def disconnect(self):
        raise NotImplementedError
    
    def close(self):
        raise NotImplementedError
    
    def subscribe(self):
        raise NotImplementedError
    
    def unsubscribe(self):
        raise NotImplementedError
    
    def _serialize_response_to_json(self, response):
        raise NotImplementedError

    def _serialize_request(self, command, payload):
        assert command == _KASPADMESSAGE.fields_by_name[command].name #this is important so we don't execute arbitary python code in this function
        LOG.info(lm.SERIALIZING_DATA(self.node, command))
        kaspa_msg = KaspadMessage()
        app_msg = eval(f'kaspa_msg.{command}') #should not use eval - but seems like the easiest way for now.
        if payload:
            if isinstance(payload, dict):
                json_format.ParseDict(payload, app_msg)
            if isinstance(payload, str):
                json_format.Parse(payload, app_msg)
        app_msg.SetInParent()
        return kaspa_msg
    
    def _serialize_response_to_dict(self, response):
        return json_format.MessageToDict(response)
    
    def _stream(self):
        while True:
            self._activate_stream.wait()
            for resp in self._RPCstub.MessageStream(req for req in self._requests_iterator()):
                self._responses.put(resp)
                    
    def _requests_iterator(self):
        while True:
            yield self._requests.get()
    
    def send(self, command, payload):
        LOG.info(lm.REQUEST_MESSAGE(command, self.node))
        self._requests.put(self._serialize_request(command, payload))
    
    def recv(self):
        return self._serialize_response_to_dict(self._responses.get())
    
    def request(self, command, payload = None):
        self.send(command, payload)
        resp = self.recv()
        LOG.info(lm.RETRIVED_MESSAGE(
            next(iter(resp.keys())),
            command,
            self.node
                    ))
        return resp

    def connect(self, host=None, port=None, stub = RPC):
        self.node = Node(f'{host}:{port}')
        LOG.info(lm.CONNECTING_TO_NODE(self.node))
        self._chan = grpc.insecure_channel(self.node.addr, compression=grpc.Compression.Gzip)
        self._RPCstub = RPCStub(self._chan)
        self._activate_stream.set()
        LOG.info(lm.CONNECTED_TO_NODE(self.node))
    
    def auto_connect(self, min_version = KASPAD_VERSION, subnetworks = MAINNET, stub = NotImplemented, timeout = 1, max_latency= 0.8):
        for node in node_acquirer.yield_open_nodes(max_latency=max_latency, timeout=timeout):
            self.connect(node.ip, node.port)
            kaspad_ver = self.request('getInfoRequest')
            kaspad_ver = ver.parse_from_string(kaspad_ver['getInfoResponse']['serverVersion'])
            if kaspad_ver < min_version:
                LOG.info(lm.OLD_VERSION_ABORT(node, kaspad_ver, min_version))
                self.disconnect()
                continue
            kaspad_network = self.request('getCurrentNetworkRequest')['getCurrentNetworkResponse']['currentNetwork'].lower()
            if kaspad_network not in subnetworks:
                LOG.info(lm.DISSALLOWED_NETWORK_ABORT(node, kaspad_network, subnetworks))
                self.disconnect()
                continue
            break
        LOG.info(lm.PASSED_VALIDITY_CHECKS(self.node, kaspad_ver, kaspad_network))