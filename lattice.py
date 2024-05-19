from enum import Enum


class ConstantLatticeElement(Enum):
    HIGH = "T"
    LOW = "⊥"


class ConstantLattice:
    def __init__(self):
        self.sl = {}

    def init_value(self, value):
        self.sl[value] = ConstantLatticeElement.HIGH

    def meet(self, value1, value2):
        if type(value1) != int and not isinstance(value1, ConstantLatticeElement) and type(value1) != bool:
            if value1 not in self.sl:
                value1 = ConstantLatticeElement.LOW
            else:
                value1 = self.sl[value1]
        if type(value2) != int and not isinstance(value2, ConstantLatticeElement) and type(value2) != bool:
            if value2 not in self.sl:
                value2 = ConstantLatticeElement.LOW
            else:
                value2 = self.sl[value2]

        if value1 == value2:
            return value1

        if value1 == ConstantLatticeElement.HIGH:
            return value2
        if value2 == ConstantLatticeElement.HIGH:
            return value1
        return ConstantLatticeElement.LOW

    def __str__(self):
        s = ""
        for key, val in self.sl.items():
            s += key + ": " + str(val) + "\n"
        return s

