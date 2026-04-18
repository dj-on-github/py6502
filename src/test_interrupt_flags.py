"""Tests for B flag and bit-5 semantics on interrupt push/pull paths.

Real 6502 hardware doesn't actually store B or bit-5 in the P register;
those bits are synthesized at push time based on what is doing the push:

  * PHP and BRK push with B=1 and bit-5=1 (software interrupts)
  * IRQ and NMI push with B=0 and bit-5=1 (hardware interrupts)
  * PLP and RTI restore the flag byte; what's pulled into B/bit-5
    positions is effectively a don't-care since the next push will
    overwrite them based on which instruction pushed.

This lets interrupt handlers distinguish IRQ/NMI from BRK by inspecting
bit 4 of the P value on the stack.  These tests lock in that behavior.
"""

import unittest
import test_shim


def make_mpu(variant="65C02"):
    mpu = test_shim.Shim6502(variant=variant)
    mpu.memory = 0x10000 * [0x00]
    return mpu


class PhpPushTests(unittest.TestCase):
    """PHP always pushes with B=1 and bit-5=1."""

    def test_php_pushes_break_and_unused_set(self):
        mpu = make_mpu()
        mpu.p = 0
        mpu.sp = 0xFF
        mpu.memory[0x0200] = 0x08   # PHP
        mpu.pc = 0x0200
        mpu.step()
        pushed = mpu.memory[0x01FF]
        self.assertEqual(0x30, pushed & 0x30,
                         "PHP must push with B=1 and bit-5=1; got $%02x"
                         % pushed)

    def test_php_preserves_other_flags_in_push(self):
        mpu = make_mpu()
        mpu.p = mpu.NEGATIVE | mpu.CARRY | mpu.ZERO
        mpu.sp = 0xFF
        mpu.memory[0x0200] = 0x08
        mpu.pc = 0x0200
        mpu.step()
        pushed = mpu.memory[0x01FF]
        self.assertEqual(mpu.NEGATIVE, pushed & mpu.NEGATIVE)
        self.assertEqual(mpu.CARRY, pushed & mpu.CARRY)
        self.assertEqual(mpu.ZERO, pushed & mpu.ZERO)
        self.assertEqual(mpu.BREAK, pushed & mpu.BREAK)
        self.assertEqual(mpu.UNUSED, pushed & mpu.UNUSED)

    def test_php_does_not_set_break_in_live_p(self):
        """PHP pushing with B=1 must not leak B into the live P register."""
        mpu = make_mpu()
        mpu.p = 0
        mpu.sp = 0xFF
        mpu.memory[0x0200] = 0x08
        mpu.pc = 0x0200
        mpu.step()
        self.assertEqual(0, mpu.p & mpu.BREAK)


class IrqNmiPushTests(unittest.TestCase):
    """IRQ/NMI push with B=0 and bit-5=1 so handlers can distinguish them
    from BRK."""

    def _do_irq(self, variant):
        mpu = make_mpu(variant)
        mpu.memory[0xFFFE] = 0x00
        mpu.memory[0xFFFF] = 0x80
        mpu.pc = 0x1234
        mpu.sp = 0xFF
        mpu.p = mpu.NEGATIVE | mpu.CARRY
        mpu.mpu.irq()
        return mpu

    def test_irq_pushes_break_clear_unused_set_65c02(self):
        mpu = self._do_irq("65C02")
        pushed = mpu.memory[0x01FD]
        self.assertEqual(0, pushed & mpu.BREAK,
                         "IRQ must push B=0; got P=$%02x" % pushed)
        self.assertEqual(mpu.UNUSED, pushed & mpu.UNUSED,
                         "IRQ must push bit-5=1; got P=$%02x" % pushed)

    def test_irq_pushes_break_clear_unused_set_nmos(self):
        mpu = self._do_irq("NMOS")
        pushed = mpu.memory[0x01FD]
        self.assertEqual(0, pushed & mpu.BREAK)
        self.assertEqual(mpu.UNUSED, pushed & mpu.UNUSED)

    def test_irq_clears_break_bit_even_if_live_p_has_it(self):
        mpu = make_mpu()
        mpu.p = mpu.BREAK | mpu.CARRY
        mpu.memory[0xFFFE] = 0x00
        mpu.memory[0xFFFF] = 0x80
        mpu.sp = 0xFF
        mpu.mpu.irq()
        pushed = mpu.memory[0x01FD]
        self.assertEqual(0, pushed & mpu.BREAK,
                         "IRQ must force B=0 in pushed P regardless of live P")

    def _do_nmi(self, variant):
        mpu = make_mpu(variant)
        mpu.memory[0xFFFA] = 0x00
        mpu.memory[0xFFFB] = 0x80
        mpu.pc = 0x1234
        mpu.sp = 0xFF
        mpu.p = mpu.NEGATIVE | mpu.CARRY
        mpu.mpu.nmi()
        return mpu

    def test_nmi_pushes_break_clear_unused_set(self):
        mpu = self._do_nmi("65C02")
        pushed = mpu.memory[0x01FD]
        self.assertEqual(0, pushed & mpu.BREAK)
        self.assertEqual(mpu.UNUSED, pushed & mpu.UNUSED)

    def test_irq_preserves_decimal_on_nmos(self):
        mpu = make_mpu("NMOS")
        mpu.p = mpu.DECIMAL
        mpu.memory[0xFFFE] = 0x00
        mpu.memory[0xFFFF] = 0x80
        mpu.sp = 0xFF
        mpu.mpu.irq()
        self.assertEqual(mpu.DECIMAL, mpu.p & mpu.DECIMAL,
                         "NMOS IRQ must preserve D")

    def test_irq_clears_decimal_on_65c02(self):
        mpu = make_mpu("65C02")
        mpu.p = mpu.DECIMAL
        mpu.memory[0xFFFE] = 0x00
        mpu.memory[0xFFFF] = 0x80
        mpu.sp = 0xFF
        mpu.mpu.irq()
        self.assertEqual(0, mpu.p & mpu.DECIMAL,
                         "65C02 IRQ must clear D")


class BrkPushTests(unittest.TestCase):
    """BRK pushes with B=1 and bit-5=1, but does not set B in the live P."""

    def test_brk_pushes_break_and_unused(self):
        mpu = make_mpu()
        mpu.memory[0xFFFE] = 0x00
        mpu.memory[0xFFFF] = 0x80
        mpu.p = 0
        mpu.sp = 0xFF
        mpu.memory[0x0200] = 0x00   # BRK
        mpu.pc = 0x0200
        mpu.step()
        pushed = mpu.memory[0x01FD]
        self.assertEqual(mpu.BREAK, pushed & mpu.BREAK)
        self.assertEqual(mpu.UNUSED, pushed & mpu.UNUSED)

    def test_brk_does_not_set_break_in_live_p(self):
        mpu = make_mpu()
        mpu.memory[0xFFFE] = 0x00
        mpu.memory[0xFFFF] = 0x80
        mpu.p = 0
        mpu.sp = 0xFF
        mpu.memory[0x0200] = 0x00
        mpu.pc = 0x0200
        mpu.step()
        self.assertEqual(0, mpu.p & mpu.BREAK,
                         "BRK must not leak B=1 into live P register")


class RtiRestoreTests(unittest.TestCase):
    """RTI restores the pulled flag byte faithfully with no post-hoc
    B/bit-5 force."""

    def _run_rti(self, pulled_flags):
        mpu = make_mpu()
        mpu.memory[0x0200] = 0x40   # RTI
        mpu.pc = 0x0200
        # Stack layout for RTI: SP+1 = flags, SP+2 = PCL, SP+3 = PCH
        mpu.sp = 0xFC
        mpu.memory[0x01FD] = pulled_flags
        mpu.memory[0x01FE] = 0x34
        mpu.memory[0x01FF] = 0x12
        mpu.step()
        return mpu

    def test_rti_restores_zero_flag_byte(self):
        mpu = self._run_rti(0x00)
        # In particular, B and UNUSED must NOT be force-set to 1.
        self.assertEqual(0x00, mpu.p)

    def test_rti_restores_full_flag_byte(self):
        mpu = self._run_rti(0xFF)
        self.assertEqual(0xFF, mpu.p)

    def test_rti_restores_typical_interrupt_frame(self):
        # Simulate an IRQ-pushed frame: B=0, UNUSED=1, plus ZERO set.
        pulled = mpu_flags_byte = 0x20 | 0x02   # UNUSED | ZERO, B clear
        mpu = self._run_rti(pulled)
        self.assertEqual(0, mpu.p & mpu.BREAK,
                         "RTI must preserve B=0 from the pulled value "
                         "(not force it high)")
        self.assertEqual(mpu.UNUSED, mpu.p & mpu.UNUSED)
        self.assertEqual(mpu.ZERO, mpu.p & mpu.ZERO)
        self.assertEqual(0x1234, mpu.pc)


class BrkRtiRoundTripTests(unittest.TestCase):
    """End-to-end: BRK then RTI restores the pushed flag byte."""

    def test_brk_then_rti_roundtrip_restores_pushed_p(self):
        mpu = make_mpu()
        # RTI at the BRK/IRQ vector
        mpu.memory[0xFFFE] = 0x00
        mpu.memory[0xFFFF] = 0x80
        mpu.memory[0x8000] = 0x40   # RTI

        mpu.p = mpu.NEGATIVE | mpu.CARRY
        mpu.sp = 0xFF
        mpu.memory[0x0200] = 0x00   # BRK
        mpu.pc = 0x0200

        mpu.step()   # BRK
        # Live P after BRK: I set, B NOT set.
        self.assertEqual(0, mpu.p & mpu.BREAK)
        self.assertEqual(mpu.INTERRUPT, mpu.p & mpu.INTERRUPT)
        self.assertEqual(0x8000, mpu.pc)

        mpu.step()   # RTI
        # The pushed P byte had B=1 and UNUSED=1 plus the pre-BRK flags.
        # RTI restores it faithfully.
        self.assertEqual(mpu.NEGATIVE, mpu.p & mpu.NEGATIVE)
        self.assertEqual(mpu.CARRY, mpu.p & mpu.CARRY)
        self.assertEqual(mpu.BREAK, mpu.p & mpu.BREAK,
                         "BRK pushed B=1; RTI must faithfully restore it")
        self.assertEqual(mpu.UNUSED, mpu.p & mpu.UNUSED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
