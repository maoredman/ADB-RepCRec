from enum import Enum
from collections import namedtuple, defaultdict
from sys import stdin

# class TransactionState(Enum):
#     BLOCKED = 0
#     WAITING = 1

# locktable, conflictgraph maintanance
# at read/write operation: add lock to locktable, add edge to conflictgraph
# at end: clean all T's lock in locktable, clean all edges connected to T on conflictgraph
# how to clean lock in locktable:
# iterate through all lock  and find T's lock (slow)
# iterate through all data items that T has lock on

class Transaction():
    def __init__(self, name, RO, blocked, start):
        self.name = name
        self.RO = RO
        self.blocked = blocked
        self.startTime = start
        self.locks = dict()
        self.variableFinalValues = dict()


class DataManager():
    def __init__(self, id: int):
        self.d = dict()

    def __getitem__(self, item):
        return self.d[item]


class State(Enum):
    GRANTED = 0
    WAITING = 1

    
class LockTable():

    def __init__(self):
        self.LockTuple = namedtuple('LockTuple', ['T', 'type', 'state'])
        self.table = {"x" + str(i) : [] for i in range(1, 21)} # Dict[variable, List[(transaction, R/W, state)]]

    """
    return a tuple (lock, transaction)
    lock: the lock T get after request a lock - R/W/None
    T': the transation that prevents T from getting a lock - T'/None
    """
    def getReadLock(self, T: Transaction, x: str) -> tuple[str, Transaction]:
        curLock = self.__getExistLock(T, x)
        if curLock:
            if curLock.state == State.GRANTED:
                return curLock, None
            else:
                raise Exception("encounter blocked operation from the same transaction")

        if len(self.table[x]) == 0:
            self.table[x].append(self.LockTuple(T, "R", State.GRANTED))
            return "R", None
        elif self.table[x][-1].state == State.GRANTED and self.table[x][-1].type == "R":
            self.table[x].append(self.LockTuple(T, "R", State.GRANTED))
            return "R", None
        else:
            self.table[x].append(self.LockTuple(T, "R", State.WAITING))
            return None, self.table[x][-2].T

    """
    return a tuple (lock, T')
    lock: the lock T get after request a lock - W/None
    T': the transation that prevents T from getting a lock - T'/None
    """
    def getWriteLock(self, T: Transaction, x: str) -> tuple[str, Transaction]:
        curLock = self.__getExistLock(T, x)
        if curLock:
            if curLock.type == "W" and curLock.state == State.GRANTED:
                return curLock, None
            else:
                raise Exception("encounter blocked operation from the same transaction")
        

        if len(self.table[x]) == 0:
            newLock = self.LockTuple(T, "W", State.GRANTED)
            self.table[x].append(newLock)
            return newLock, None
        else:
            blockingLock = self.table[x][-1]
            self.table[x].append(self.LockTuple(T, "W", State.WAITING))
            return None, blockingLock.T

    """
    return current lock that T has on x. If not exist, return None
    """
    def __getExistLock(self, T: Transaction, x: str): 
        for lock in self.table[x]:
            if lock.T == T:
                return lock
        return None

    '''
    bool : whether the there exists a deadlock
    Transacion: the transation to kill to resolve the deadlock
    '''
    def __checkDeadLock(self) -> tuple[bool, Transaction]:
        
        # build graph
        graph = defaultdict(list)
        visited = defaultdict(0)
        for queue in self.table:
            # build edge
            for i in range(1, len(queue)):
                if queue[i].state == State.WAITING:
                    graph[queue[i-1].T].append(queue[i].T)
            # get all node
            for T, _, _ in queue:
                visited.add(T)
        # cycle detection
        def dfs(T: Transaction, trail):
            if visited[T] == 1:
                return True, trail
            elif visited[T] == 2:
                return False, []
            
            visited[T] = 1
            trail.append(T)
            for neighbor in graph[T]:
                if dfs(neighbor, trail):
                    return True, trail
            visited[T] = 2
            trail.pop()

            return False, []

        
        for node in visited.keys():
            haveCycle, trail = dfs(node, [])

            if haveCycle:
                youngestT, youngestAge = None, None
                for T in trail:
                    if youngestT == None or T.startTime > youngestAge:
                        youngestT = T
                        youngestAge = T.startTime
                return True, youngestT
        return False, None


class TransactionManager():

    def __init__(self):
        dataManagerTuple = namedtuple('dataManagerTuple', ['dataManager', 'lastFail', 'lastRecover'])
        self.time = 0
        self.transactions = dict() # Dict[str, Transaction]
        self.lockTable = LockTable()
        self.instructionBuffer = []
        # self.conflictGraph = dict() # Dict[Transaction, List[Transaction], key - being waited, value - waiting
    

    # when an instruction in the instructionBuffer becomes unblocked, this function can be reused to run it
    def runInstruction(self, line: str):
        command, params = line.split("(")
        params = [param.strip() for param in params.strip("()").split(",")]

        if command == "begin":
            self.begin(params[0])
        elif command == "beginRO":
            self.beginRO(params[0])
        elif command == "R":
            if not self.read(params[0], params[1]):
                self.instructionBuffer.append(line)
        elif command == "W":
            self.write(params[0], params[1], params[2])
        elif command == "dump":
            self.dump()
        elif command == "end":
            self.end(params[0])
        elif command == "fail":
            self.end(params[0])
        elif command == "recover":
            self.recover(params[0])
        else:
            raise Exception("Command Not Found")

    def tick(self):
        self.time += 1

    def begin(self, transactionName: str):
        assert(transactionName not in self.transactions)
        T = Transaction(params[0], False, False, TM.time)
        self.transactions[transactionName] = T
    
    def beginRO(self, transactionName: str):
        assert(transactionName not in self.transactions)
        T = Transaction(params[0], True, False, TM.time)
        self.transactions[transactionName] = T


    # return True/False depending on whether the read was blocked
    # print out the value of the variable if not blocked
    def read(self, transactionName: str, x: str):
        assert(transactionName in self.transactions)
        T = self.transactions[transactionName].RO
        if T.RO:
            # TODO: print variable value
            return True

        # regular read
        if self.__getLock(T, x, "R"):
            # TODO: print variable value
            return True
        return False
    

    # return True/False depending on whether the write was blocked
    def write(self, transactionName: str, x: str, val: str):
        assert(transactionName in self.transactions)
        T = self.transactions[transactionName]

        if not self.__getLock(T, x, "W"):
            return False

        # TODO: implement the actual write logic
        return True


    def dump(self):
        pass

    def end(self, transactionName: str):
        pass

    def fail(self, site: int):
        pass
    
    def recover(self, site: int):
        pass


    def __getLock(self, T: Transaction, x: str, lockType: str) -> bool:
        if lockType == "R":
            aquiredLock, blockingTransaction = self.lockTable.getReadLock()
        else:
            aquiredLock, blockingTransaction = self.lockTable.getWriteLock()

        if aquiredLock == None:
            self.conflictGraph[blockingTransaction].append(T)
            # TODO: run deadlock detection
            return False

        T.locks[x] = aquiredLock
        return True



    def __resolveDeadLock(self) -> bool: 
        pass

if __name__ == "__main__":

    TM = TransactionManager()

    for line in stdin:
        line = line.strip()
        if line == "":
            continue

        TM.runInstruction(line)
        TM.tick()

