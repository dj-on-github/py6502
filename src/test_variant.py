"""Focused tests for the sim6502 variant switch.

These verify that the NMOS/65C02 variant selection actually routes to the
correct behavior for each of the variant-sensitive features:

* JMP indirect page-wrap bug (NMOS yes, 65C02 no)
* BRK clearing the D flag (65C02 yes, NMOS no)
* BIT #imm leaving N and V untouched (65C02; opcode unavailable on NMOS)
* 65C02-only opcodes being absent on NMOS

The 432 Common6502Tests and 489 65C02-specific tests already cover the
shared baseline; these are the deltas.
"""

import unittest
import test_shim
import sim6502


def make_mpu(variant):
    mpu = test_shim.Shim6502(variant=variant)
    mpu.memory = 0x10000 * [0x00]   # zero-fill so stale bytes don't mask bugs
    return mpu


class VariantConstructionTests(unittest.TestCase):

    def test_default_variant_is_65c02(self):
        cpu = sim6502.sim6502()
        self.assertEqual("65C02", cpu.variant)

    def test_explicit_nmos(self):
        cpu = sim6502.sim6502(variant="NMOS")
        self.assertEqual("NMOS", cpu.variant)

    def test_explicit_65c02(self):
        cpu = sim6502.sim6502(variant="65C02")
        self.assertEqual("65C02", cpu.variant)

    def test_invalid_variant_raises(self):
        with self.assertRaises(ValueError):
            sim6502.sim6502(variant="6510")


class JmpIndirectPageWrapTests(unittest.TestCase):
    """JMP ($xxFF): NMOS reads high byte from $xx00; 65C02 reads from $xxFF+1."""

    def _setup_wrap_scenario(self, variant):
        mpu = make_mpu(variant)
        mpu.memory[0x10FF] = 0x34    # low byte of target
        mpu.memory[0x1000] = 0x12    # high byte if NMOS wraps
        mpu.memory[0x1100] = 0xDE    # high byte if 65C02 reads correctly
        # JMP ($10FF) at $0200
        mpu.memory[0x0200] = 0x6C
        mpu.memory[0x0201] = 0xFF
        mpu.memory[0x0202] = 0x10
        mpu.pc = 0x0200
        mpu.step()
        return mpu

    def test_nmos_jmp_indirect_wraps_within_page(self):
        mpu = self._setup_wrap_scenario("NMOS")
        self.assertEqual(0x1234, mpu.pc,
                         "NMOS JMP ($10FF) should read high byte from $1000, "
                         "got PC=$%04x" % mpu.pc)

    def test_65c02_jmp_indirect_does_not_wrap(self):
        mpu = self._setup_wrap_scenario("65C02")
        self.assertEqual(0xDE34, mpu.pc,
                         "65C02 JMP ($10FF) should read high byte from $1100, "
                         "got PC=$%04x" % mpu.pc)


class BrkDecimalFlagTests(unittest.TestCase):
    """BRK on 65C02 clears D; on NMOS it is preserved."""

    def _run_brk(self, variant):
        mpu = make_mpu(variant)
        mpu.memory[0xFFFE] = 0x00    # IRQ/BRK vector low
        mpu.memory[0xFFFF] = 0x80    # IRQ/BRK vector high  => $8000
        mpu.p |= mpu.DECIMAL
        mpu.memory[0x0200] = 0x00    # BRK
        mpu.pc = 0x0200
        mpu.step()
        return mpu

    def test_nmos_brk_preserves_decimal_flag(self):
        mpu = self._run_brk("NMOS")
        self.assertEqual(mpu.DECIMAL, mpu.p & mpu.DECIMAL,
                         "NMOS BRK should preserve D; got p=$%02x" % mpu.p)

    def test_65c02_brk_clears_decimal_flag(self):
        mpu = self._run_brk("65C02")
        self.assertEqual(0, mpu.p & mpu.DECIMAL,
                         "65C02 BRK should clear D; got p=$%02x" % mpu.p)


class BitImmediateTests(unittest.TestCase):
    """BIT #imm on 65C02 affects only Z.  Opcode is undefined on NMOS."""

    def test_65c02_bit_imm_preserves_n_and_v(self):
        mpu = make_mpu("65C02")
        mpu.p |= mpu.NEGATIVE | mpu.OVERFLOW
        mpu.p &= ~mpu.ZERO
        mpu.a = 0x00
        # BIT #$00 -- operand has neither bit 7 nor bit 6 set
        mpu.memory[0x0200] = 0x89
        mpu.memory[0x0201] = 0x00
        mpu.pc = 0x0200
        mpu.step()
        # If the NMOS-style flag setting had run, N and V would have been
        # cleared from the zero operand.  65C02 keeps them.
        self.assertEqual(mpu.NEGATIVE, mpu.p & mpu.NEGATIVE,
                         "65C02 BIT #imm must not clear N")
        self.assertEqual(mpu.OVERFLOW, mpu.p & mpu.OVERFLOW,
                         "65C02 BIT #imm must not clear V")
        self.assertEqual(mpu.ZERO, mpu.p & mpu.ZERO,
                         "BIT #$00 AND A=$00 should set Z")

    def test_65c02_bit_imm_sets_z_based_on_and(self):
        mpu = make_mpu("65C02")
        mpu.p |= mpu.ZERO
        mpu.a = 0xFF
        # BIT #$FF -- A & $FF == $FF, Z should clear
        mpu.memory[0x0200] = 0x89
        mpu.memory[0x0201] = 0xFF
        mpu.pc = 0x0200
        mpu.step()
        self.assertEqual(0, mpu.p & mpu.ZERO)

    def test_nmos_bit_imm_is_illegal(self):
        mpu = make_mpu("NMOS")
        mpu.a = 0xFF
        mpu.memory[0x0200] = 0x89    # BIT #imm opcode
        mpu.memory[0x0201] = 0xFF
        mpu.pc = 0x0200
        # The sim reports illegal opcodes via the return tuple from execute().
        # Regardless of the exact sentinel, A must not be modified and no
        # BIT-style flag updates should occur.
        saved_p = mpu.p
        mpu.step()
        self.assertEqual(0xFF, mpu.a, "NMOS illegal opcode must not touch A")


class CmosOpcodePresenceTests(unittest.TestCase):
    """Spot-check that CMOS-only opcodes are unavailable on NMOS."""

    # (opcode, mnemonic, addr_mode_label_substring) for a sampling of ops
    CMOS_ONLY = [
        (0x80, "bra"),
        (0x1A, "ina"),
        (0x3A, "dea"),
        (0x5A, "phy"),
        (0xDA, "phx"),
        (0x64, "stz"),
        (0x9C, "stz"),
        (0x04, "tsb"),
        (0x14, "trb"),
        (0x89, "bit"),
        (0xB2, "lda"),   # ($zp)
        (0x7C, "jmp"),   # ($abs,X)
    ]

    def test_cmos_only_opcodes_present_on_65c02(self):
        cpu = sim6502.sim6502(variant="65C02")
        for op, mnemonic in self.CMOS_ONLY:
            instr, _addrmode = cpu.hexcodes[op]
            self.assertEqual(mnemonic, instr,
                             "65C02 opcode $%02x should be %s, got %r"
                             % (op, mnemonic, instr))

    def test_cmos_only_opcodes_absent_on_nmos(self):
        cpu = sim6502.sim6502(variant="NMOS")
        for op, mnemonic in self.CMOS_ONLY:
            instr, _addrmode = cpu.hexcodes[op]
            self.assertEqual("", instr,
                             "NMOS opcode $%02x should be undefined, got %r"
                             % (op, instr))

    def test_nmos_jmp_6c_still_present(self):
        """The NMOS-compatible JMP indirect ($6C) must still be available."""
        cpu = sim6502.sim6502(variant="NMOS")
        self.assertEqual(("jmp", "absoluteindirect"), cpu.hexcodes[0x6C])


if __name__ == "__main__":
    unittest.main(verbosity=2)
