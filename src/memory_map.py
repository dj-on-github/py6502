"""Memory map for 6502 address space."""

# Memory access modes
MODE_READ = 0
MODE_WRITE = 1
MODE_EXECUTE = 2

class TrapException(Exception):
    """May be raised by an interceptor on access to a memory address."""
    def __init__(self, address, access_mode):
        self.address = address
        self.access_mode = access_mode

    def __str__(self):
        return "Trap when accessing memory location $%X with mode %d" % (
            self.address, self.access_mode)


class MemoryMap(object):
    # Don't intercept accesses to uninitialized memory
    NONE_INTERCEPTOR = 0
    # Raise TrapException on read/execute access to uninitialized memory
    TRAP_INTERCEPTOR = 1

    def __init__(self, cpu, default_interceptor=NONE_INTERCEPTOR):
        # Pointer back to sim6502 object
        self.cpu = cpu

        # -1 represents an uninitialized memory address, which will optionally trap if accessed.
        self._memory_map = [-1] * 65536

        self.interceptors = {}

        if default_interceptor == self.NONE_INTERCEPTOR:
            self.default_interceptor = None
        elif default_interceptor == self.TRAP_INTERCEPTOR:
            self.default_interceptor = self.TrapInterceptor
        else:
            self.default_interceptor = default_interceptor

    def TrapInterceptor(self, address, access_mode, _):
        if self._memory_map[address] == -1 and (access_mode == MODE_READ or access_mode == MODE_EXECUTE):

            print self.cpu.show_state()
            print self.Dump(self.cpu.pc, 0x3)
            raise TrapException(address, access_mode)

    def InitializeMemory(self, address, data, interceptor=None):
        for idx, value in enumerate(data):
            # Bug: https://github.com/dj-on-github/py6502/issues/6
            # Fix this by choosing to skip assigning data from object_code if it is untouched. 
            #if value < 0 or value > 255:
            #    raise ValueError
            if (value >= 0 and value < 256):
                self._memory_map[address + idx] = value
            if interceptor:
                self.Intercept(address + idx, interceptor)

    def Intercept(self, address, interceptor):
        """Register interceptor for access to a memory address"""
        self.interceptors[address] = interceptor

    def Dump(self, address=0x0, length=0x10000):
        lines = []
        line = []
        for i, value in enumerate(self._memory_map[address:address+length]):
            if i % 16 == 0:
                line.append('$%04X :' % (address + i))
            if value == -1:
                line.append('--')
            else:
                line.append('%02X' % value)
            if (i + 1) % 16 == 0:
                lines.append(' '.join(line))
                line = []

        if line:
            lines.append(' '.join(line))

        return '\n'.join(lines)

    def _MaybeIntercept(self, address, access_mode):
        try:
            interceptor = self.interceptors[address]
        except KeyError:
            interceptor = self.default_interceptor

        # May raise TrapException
        if interceptor:
            if access_mode == MODE_WRITE:
                value = self._memory_map[address]
            else:
                value = None
            interceptor(address, access_mode, value)

    # TODO: record access trace records

    def Read(self, address, trace=True):
        self._MaybeIntercept(address, MODE_READ)
        return self._memory_map[address]

    def Write(self, address, value, trace=True):
        self._memory_map[address] = value
        self._MaybeIntercept(address, MODE_WRITE)

    def Execute(self, address, trace=True):
        self._MaybeIntercept(address, MODE_EXECUTE)
        return self._memory_map[address]


