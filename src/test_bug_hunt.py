"""Targeted tests to confirm suspected bugs in sim6502."""

import sys
import unittest
import test_shim


def make_mpu():
    mpu = test_shim.Shim6502()
    mpu.memory = 0x10000 * [0xAA]
    return mpu


def write(mem, addr, data):
    mem[addr:addr + len(data)] = list(data)


class BugHuntTests(unittest.TestCase):

    # --- BCD ADC precedence bug ---

    def test_bcd_adc_19_plus_19(self):
        """BCD: 0x19 + 0x19 = 0x38, C=0.  Catches the << vs + precedence bug."""
        mpu = make_mpu()
        mpu.p |= mpu.DECIMAL
        mpu.p &= ~mpu.CARRY
        mpu.a = 0x19
        write(mpu.memory, 0x0000, (0x69, 0x19))  # ADC #$19
        mpu.step()
        self.assertEqual(0x38, mpu.a, "BCD 19+19 should be 38, got %02x" % mpu.a)
        self.assertEqual(0, mpu.p & mpu.CARRY)

    def test_bcd_adc_50_plus_50(self):
        """BCD: 0x50 + 0x50 = 0x00, C=1 (carry out of high nibble)."""
        mpu = make_mpu()
        mpu.p |= mpu.DECIMAL
        mpu.p &= ~mpu.CARRY
        mpu.a = 0x50
        write(mpu.memory, 0x0000, (0x69, 0x50))
        mpu.step()
        self.assertEqual(0x00, mpu.a)
        self.assertEqual(mpu.CARRY, mpu.p & mpu.CARRY,
                         "BCD 50+50 should set carry")

    # --- Zeropage indexed indirect X high-byte wrap ---

    def test_zpix_high_byte_wraps_in_zeropage(self):
        """LDA ($FF,X) with X=0: low byte from $FF, high byte from $00.
        Current code reads $100 for the high byte, which reads past zp."""
        mpu = make_mpu()
        mpu.x = 0
        mpu.a = 0
        # pointer in zeropage: $FF=0x34, $00=0x12 => target $1234
        mpu.memory[0x00FF] = 0x34
        mpu.memory[0x0000] = 0x12
        mpu.memory[0x0100] = 0xDE  # wrong target if bug present
        mpu.memory[0x1234] = 0x42  # correct target value
        mpu.memory[0xDE34] = 0x99  # what we'd hit with the bug
        write(mpu.memory, 0x0200, (0xA1, 0xFF))  # LDA ($FF,X)
        mpu.pc = 0x0200
        mpu.step()
        self.assertEqual(0x42, mpu.a,
                         "Got %02x; zp indexed indirect X should wrap high byte in zp" % mpu.a)

    def test_zpi_high_byte_wraps_in_zeropage(self):
        """LDA ($FF) [65C02 zp indirect]: low byte $FF, high byte $00."""
        mpu = make_mpu()
        mpu.memory[0x00FF] = 0x34
        mpu.memory[0x0000] = 0x12
        mpu.memory[0x0100] = 0xDE
        mpu.memory[0x1234] = 0x77
        mpu.memory[0xDE34] = 0x88
        write(mpu.memory, 0x0200, (0xB2, 0xFF))  # LDA ($FF) - opcode 0xB2
        mpu.pc = 0x0200
        mpu.step()
        self.assertEqual(0x77, mpu.a)

    # --- PLA/PLX/PLY flag-setting ---

    def test_pla_sets_zero_flag(self):
        mpu = make_mpu()
        mpu.sp = 0xFE
        mpu.memory[0x01FF] = 0x00
        mpu.a = 0xFF
        mpu.p &= ~mpu.ZERO
        write(mpu.memory, 0x0200, (0x68,))  # PLA
        mpu.pc = 0x0200
        mpu.step()
        self.assertEqual(0x00, mpu.a)
        self.assertEqual(mpu.ZERO, mpu.p & mpu.ZERO,
                         "PLA of 0x00 should set Z")

    def test_pla_sets_negative_flag(self):
        mpu = make_mpu()
        mpu.sp = 0xFE
        mpu.memory[0x01FF] = 0x80
        mpu.a = 0x00
        mpu.p &= ~mpu.NEGATIVE
        write(mpu.memory, 0x0200, (0x68,))  # PLA
        mpu.pc = 0x0200
        mpu.step()
        self.assertEqual(0x80, mpu.a)
        self.assertEqual(mpu.NEGATIVE, mpu.p & mpu.NEGATIVE,
                         "PLA of 0x80 should set N")

    # --- absolute,X out-of-range (mod 16-bit) ---

    def test_absolute_x_wraps_at_16_bits(self):
        """LDA $FFFF,X with X=1 should address $0000, not raise."""
        mpu = make_mpu()
        mpu.x = 1
        mpu.memory[0x0000] = 0x5A
        write(mpu.memory, 0x0200, (0xBD, 0xFF, 0xFF))  # LDA $FFFF,X
        mpu.pc = 0x0200
        try:
            mpu.step()
        except IndexError as e:
            self.fail("absolute,X addressing should wrap at 16 bits, got IndexError: %s" % e)
        self.assertEqual(0x5A, mpu.a)


if __name__ == "__main__":
    unittest.main(verbosity=2)
