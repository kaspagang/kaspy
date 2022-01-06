from . import settings
import grpc
import json
from google.protobuf import json_format
from logging import INFO, getLogger, basicConfig

from .network.node import Node
from .protos.messages_pb2 import KaspadMessage, _KASPADMESSAGE
from .protos.messages_pb2_grpc import RPCStub
from .defines import *
from .defines import log_messages as lm
from .exceptions import exceptions as e

basicConfig(level=INFO)
LOG = getLogger('[KASPA_CLIENT]')

class kaspa_client:
    
    def __init__(self):
        self._stream = None
        self._chan = None
        self.node = None
        self._is_connected = lambda : True if self._chan else False
        
        #for future send() / recv()
        self._requests = NotImplemented
        self._responses = NotImplemented
        
        self.host = Node

    def _reset(self):
        self._stream = None
        self._requests = NotImplemented
        self._responses = NotImplemented
        self.node = None
        self.host = str()
        self.port = str()
        self._chan = None
    
    def _serialize_request(self, command, payload):
        '''
        I am at a loss here, using eval is dirty, but only other option I can think of involves creating a huge dictionary manually.
        '''
        assert command == _KASPADMESSAGE.fields_by_name[command].name #this is important so we don't execute arbitary python code in this function
        LOG.info(lm.SERIALIZING_DATA(self.node, command))
        kaspa_msg = KaspadMessage()
        app_msg = eval(f'kaspa_msg.{command}') #should not use eval - but seems like the easiest way for now.
        if payload:
            if isinstance(payload, dict):
                json_format.ParseDict(payload)
            if isinstance(payload, str):
                json_format.Parse(payload, app_msg)
        app_msg.SetInParent()
        print(json_format.MessageToDict(kaspa_msg))
        return kaspa_msg
    
    def auto_connect(self, **kwargs):
        '''this may take a while...'''
        from kaspy.network.network import KaspaNetwork
        node = KaspaNetwork.retrive_valid_node()
        host, port = node.ip, node.port
        self.connect(host, port)            
    
    def request(self, command, payload = None):
        '''
        Requires debugging and error handling - occationally we get `resp_as_json`` as `NoneType`. No idea why.
        '''
        payload = None if payload == {} else payload
        LOG.info(lm.REQUEST_MESSAGE(command, self.node))
        payload = self._serialize_request(command, payload)
        resp = next(self._stream(iter([payload,]),  wait_for_ready = True), None)
        if isinstance(resp,  type(None)):
            LOG.debug(e.ResponseAsNoneType(resp))
            pass
        elif isinstance(resp, KaspadMessage):
            resp = json_format.MessageToJson(resp)
            LOG.info(lm.RETRIVED_MESSAGE(
                next(iter(json.loads(resp).keys())),
                command,
                self.node
                        ))
            return resp
        else:
            raise Exception(f'reponse was sent as type {type(resp)} expected type {type(KaspadMessage)}')

    def connect(self, host=None, port=None):
        self.node = Node(f'{host}:{port}')
        LOG.info(lm.CONNECTING_TO_NODE(self.node))
        self._chan = grpc.insecure_channel(self.node.addr)
        self._stream = RPCStub(self._chan).MessageStream
        LOG.info(lm.CONNECTED_TO_NODE(self.node))
    
    def close(self):
        self._chan.close()
        self._reset()        
        LOG.info(lm.CLOSING_CHANNEL(self.node))