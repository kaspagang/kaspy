from logging import DEBUG, getLogger, basicConfig, INFO

from kaspy.exceptions.exceptions import ResponseAsNoneType


from ..protos.messages_pb2 import KaspadMessage
from ..protos.messages_pb2_grpc import RPCStub

from ..defines import log_messages as lm
from ..utils.version_control import version as ver

import grpc
import socket
import json
import time

from google.protobuf import json_format


basicConfig(level=DEBUG)
basicConfig(level=INFO)
LOG = getLogger('[KASPA_NET]')

class query_node:
    
    '''some functions to help retrive basic info from a node'''
    
    ''' 
    For reference see Breaking issues in README   
    '''
    def version(addr):
        kas_msg = KaspadMessage()
        kas_msg.getInfoRequest.SetInParent()
        temp_chan = grpc.insecure_channel(f'{addr}')
        temp_stub = RPCStub(temp_chan)
        data = None
        for resp in temp_stub.MessageStream(iter([kas_msg]), wait_for_ready = True):
            data = resp
        if isinstance(data,  type(None)): # For reference see Breaking issues in README   
            LOG.debug(ResponseAsNoneType(data))
            temp_chan.close()
            pass
        else:
            temp_chan.close()
            data = json_format.MessageToDict(data)
            return ver.parse_from_string(data['getInfoResponse']['serverVersion'])
    
    
    @staticmethod
    def network(addr, timeout):
        kas_msg = KaspadMessage()
        kas_msg.getCurrentNetworkRequest.SetInParent()
        temp_chan = grpc.insecure_channel(f'{addr}')
        temp_stub = RPCStub(temp_chan)
        data = None
        for resp in temp_stub.MessageStream(iter([kas_msg]), wait_for_ready = True):
            data = resp
        if isinstance(data,  type(None)): # For reference see Breaking issues in README   
            LOG.debug(ResponseAsNoneType(data))
            temp_chan.close()
            pass
        else:
            temp_chan.close()
            data = json_format.MessageToDict(data)
            return data['getCurrentNetworkResponse']['currentNetwork'].lower()
    
    @staticmethod
    def sync(addr, **kwargs):
        '''
        I have an idea meassuring how sync'd a node is using `...` 
        This command results in info on all connected nodes and has a variable timeOffset
        if timeOffset pertains to how far ahead/behind other peer_addresses are we could
        infer a value for the sync status - unsure if this is the case
        '''
        raise NotImplementedError
    
    def is_port_open(ip, port, timeout):
        sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sck.settimeout(timeout)
        try:
            if sck.connect_ex((ip, int(port))) == 0:
                LOG.info(lm.PORT_OPEN(f'{ip}:{port}'))
                ret = True
            else:
                LOG.info(lm.PORT_CLOSED(f'{ip}:{port}'))
                ret = False
        except Exception as e:
            LOG.debug(e)
            LOG.info(lm.PORT_CLOSED(f'{ip}:{port}'))
            ret = False
        finally: sck.close()
        return ret

    
    @staticmethod
    def connected_peers(ip, port):
        try:
            return [f'{addr[-1][0]}:{port}' for addr in socket.getaddrinfo(host=ip, port=port)]
        except Exception as e:
            LOG.debug(e)
            return None
            
class Node():
    
    def __init__(self, addr: str) -> None:
        self.ip, self.port = addr.rsplit(':', 1)
        self.addr = addr
        LOG.info(lm.RETRIVING_SERVER_INFO(self.addr))
        self.version = None
        self.network = None
    
    def __str__(self):
        return self.addr
