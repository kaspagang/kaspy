class ResponseAsNoneType(Exception):
    def __init__(self, Response):
        super().__init__(self,
            f'Recived Response: {Response} as type {type(Response)}'
            )

class FailedResponse(Exception):
    except_msg = f'failed to recive a response from host'
    def __init__(self): super().__init__(self.except_msg)

class NoneTypeResponse(Exception):
    except_msg = f'Recived a NoneType response from host'
    def __init__(self): super().__init__(self.except_msg)