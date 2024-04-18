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
