class Node():
    
    def __init__(self, addr: str) -> None:
        self.ip, self.port = addr.rsplit(':', 1)
        self.addr = addr
    
    def __str__(self):
        return self.addr
