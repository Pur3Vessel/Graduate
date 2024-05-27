from abc import ABC

color_to_regs = {
    1: "ebx",
    2: "ecx",
    3: "edx",
    4: "edi",
    5: "esi"
}

color_to_xmm_regs = {
    1: "xmm2",
    2: "xmm3",
    3: "xmm4",
    4: "xmm5",
    5: "xmm6",
    6: "xmm7"
}


class LowIR(ABC):
    pass


class Label(LowIR):
    def __init__(self, label):
        self.label = label

    def __str__(self):
        return self.label + ":"


class Jump(LowIR):
    def __init__(self, label):
        self.label = label

    def __str__(self):
        return "jmp " + self.label


class Move(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "mov " + self.arg1 + ", " + self.arg2

class MoveSS(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "movss " + self.arg1 + ", " + self.arg2

class Neg(LowIR):
    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        return "neg" + self.arg