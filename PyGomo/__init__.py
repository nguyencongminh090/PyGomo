
from queue import Queue, Empty
from threading import Thread
from typing import TextIO, Callable, Tuple, Union
from abc import ABC, abstractmethod
import re
import math
import subprocess


class StdoutReader:
    """
    Handle stdout from engine.
    """
    def __init__(self, stream: TextIO):
        self.__stream        = stream
        self.__queues        = {}
        self.__filters       = {}

        self.__thread        = Thread(target=self.__populate_queue)
        self.__thread.daemon = True
        self.__thread.start()

    def add_category(self, category: str, filter_func):
        if category in self.__queues:
            raise ValueError(f"Category '{category}' already exists.")
        self.__queues[category]  = Queue()
        self.__filters[category] = filter_func

    def __populate_queue(self):
        while True:
            line = self.__stream.readline()
            # Break on EOF
            if line == '':
                break

            line = line.strip().lower()
            if not line:
                continue
            
            for category, filter_func in self.__filters.items():
                if filter_func(line):
                    self.__queues[category].put(line)
                    break

    def get(self, category: str, timeout: float = 0.0, reset: bool = False) -> str:
        if category not in self.__queues:
            validCategories = ", ".join(self.__queues.keys())
            raise ValueError(f"Unsupported category '{category}'. Valid options are: {validCategories}")

        if reset:
            self.reset_queue(self.__queues[category])

        try:
            return self.__queues[category].get(block=True, timeout=timeout)
        except Empty:
            return ''
        
    @staticmethod
    def reset_queue(queue: Queue):
        while queue.qsize() > 1:
            queue.get_nowait()


class IProtocol(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def play(move: str, timeLeft: int):
        ...

    @abstractmethod
    def stop(self):
        ...

    @abstractmethod
    def quit(self):
        ...

    @abstractmethod
    def send_move(self, move: str):
        ...

    @abstractmethod
    def is_ready(self) -> bool:
        ...

    @abstractmethod
    def send_command(self, *command):
        ...

    @abstractmethod
    def configure(self, option: dict):
        ...


class IProtocolHandler(ABC):
    @abstractmethod
    def get(self) -> StdoutReader:
        ...


class ProtocolFactory:
    @staticmethod
    def create(protocolType: str, sender: Callable, reader: Callable) -> IProtocol:
        match protocolType:
            case 'gomocup':
                return GomocupProtocol(sender, reader)
            case _:
                raise ValueError("Unsupported protocol")  


class ProtocolHandler:
    @staticmethod
    def create(protocolType: str, stream: TextIO) -> IProtocolHandler:
        match protocolType:
            case 'gomocup':
                return GomocupProtocolHandler(stream)
            case _:
                raise ValueError("Unsupported protocol")


class GomocupProtocolHandler(IProtocolHandler):
    def __init__(self, stream: TextIO):
        self.__stdoutReader = StdoutReader(stream)
        self.__stdoutReader.add_category('coord', self.__is_coord)
        self.__stdoutReader.add_category('message', self.__is_message)
        self.__stdoutReader.add_category('output', self.__is_output)

    def __is_coord(self, line: str) -> bool:
        return bool(re.match(r'^\d+\s*,\s*\d+(\s+\d+\s*,\s*\d+)*$', line))

    def __is_message(self, line: str) -> bool:
        return line.lower().startswith("message")

    def __is_output(self, line: str) -> bool:
        return not line.lower().startswith("error")

    def get(self):
        return self.__stdoutReader


class GomocupProtocol(IProtocol):
    def __init__(self, sender: Callable, reader: Callable):
        super().__init__()
        self.__sender = sender
        self.__reader = reader

    def play(self, move:str, timeLeft: int):
        self.configure({'time_left': timeLeft})
        self.send_move(move)
        bestMove = self.__reader('coord', timeout=timeLeft)
        info     = self.__reader('message', reset=True, timeout=timeLeft)
        if not bestMove:
            raise TimeOut(f'Timeout: Engine did not return move after {timeLeft}ms')
        return PlayResult(bestMove, info)

    def stop(self):
        self.__sender('stop')

    def quit(self):
        self.__sender('end')

    def send_move(self, move: str):
        self.__sender('turn', move)

    def is_ready(self, boardSize=15, timeout=0.0) -> bool:
        self.__sender('start', boardSize)
        return self.__reader('output', timeout=timeout) == 'ok'

    def send_command(self, *command):
        self.__sender(*command)

    def configure(self, option: dict):
        for key, value in option.items():
            self.__sender('info', key, value)


class Move:
    def __init__(self, move: Union[Tuple[int, int], str]):
        match move:
            case str() if "," in move:
                move = move.replace(" ", "")
                self.col, self.row = map(int, move.split(","))
            case str():
                move = move.replace(" ", "")
                self.col = ord(move[0].lower()) - 97
                self.row = int(move[1:]) - 1
            case tuple() if len(move) == 2:
                self.col, self.row = move

    def to_num(self):
        return self.col, self.row

    def to_alphabet(self):
        return f'{chr(97 + self.col)}{self.row + 1}'

    def to_strnum(self):
        return f'{self.col},{self.row}'

    def __str__(self):
        return self.to_alphabet()
    
    def __repr__(self):
        return f'<Move {self.to_alphabet()}>'
    

class Mate:
    def __init__(self, value: str):
        self.__value = value

    def step(self) -> int:
        return int(self.__value.replace('m', ''))


class Evaluate:
    def __init__(self, value: str):
        self.__value = value

    def score(self) -> Union[str, float, Mate]:
        if 'm' not in self.__value:
            return float(self.__value) if self.__value.lstrip('-+').isnumeric() else self.__value
        else:
            return Mate(self.__value)

    def winrate(self):
        def _to_score(x):
            if 'm' not in x:
                return float(x)
            else:
                value = Mate(self.__value).step()
                return (20000 - abs(value)) + (2 * (abs(value) - 20000) & (value >> 31))
        return 1 / (1 + math.e ** -(float(_to_score(self.__value))))

    def is_winning(self):
        return self.__value[:2] == '+m'

    def is_losing(self):
        return self.__value[:2] == '-m'


class PlayResult:
    def __init__(self, move: str, info: str):
        self.move = Move(move)
        self.info = self.__parse_uci(info) 

    def __parse_uci(self, info):
        pattern = re.compile(r"depth (\d+)-(\d+) ev ([+-]?\w?\d+) n (\d+)(?:\w) (?:\S*) (\d+) tm (\d+)(?:\S*) pv ((?:[a-zA-Z]\d+\s?)*)")
        obj     = pattern.search(info)
        if obj is not None:
            return {
                "depth"     : f'{obj.group(1)}-{obj.group(2)}',
                "ev"        : Evaluate(obj.group(3)),
                "node"      : obj.group(4),
                "nps"       : obj.group(5),
                "time"      : int(obj.group(6)),
                "pv"        : list(map(Move, obj.group(7).split()))
            }
        return {}
    
    def parse_custom(self, pattern, key: Tuple):
        pattern = re.compile(pattern)
        obj     = pattern.search(self.info)
        objDict = {}
        if obj is not None:
            for idx, value in enumerate(key):
                objDict[value] = obj.group(idx)
            
        self.info.clear()
        self.info.update(objDict)


class Engine:
    def __init__(self, path: str, protocolType: str):
        self.__engine = subprocess.Popen(path, 
                                         stdin=subprocess.PIPE, 
                                         stdout=subprocess.PIPE, 
                                         bufsize=1, universal_newlines=True)
        self.id          = self.__engine.pid
        self.protocol    = ProtocolFactory.create(protocolType, self.send, self.receive)
        self.__stdReader = ProtocolHandler.create(protocolType, self.__engine.stdout).get()

    def send(self, *command):
        command = ' '.join(str(c).upper() if i == 0 else str(c) for i, c in enumerate(command))
        self.__engine.stdin.write(f'{command}\n')
        

    def receive(self, name: str, reset=False, timeout=0.0):
        return self.__stdReader.get(name, reset, timeout)
    

class TimeOut(Exception):
    pass
