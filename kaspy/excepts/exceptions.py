from kaspy.defines import P2P_SERVICE, RPC_SERVICE

class RPCResponseException(Exception):
    def __init__(self, node, code, details):
        '''Exception that is raised when server cannot process a request'''
        super().__init__(f'{code}: did not get valid response from host {node}; {details}')
        
class CLientClosed(Exception):
    def __init__(self, node, command):
        '''Exception that is raised when client is closed and tries to send data'''
        super().__init__(f'could not send {command} to host {node} because the client is CLOSED')
    
class ClientDisconnected(Exception):
    def __init__(self, node, command):
        '''Exception that is raised when client is disconnected and tries to send data'''
        super().__init__(f'could not send {command} to host {node} because the client is DISCONNECTED')

class WrongService(Exception):
    def __init__(self, node, server_service, command):
        '''Exception that is raised when client is trying to send P2P commands to RPC, and vice versa'''
        super().__init__(
            f'''
            could not send {command} to {server_service} host {node}; command is a 
            {RPC_SERVICE if server_service == P2P_SERVICE else P2P_SERVICE} command
            ''')
class RPCServiceUnavailable(Exception):
    def __init__(self, node, code, details):
        super().__init__(f'Service on {node} is currently {code}.. Reason: {details}')
              
class InvalidCommand(Exception):
    def __init__(self, node, command):
        '''Exception that is raised when command is not registered anywhere in the proto files'''
        super().__init__(f'could not send command {command} to {node}; {command} is not a valid command')

class CommandIsNotSubcribable(Exception):
     def __init__(self, node, command):
        '''Exception that is raised when command is not registered anywhere in the proto files'''
        super().__init__(f'cannot subscribe to {node} with {command}; {command} is not subscribable')

class SubscriptionCannotBeUnsubscribed(Exception):
     def __init__(self, node, command):
        '''Exception that is raised when command is not registered anywhere in the proto files'''
        super().__init__(f'cannot unsubscribe to {command} in {node}')
    
