"""More bug confirmations: IRQ/NMI stack-page and vector issues."""

import unittest
import test_shim


def make_mpu():
    mpu = test_shim.Shim6502()
    mpu.memory = 0x10000 * [0x00]  # zero instead of 0xAA so stack contents are clearer
    return mpu


class IRQNMITests(unittest.TestCase):

    def test_irq_reads_correct_vector(self):
        """IRQ vector is $FFFE/$FFFF; NMI is $FFFA/$FFFB."""
        mpu = make_mpu()
        mpu.memory[0xFFFA] = 0x11  # NMI vector low
        mpu.memory[0xFFFB] = 0x22  # NMI vector high  => $2211
        mpu.memory[0xFFFE] = 0x34  # IRQ vector low
        mpu.memory[0xFFFF] = 0x12  # IRQ vector high  => $1234
        mpu.pc = 0x0500
        mpu.sp = 0xFD
        mpu.mpu.irq()
        self.assertEqual(0x1234, mpu.pc,
                         "IRQ should jump to vector at $FFFE/$FFFF, got $%04x" % mpu.pc)

    def test_irq_push_uses_stack_page(self):
        """IRQ must push return address to $0100-$01FF, not to bare $SP in zero page."""
        mpu = make_mpu()
        mpu.memory[0xFFFE] = 0x34
        mpu.memory[0xFFFF] = 0x12
        mpu.pc = 0xBEEF
        mpu.sp = 0xFD
        mpu.mpu.irq()
        # pushed PC high should land at $01FD, low at $01FC
        self.assertEqual(0xBE, mpu.memory[0x01FD],
                         "IRQ should push PC high to $01FD (stack page), got %02x"
                         % mpu.memory[0x01FD])
        self.assertEqual(0xEF, mpu.memory[0x01FC],
                         "IRQ should push PC low to $01FC (stack page), got %02x"
                         % mpu.memory[0x01FC])

    def test_irq_sets_interrupt_disable(self):
        """IRQ entry must set the I flag so the handler isn't re-interrupted."""
        mpu = make_mpu()
        mpu.memory[0xFFFE] = 0x00
        mpu.memory[0xFFFF] = 0x80
        mpu.pc = 0x0500
        mpu.sp = 0xFD
        mpu.p &= ~mpu.INTERRUPT
        mpu.mpu.irq()
        self.assertEqual(mpu.INTERRUPT, mpu.p & mpu.INTERRUPT,
                         "IRQ entry should set the I flag")

    def test_nmi_push_uses_stack_page(self):
        mpu = make_mpu()
        mpu.memory[0xFFFA] = 0x34
        mpu.memory[0xFFFB] = 0x12
        mpu.pc = 0xBEEF
        mpu.sp = 0xFD
        mpu.mpu.nmi()
        self.assertEqual(0xBE, mpu.memory[0x01FD],
                         "NMI should push PC high to stack page, got %02x"
                         % mpu.memory[0x01FD])
        self.assertEqual(0xEF, mpu.memory[0x01FC],
                         "NMI should push PC low to stack page, got %02x"
                         % mpu.memory[0x01FC])


if __name__ == "__main__":
    unittest.main(verbosity=2)
