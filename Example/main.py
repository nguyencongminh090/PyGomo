import PyGomo
import random
from AutoCorrect import AutoCorrect
from time import perf_counter as clock


class BitBoard:
    def __init__(self, size, symbol):
        self.__size = size
        self.symbol = symbol
        self.bitBoard = 0
        self.zobristTable = self.__generateZobristTable()

    def __generateZobristTable(self):
        table = {}
        for row in range(self.__size):
            for col in range(self.__size):
                table[(row, col)] = random.getrandbits(2**6)
        return table

    def hash(self) -> int:
        hash_value = 0
        for row in range(self.__size):
            for col in range(self.__size):
                if self.available((row, col)):
                    hash_value ^= self.zobristTable[(row, col)]
        return hash_value

    def addMove(self, move: (int, int)):
        self.bitBoard |= 1 << (move[0] * self.__size + move[1])

    def available(self, move: (int, int)) -> bool:
        if move[0] < 0 or move[1] < 0:
            return 0
        return 1 if self.bitBoard & (1 << (move[0] * self.__size + move[1])) else 0

    def clear(self):
        self.bitBoard = 0

    def view(self):
        line = []
        for x in range(self.__size):
            curLine = []
            for y in range(self.__size):
                if self.available((y, x)):
                    curLine.append(self.symbol)
                else:
                    curLine.append('.')
            line.append('  '.join(curLine))
        return '\n'.join(line)

    def isWin(self):
        directions = [
            (1, 0),
            (0, 1),
            (1, 1),
            (1, -1)
        ]
        for row in range(self.__size):
            for col in range(self.__size):
                if self.available((row, col)):
                    for dRow, dCol in directions:
                        count = 1
                        r, c = row + dRow, col + dCol
                        while 0 <= r < self.__size and 0 <= c < self.__size and self.available((r, c)):
                            count += 1
                            r += dRow
                            c += dCol
                        if count == 5 and (self.available((row - dRow, col - dCol)) +
                                           self.available((row + 5 * dRow, col + 5 * dCol)) == 0):
                            return True
        return False

    def length(self):
        return self.bitBoard.bit_count()

    def setSize(self, size):
        self.__size = size


class Board:
    def __init__(self, size=15):
        self.size = size
        self.__boardX = BitBoard(self.size, 'x')
        self.__boardY = BitBoard(self.size, 'o')

    def length(self):
        return self.__boardX.length() + self.__boardY.length()

    def addMove(self, move: (int, int)):
        if self.length() % 2 == 0:
            self.__boardX.addMove(move)
        else:
            self.__boardY.addMove(move)

    def available(self, move):
        return self.__boardX.available(move) or self.__boardY.available(move)

    def clear(self):
        self.__boardX.clear()
        self.__boardY.clear()

    def view(self):
        # print('[X] Board:')
        # print(self.__boardX.view())
        # print('[O] Board:')
        # print(self.__boardY.view())
        print('Current Board:')
        line = []
        for x in range(self.size + 1):
            curLine = []
            for y in range(self.size + 1):
                if self.__boardX.available((y, x)):
                    curLine.append(self.__boardX.symbol)
                elif self.__boardY.available((y, x)):
                    curLine.append(self.__boardY.symbol)
                elif x < self.size and y < self.size:
                    curLine.append('.')

                if y == self.size and x != self.size:
                    curLine.append(str(15 - x))
                if x == self.size and y != self.size:
                    curLine.append(chr(97 + y))
            line.append('  '.join(curLine))
        print('\n'.join(line))

    def isWin(self):
        return self.__boardX.isWin() or self.__boardY.isWin()

    def hash(self):
        return hex(self.__boardX.hash() ^ self.__boardY.hash()).upper()[2:]

    def setSize(self, size):
        self.clear()
        self.__boardX.setSize(size)
        self.__boardY.setSize(size)


class ParseMove:
    @staticmethod
    def __valid(move, size=15):
        if len(move) < 2:
            return False

        x = ord(move[0]) - 96
        y = int(move[1:])
        return 0 < x < size + 1 and 0 < y < size + 1

    @staticmethod
    def coord2Num(move, size=15):
        return ord(move[0]) - 97, size - int(move[1:])

    @staticmethod
    def __coord2Num(move):
        return ord(move[0]) - 97, int(move[1:]) - 1

    @staticmethod
    def num2Num(move, size=15):
        return int(move.split(',')[0]), size - 1 - int(move.split(',')[1])

    def get(self, string, numCoord=False, size=15):
        result = []
        while string:
            cur = string[0]
            string = string[1:]
            while string and string[0].isnumeric():
                cur += string[0]
                string = string[1:]
            if self.__valid(cur, size=size):
                result.append(cur if not numCoord else self.__coord2Num(cur))
        return result


class UserInterface:
    def __init__(self, controller):
        self.__controller : PyGomo.Controller = controller
        self.__board                          = Board()
        self.__command                        = Command(self.__board, self.__controller)

    def start(self):
        while True:
            command = input('Command: ').strip().split(' ')
            print(f'<- Command: {command}')
            if command[0] == 'quit':
                self.__controller.quit()
                print('Closed engine')
                break
            self.__command.processCommand(command[0], *command[1:])


class Command:
    def __init__(self, board: Board, controller: PyGomo.Controller):
        self.__board: Board = board
        self.__controller   = controller
        self.__size         = self.__board.size

    def processCommand(self, command, *args):
        autoCorrect = AutoCorrect(('setBoardSize', 'play', 'analyze'))
        match autoCorrect.search(command, len(command)):
            case 'setBoardSize':
                self.__board.setSize(args[0])
                self.__size = args[0]
                print(f'Board size: {self.__size}')
            case 'play':
                self.__play()
            case 'analyze':
                self.__analyze()

    def __play(self):
        compTurn = 1
        turn = 0
        listOfMove = []

        print('Engine play first' if compTurn == turn else 'Human play First')

        time   = int(input('Time (ms): '))
        rule   = input('Rule: ')
        config = {
            'timeout_match': time,
            'timeout_turn' : time,
            'game_type'    : 1,
            'rule'         : rule,
            'usedatabase'  : 1}

        self.__loadEngine(config)
        if self.__controller.isReady(self.__size):
            print('Engine loaded')
        else:
            print("Can't load engine!")
            return

        while True:
            if compTurn == turn and turn == 0:

                start = clock()
                self.__controller.protocol().setPos(listOfMove)
                stop = clock()
                move = self.__controller.get("move")

                print('->', self.__controller.get('output'))
                print(f'-> Run time: {stop - start:.7f}\n\n')
                print(f'-> Move: {move}')

                self.__board.addMove(ParseMove().num2Num(move, size=self.__size))
                print(self.__board.view())

                self.__controller.calcTimeLeft(int(round(stop - start, 3) * 1000))

                turn = (turn + 1) % 2
                listOfMove.append(move)
            elif compTurn == turn:
                self.__controller.protocol().playMove(listOfMove[-1])

                start = clock()
                enMove: PyGomo.Move = self.__controller.get("move")
                stop = clock()
                move   = enMove.move

                print(f'**INFO**')
                print(f'- Depth: {enMove.info["depth"]}')
                print(f'- Eval : {enMove.info["ev"].toWinrate()}')
                print(f'- Nodes: {enMove.info["nodes"]}')
                print(f'- Time : {enMove.info["tm"]}s')
                print(f'- Pv   : {enMove.info["pv"]}')
                print()
                print(f'-> Run time: {stop - start:.3f}s')
                print(f'-> Move: {move.coord}')

                self.__board.addMove(ParseMove().num2Num(move.coord, size=self.__size))
                self.__board.view()

                self.__controller.calcTimeLeft(int(round(stop - start, 3) * 1000))

                turn = (turn + 1) % 2
                listOfMove.append(move)

            else:
                inp = input('Your Move: ').strip()
                if inp.lower() == 'resign':
                    self.__controller.resetTime()
                    print('[Resigned]')
                    break
                elif not self.__board.available(ParseMove().coord2Num(inp, size=self.__size)):
                    listOfMove.append(f'{ord(inp[0]) - 97},{int(inp[1:]) - 1}')
                    turn = (turn + 1) % 2
                    self.__board.addMove(ParseMove().coord2Num(inp, size=self.__size))
                    self.__board.view()

            if self.__board.isWin():
                print('Finished')
                self.__board.clear()
                break
        self.__board.clear()

    def __analyze(self):
        compTurn = random.randint(0, 1)
        turn = 0
        first = True

        print('Engine play first' if compTurn == turn else 'Human play First')

        time = int(input('Time (ms): '))
        rule = input('Rule: ')
        listOfMove = [f'{x},{y}' for x, y in ParseMove().get(input('Pos: '), numCoord=True, size=self.__size)]
        print('ListMove:', listOfMove)

        for i in listOfMove:
            print(i, ParseMove().num2Num(i, size=self.__size))
            self.__board.addMove(ParseMove().num2Num(i, size=self.__size))
        self.__board.view()

        config = {
            'timeout_match': time,
            'timeout_turn': time,
            'time_left'   : time,
            'game_type': 1,
            'rule': rule,
            'usedatabase': 1}

        self.__loadEngine(config)
        if self.__controller.isReady(self.__size):
            print('Engine loaded')
        else:
            print("Can't load engine!")
            return

        while True:
            if compTurn == turn and first:

                self.__controller.protocol().setPos(listOfMove)

                start = clock()
                enMove: PyGomo.Move = self.__controller.get("move")
                stop = clock()
                move = enMove.move

                print(f'**INFO**')
                print(f'- Depth: {enMove.info["depth"]}')
                print(f'- Eval : {enMove.info["ev"].toWinrate()}')
                print(f'- Nodes: {enMove.info["nodes"]}')
                print(f'- Time : {enMove.info["tm"]}s')
                print(f'- Pv   : {enMove.info["pv"]}')
                print()
                print(f'-> Run time: {stop - start:.3f}s')
                print(f'-> Move: {move.coord}')

                self.__board.addMove(ParseMove().num2Num(move.coord, size=self.__size))
                self.__board.view()

                self.__controller.calcTimeLeft(int(round(stop - start, 3) * 1000))

                turn = (turn + 1) % 2
                listOfMove.append(move)

                first = False
            elif compTurn == turn:
                self.__controller.protocol().playMove(listOfMove[-1])

                start = clock()
                enMove: PyGomo.Move = self.__controller.get("move")
                stop = clock()
                move = enMove.move

                print(f'**INFO**')
                print(f'- Depth: {enMove.info["depth"]}')
                print(f'- Eval : {enMove.info["ev"].toWinrate()}')
                print(f'- Nodes: {enMove.info["nodes"]}')
                print(f'- Time : {enMove.info["tm"]}s')
                print(f'- Pv   : {enMove.info["pv"]}')
                print()
                print(f'-> Run time: {stop - start:.3f}s')
                print(f'-> Move: {move.coord}')

                self.__board.addMove(ParseMove().num2Num(move.coord, size=self.__size))
                self.__board.view()

                self.__controller.calcTimeLeft(int(round(stop - start, 3) * 1000))

                turn = (turn + 1) % 2
                listOfMove.append(move)

            else:
                inp = input('Your Move: ').strip()
                if inp.lower() == 'resign':
                    self.__controller.resetTime()
                    print('[Resigned]')
                    break
                elif not self.__board.available(ParseMove().coord2Num(inp)):
                    listOfMove.append(f'{ord(inp[0]) - 97},{int(inp[1:]) - 1}')
                    turn = (turn + 1) % 2
                    self.__board.addMove(ParseMove().coord2Num(inp))
                    self.__board.view()

            if self.__board.isWin():
                print('Finished')
                self.__board.clear()
                break
        self.__board.clear()

    def __loadEngine(self, config: dict):
        self.__controller.setConfig(config)
        self.__controller.setTimeMatch(config['timeout_match'])
        self.__controller.setTimeLeft(config['timeout_match'])


def main():
    engine     = PyGomo.Engine(r'D:\Python\EngineModule\GomokuTool\Engine\engine.exe')
    protocol   = PyGomo.Protocol()
    controller = PyGomo.Controller(engine, protocol)
    userInterface = UserInterface(controller)
    userInterface.start()


if __name__ == '__main__':
    main()
