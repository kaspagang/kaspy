from __future__ import annotations
from typing import Union


class version(object):
        
    @classmethod
    def parse_from_string(cls, string : str) -> version:
        split_string = string.rsplit('.')
        major, minor, bug_fix = 0, 0, 0 
        major, minor, bug_fix = tuple(split_string[-3:])
        major = int(''.join(filter(str.isdigit, (x for x in major))))
        minor = int(''.join(filter(str.isdigit, (x for x in minor))))
        bug_fix = int(''.join(filter(str.isdigit, (x for x in bug_fix))))
        return version(major, minor, bug_fix)
    
    
    def __init__(self, major: int , minor: int, bug_fix: int) -> None:
        self.major =  major
        self.minor = minor
        self.bug_fix = bug_fix
        assert all(isinstance(v, int) for v in [self.major, self.minor, self.bug_fix]) #only allow numerival and 'x' or 'XX notation
    
    
    def __eq__(self, comp: version) -> bool:
        if (self.major == comp.major) and (
            self.minor == comp.minor) and (
            self.bug_fix == comp.bug_fix):
            return True
        else:
            return False
    
    def __lt__(self, comp: version) -> bool:
        if self.major < comp.major:
            return True
        elif self.minor < comp.minor:
            return True
        elif self.bug_fix < comp.bug_fix:
            return True
        else:
            return False
    
    def __gt__(self, comp : version) -> bool:
        if self.major > comp.major:
            return True
        elif self.minor > comp.minor:
            return True
        elif self.bug_fix > comp.bug_fix:
            return True
        else:
            return False
    
    def __le__(self, comp: version) -> bool:
        return self.__eq__(comp) | self.__lt__(comp)
    
    def __ge__(self, comp: version) -> bool:
        return self.__eq__(comp) | self.__gt__(comp)
    
    def __str__(self):
        return f'v{self.major}.{self.minor}.{self.bug_fix}'