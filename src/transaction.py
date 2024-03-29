from building import Building
from enum import IntEnum, unique

@unique
class TransactionType(IntEnum):
    MANUAL = 1
    BUY    = 2
    SELL   = 3
    INCOME = 4
    GIVEN_LOAN = 5
    TAKEN_LOAN = 6

class Transaction:
    def __init__(self, ty, timestamp, *, comment=None, amount=None, buildings=None):
        if ty in (TransactionType.MANUAL, TransactionType.GIVEN_LOAN, TransactionType.TAKEN_LOAN):
            assert comment != None, "Comment on manual transaction must not be None"
            assert amount != None, "Amount on manual transaction must not be None"
        else:
            assert buildings != None, "Buildings type on auto transaction must not be None"

        self.amount = amount
        self.comment = comment
        self.trans_type = ty
        self.buildings = buildings
        self.timestamp = timestamp
    
    def compute_amount(self) -> int:
        if self.trans_type in (TransactionType.MANUAL, TransactionType.TAKEN_LOAN):
            return self.amount
        elif self.trans_type == TransactionType.GIVEN_LOAN:
            return -self.amount
        elif self.trans_type == TransactionType.BUY:
            return -sum([building.cost() for building in self.buildings])
        elif self.trans_type == TransactionType.SELL:
            return sum([building.cost() for building in self.buildings])
            
    def compute_comment(self):
        if self.trans_type == TransactionType.MANUAL:
            return self.comment
        elif self.trans_type == TransactionType.TAKEN_LOAN:
            return f"Loan from {self.comment}"
        elif self.trans_type == TransactionType.GIVEN_LOAN:
            return f"Loan to {self.comment}"
        elif self.trans_type == TransactionType.BUY:
            return f"Bought {len(self.buildings)}x {self.buildings[0].name()}"
        elif self.trans_type == TransactionType.SELL:
            return f"Sold {len(self.buildings)}x {self.buildings[0].name()}"