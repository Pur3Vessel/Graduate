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


class MoveZX(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "movzx " + self.arg1 + ", " + self.arg2


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
        return "neg " + self.arg


class Not(LowIR):
    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        return "not " + self.arg


class Xorps(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "xorps " + self.arg1 + ", " + self.arg2


class Xor(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "xor " + self.arg1 + ", " + self.arg2


class Return(LowIR):
    def __str__(self):
        return "ret"


class JumpEqual(LowIR):
    def __init__(self, label):
        self.label = label

    def __str__(self):
        return "je " + self.label


class Cmp(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "cmp " + self.arg1 + ", " + self.arg2


class Comiss(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "comiss " + self.arg1 + ", " + self.arg2


class Add(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "add " + self.arg1 + ", " + self.arg2


class Addss(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "addss " + self.arg1 + ", " + self.arg2


class Sub(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "sub " + self.arg1 + ", " + self.arg2


class Subss(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "subss " + self.arg1 + ", " + self.arg2


class Mulss(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "mulss " + self.arg1 + ", " + self.arg2


class Divss(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "divss " + self.arg1 + ", " + self.arg2


class Imul(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "imul " + self.arg1 + ", " + self.arg2


class And(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "and " + self.arg1 + ", " + self.arg2


class Or(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "and " + self.arg1 + ", " + self.arg2


class Setg(LowIR):
    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        return "setg " + self.arg


class Setne(LowIR):
    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        return "setne " + self.arg


class Sete(LowIR):
    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        return "sete " + self.arg


class Setge(LowIR):
    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        return "setge " + self.arg


class Setl(LowIR):
    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        return "setl " + self.arg


class Setle(LowIR):
    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        return "setle " + self.arg


class Cvtsi2ss(LowIR):
    def __init__(self, arg1, arg2):
        self.arg1 = arg1
        self.arg2 = arg2

    def __str__(self):
        return "cvtsi2ss " + self.arg1 + ", " + self.arg2
