import sim6502

class Shim6502(object):
    """Shim between the API expected by py65's MPU class and sim6502 class"""

    # processor flags
    NEGATIVE = 0x80
    OVERFLOW = 0x40
    UNUSED = 0x20
    BREAK = 0x10
    DECIMAL = 0x8
    INTERRUPT = 0x4
    ZERO = 0x2
    CARRY = 0x1

    def __init__(self):
        self.mpu = sim6502.sim6502()

    def step(self):
        self.mpu.execute()

    def reset(self):
        self.mpu.reset()

    @property
    def memory(self):
        return self._memory

    @memory.setter
    def memory(self, value):
        self.mpu.memory_map.InitializeMemory(0x0, value)
        self._memory = MemoryShim(self.mpu.memory_map)

    @property
    def p(self):
        return self.mpu.cc

    @p.setter
    def p(self, value):
        self.mpu.cc = value

    @property
    def x(self):
        return self.mpu.x

    @x.setter
    def x(self, value):
        self.mpu.x = value

    @property
    def y(self):
        return self.mpu.y

    @y.setter
    def y(self, value):
        self.mpu.y = value

    @property
    def sp(self):
        return self.mpu.sp

    @sp.setter
    def sp(self, value):
        self.mpu.sp = value

    @property
    def a(self):
        return self.mpu.a

    @a.setter
    def a(self, value):
        self.mpu.a = value

    @property
    def pc(self):
        return self.mpu.pc

    @pc.setter
    def pc(self, value):
        self.mpu.pc = value


class MemoryShim(object):
    def __init__(self, memory_map):
        self.memory_map = memory_map

    def __getitem__(self, item):
        return self.memory_map.Read(item)

    def __setitem__(self, item, value):
        # TODO: hack, bypasses tracing
        return self.memory_map._memory_map.__setitem__(item, value)

    def __len__(self):
        return len(self.memory_map._memory_map)

