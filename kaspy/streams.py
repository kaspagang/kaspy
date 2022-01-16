from kaspy.protos.messages_pb2_grpc import RPCStub, P2PStub
from kaspy.protos.messages_pb2 import _KASPADMESSAGE, KaspadMessage
from kaspy.network.node import Node
from kaspy.defines import CONNECTED, DISCONNECTED, CLOSED

import grpc
import json
from queue import Empty, SimpleQueue
from google.protobuf import json_format
from typing import Any, Callable, Union
from threading import Event, Thread
from .excepts.exceptions import InvalidCommand

class BaseStream:
    
    def __init__(self, node: Node, stub: Union[RPCStub, P2PStub], idle_timeout: float = None):
        self._conn = grpc.insecure_channel(f'{node}')
        self._stub = stub(self._conn)
        self._halt = Event()
        self._idle_timeout = idle_timeout
        self._inputs = SimpleQueue()
        self.status = CONNECTED
    
    def start(self):
        Thread(target=self.run, daemon=True).start()
    
    def run(self):
        self._halt.set()
        self.switch()
    
    def switch(self):
        self._halt.wait()
        try:
            for resp in self._stub.MessageStream((inp for inp in self.loop()), timeout=self._idle_timeout):
                resp = self._serialize_response_to_dict(resp)
                self.process_output(resp)
        except grpc.RpcError as e:
            if self.status == CLOSED:
                pass
            else:
                raise e
    
    def loop(self):
        while True:
            inp =  self._inputs.get()
            if inp == DISCONNECTED:
                self.switch()
            else:
                yield self._serialize_request(*inp)
    
    def disconnect(self):
        self._halt.clear()
        self._inputs.put(DISCONNECTED)
        pass
    
    def reconnect(self):
        self.status = CONNECTED
        self._halt.set()
    
    def close(self):
        self.status = CLOSED
        self._conn.close()    

    def process_output(self, output):
        raise NotImplementedError
    
    def _serialize_request(self, command : str, payload : Union[dict, str, None] = {}) -> KaspadMessage:
        if payload is None: payload = {}
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

class RequestStream(BaseStream):
    
    def __init__(self, node: Node, stub: Union[RPCStub, P2PStub], idle_timeout: float = None, filter: set = set([])):
        super().__init__(node, stub, idle_timeout=idle_timeout)
        self._outputs = SimpleQueue()
        self.filter = filter
        
    def get(self, timeout: Union[int, float, None] = None) -> KaspadMessage:
        try:
            return self._outputs.get(timeout=timeout)
        except Empty:
            raise TimeoutError
    
    def put(self, input):
        self._inputs.put(input)
    
    def process_output(self, output):
        test = next(iter(output.keys()))
        if test in self.filter:
            pass
        else:
            self._outputs.put(output)

class SubcribeStream(BaseStream):
    
    def __init__(self, node, command: str, payload: Union[None,dict], callback: Callable[[dict], Any], stub: Union[RPCStub, P2PStub], idle_timeout: float = None):
        super().__init__(node=node, stub=stub, idle_timeout=idle_timeout)
        self.subscription = (command, payload)
        sub_msg = command[6:].replace('Request', 'Notification')
        self._sub_msg = sub_msg[0].lower() + sub_msg[1:]
        self._callback = callback
        self._hash =  hash(f'{self._sub_msg}')
        
    def run(self):
        self._halt.set()
        self._inputs.put(self.subscription)
        self.switch()
    
    def _send_thread_to_callback(self, output):
        Thread(target=self._callback, args=(output,), daemon=True).start()
        
    def process_output(self, output):
        if next(iter(output.keys())) == self._sub_msg:
            self._send_thread_to_callback(output)
            
class P2PRequestStream(BaseStream):
    
    def __init__(self, node: Node, stub: Union[RPCStub, P2PStub], idle_timeout: float = None, filter_inv = True):
        super().__init__(node, stub, idle_timeout=idle_timeout)
        self._outputs = SimpleQueue()
        self._filter_inv = filter_inv
        
    def get(self, timeout: Union[int, float, None] = None) -> KaspadMessage:
        try:
            return self._outputs.get(timeout=timeout)
        except Empty:
            raise TimeoutError
    
    def put(self, input):
        self._inputs.put(input)
    
    def process_output(self, output):
        if output.name in self.filter:
            pass
        else:
            self._outputs.put(output)