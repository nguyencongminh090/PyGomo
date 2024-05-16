import subprocess
from queue import Queue, Empty
from threading import Thread
import math
from abc import ABC


class StdoutReader:
    """
    stdout -> string
    Read output from engine
    Output include 2 types:
        - Message (start with MESSAGE ...)
        - No prefix (ex: "OK", ...)
        - Coord ("7,7", ...)
    """
    def __init__(self, stream):
        self.__stream = stream
        self.__queueMessage = Queue()
        self.__queueOutput = Queue()
        self.__queueCoord = Queue()

        self.__thread = Thread(target=self.__populateQueue)
        self.__thread.daemon = True
        self.__thread.start()

    def __populateQueue(self):
        while True:
            line = self.__stream.readline().strip()
            if line == '':
                continue
            elif self.isMessage(line):
                self.__queueMessage.put(line)
            elif self.isCoord(line):
                self.__queueCoord.put(line)
            elif self.isOutput(line):
                self.__queueOutput.put(line)
            elif line is None:
                break

    def isOutputQueueEmpty(self) -> bool:
        return self.__queueOutput.empty()

    def isMessageQueueEmpty(self) -> bool:
        return self.__queueMessage.empty()

    def isCoordQueueEmpty(self) -> bool:
        return self.__queueCoord.empty()

    @staticmethod
    def isMessage(line) -> bool:
        """Return True if line is Message"""
        return line.lower().startswith('message')

    @staticmethod
    def isOutput(line: str) -> bool:
        """Return True if line is output"""
        return not line.lower().startswith('error')

    @staticmethod
    def isCoord(line) -> bool:
        if line.lower() == 'swap':
            return True
        for coord in line.split():
            if not coord.split(',')[0].isnumeric() or not coord.split(',')[1].isnumeric():
                return False
        return True

    def getMessage(self, timeout=0.0):
        try:
            output = self.__queueMessage.get(block=True, timeout=timeout)
            return output if output is not None else ''
        except Empty:
            return None

    def getOutput(self, timeout=0.0):
        try:
            output = self.__queueOutput.get(block=True, timeout=timeout)
            return output if output is not None else ''
        except Empty:
            return None

    def getCoord(self, timeout=0.0):
        try:
            output = self.__queueCoord.get(block=True, timeout=timeout)
            if output is not None:
                self.__clearQueue(self.__queueMessage)
                return output.removesuffix('\n')
            return ''
        except Empty:
            return None

    @staticmethod
    def __clearQueue(queue: Queue):
        while queue.qsize() > 1:
            queue.get_nowait()


# noinspection PyUnresolvedReferences
class Engine:
    def __init__(self, path):
        super().__init__()
        self.__engine = subprocess.Popen(path, stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         bufsize=1, universal_newlines=True)
        self.ID = self.__engine.pid
        self.__stdoutReader = StdoutReader(self.__engine.stdout)
        self.__timeManage = TimeManage(self.ID)

    def send(self, *command):
        """Send input to engine"""
        new_command = []
        for i in range(len(command)):
            if i == 0:
                new_command.append(str(command[i]).upper())
            else:
                new_command.append(str(command[i]))
        command = ' '.join(new_command)
        print('<--', command)
        self.__engine.stdin.write(command + '\n')

    def receive(self, option):
        """Receive output from engine"""
        match option:
            case 'move':
                return self.__getMove()
            case 'output':
                # For ABOUT, START 15
                output = self.__stdoutReader.getOutput(self.__timeManage.setting.timeLeft / 1000)
                return output.lower() if output is not None else ''

    def __getMove(self):
        output = self.__stdoutReader.getCoord(self.__timeManage.setting.timeLeft / 1000)
        message = self.__stdoutReader.getMessage()
        if output is None:
            return TimeOut(f"Engine didn't return move after {self.__timeManage.setting.timeLeft}ms")
        return Move(output, message)


class IProtocol(ABC):
    def setEngine(self, engine: Engine):
        ...

    def playMove(self, move: str):
        ...

    def setPos(self, listPos: [str]):
        ...

    def stop(self):
        ...

    def quit(self):
        ...

    def isReady(self, boardSize: int) -> bool:
        ...

    def getEngineInfo(self) -> str:
        ...

    def send(self, *args):
        ...

    def setConfig(self, keyword, value):
        ...


class GomocupProtocol(IProtocol):
    def __init__(self):
        """Gomocup IProtocol implement"""
        self.__engine : Engine = ...

    def setEngine(self, engine: Engine):
        self.__engine : Engine = engine

    def playMove(self, move):
        self.__engine.send('turn', move)

    def stop(self):
        self.__engine.send('stop')

    def quit(self):
        self.__engine.send('end')

    def setConfig(self, keyword, value):
        self.__engine.send('info', keyword, value)

    def getEngineInfo(self):
        self.__engine.send('about')

    def multiPv(self, value):
        self.__engine.send('yxnbest', value)

    def isReady(self, boardSize=15):
        self.__engine.send('start', boardSize)
        if self.__engine.receive('output') == 'ok':
            return True
        return False

    def setPos(self, listOfMove: [str]):
        self.__engine.send('board')
        for idx, move in enumerate(listOfMove):
            if len(listOfMove) % 2 == idx % 2:
                self.__engine.send(move + ',' + '1')
            else:
                self.__engine.send(move + ',' + '2')
        self.__engine.send('done')

    def send(self, *args):
        """Send custom command to engine"""
        self.__engine.send(*args)


# noinspection PyUnresolvedReferences
class TimeManage:
    DICT_OBJ = {}

    def __new__(cls, key):
        if not hasattr(cls, 'instance'):
            cls.instance = super(TimeManage, cls).__new__(cls)
        if key not in cls.DICT_OBJ:
            cls.DICT_OBJ[key] = {}
        cls.instance.__dict__ = cls.DICT_OBJ[key]
        return cls.instance


# noinspection PyTypeHints, PyUnresolvedReferences
class Controller:
    def __init__(self):
        self.__engine     : Engine     = ...
        self.__protocol   : IProtocol  = ...
        self.__timeManage : TimeManage = ...

    def setEngine(self, engine: Engine):
        assert self.__protocol is not Ellipsis
        self.__engine = engine
        self.__protocol.setEngine(self.__engine)
        self.__timeManage = TimeManage(self.__engine.ID)
        self.__timeManage.setting : TimeSetting = TimeSetting()

    def setProtocol(self, protocol: IProtocol):
        self.__protocol = protocol

    def get(self, option):
        return self.__engine.receive(option)

    def setConfigures(self, config: dict):
        for i in config:
            self.__protocol.setConfig(i, config[i])

    def calcTimeLeft(self, delta):
        self.__timeManage.setting.timeLeft -= delta - self.__timeManage.setting.timePlus

    def updateTimeLeft(self):
        self.__protocol.setConfig('time_left', self.__timeManage.setting.timeLeft)

    def resetTime(self):
        self.__timeManage.setting.timeLeft = self.__timeManage.setting.timeMatch
        ...

    def setTimeMatch(self, value):
        """Time must be in millisecond"""
        self.__timeManage.setting.timeMatch = value

    def setTimeLeft(self, value):
        """Time must be in millisecond"""
        self.__timeManage.setting.timeLeft  = value

    def playMove(self, move: str):
        self.__protocol.playMove(move)

    def setPos(self, listPos: [str]):
        self.__protocol.setPos(listPos)

    def stop(self):
        self.__protocol.stop()

    def quit(self):
        self.__protocol.quit()

    def isReady(self, boardSize=15) -> bool:
        return self.__protocol.isReady(boardSize)

    def getEngineInfo(self) -> str:
        self.__protocol.getEngineInfo()

    def send(self, *args):
        """Send custom command to engine"""
        self.__protocol.send(*args)

    def setConfig(self, keyword, value):
        self.__protocol.setConfig(keyword, value)


class Setting:
    def __init__(self):
        self.TimeManage = TimeSetting()


class TimeSetting:
    def __init__(self):
        """
        Default value:\n
        timeMatch = 60000\n
        timeLeft  = 60000\n
        timePlus  = 0
        """
        self.timeMatch = 60000
        self.timeLeft  = 60000
        self.timePlus  = 0


class TimeOut(Exception):
    pass


class Move:
    def __init__(self, move: str, info: str):
        self.move: Coord = Coord(move)
        self.__info = info.strip().lower().split()
        self.info = self.__infoClassify()

    def __infoClassify(self):
        # MESSAGE depth 27-45 ev 245 n 100M n/ms 1700 tm 1145 pv a3 b4 f2
        infoDict = {'depth': self.__info[self.__info.index('depth') + 1],
                    'ev'   : Evaluation(self.__info[self.__info.index('ev') + 1]),
                    'nodes': self.__info[self.__info.index('n') + 1],
                    'pv'   : self.__info[self.__info.index('pv') + 1:],
                    'tm'   : int(self.__info[self.__info.index('tm') + 1]) / 1000}
        return infoDict


class Coord:
    def __init__(self, coord: str):
        self.coord = coord

    def toNum(self):
        return ord(self.coord[0]) - 97, int(self.coord[1:]) - 1


class Evaluation:
    def __init__(self, ev: str):
        self.ev = int(ev) if ev.lstrip('-+').isnumeric() else ev

    def toWinrate(self, n=2):
        if isinstance(self.ev, int):
            return f'{round((math.e ** (self.ev / 200)) / (1 + math.e ** (self.ev / 200)) * 100, n)}%'
        else:
            return self.ev
