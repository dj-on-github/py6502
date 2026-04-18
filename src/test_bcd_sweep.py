"""Exhaustive BCD ADC/SBC sweep.

For every valid BCD operand pair (00-99 x 00-99) and both values of the
carry flag, run one ADC #imm and one SBC #imm and compare the result byte
and carry flag against a simple reference implementation.

This is the kind of exhaustive sweep you'd use against an RTL implementation
to pin down BCD-mode arithmetic end-to-end.  40 000 cases for each of ADC
and SBC = 80 000 simulator steps, runs in well under a minute.

What is NOT tested here:
  * Invalid BCD inputs (the simulator raises ValueError on those; covering
    that would require a separate test with try/except structure).
  * N, V, Z flag fidelity -- NMOS computes these from the pre-adjust binary
    result, 65C02 from the decimal-correct result.  The simulator uses a
    single code path and matches neither exactly; a separate, variant-aware
    sweep should cover those flags once the sim is fixed.  For now the
    sweep focuses on the two bits that practical BCD code actually depends
    on: the result byte and the carry-out (used for multi-byte BCD
    arithmetic).
"""

import unittest
import test_shim


# Valid BCD byte values: each nibble in 0..9.  Exactly 100 of them.
BCD_VALUES = tuple(
    (tens << 4) | ones
    for tens in range(10)
    for ones in range(10)
)


def _to_decimal(bcd_byte):
    """Convert a valid BCD byte (each nibble 0-9) to its decimal value."""
    return (bcd_byte >> 4) * 10 + (bcd_byte & 0xF)


def _to_bcd(decimal_value):
    """Convert 0..99 to its BCD byte representation."""
    assert 0 <= decimal_value <= 99
    return ((decimal_value // 10) << 4) | (decimal_value % 10)


def bcd_adc_reference(a, m, carry_in):
    """Reference BCD ADC.

    Given BCD-valid A and M and a carry-in (0 or 1), returns
    (result_byte, carry_out) using the defined behavior: "correct" decimal
    arithmetic with carry-out set when the true sum is >= 100.
    """
    total = _to_decimal(a) + _to_decimal(m) + carry_in
    carry_out = 1 if total >= 100 else 0
    return _to_bcd(total % 100), carry_out


def bcd_sbc_reference(a, m, carry_in):
    """Reference BCD SBC.

    6502 SBC computes A - M - (1 - C).  Carry is cleared on borrow, set
    otherwise -- i.e. C stays 1 if A >= M + (1 - C_in).
    """
    diff = _to_decimal(a) - _to_decimal(m) - (1 - carry_in)
    carry_out = 0 if diff < 0 else 1
    # Python's % already wraps negatives into [0, 100) which matches the
    # two-digit BCD wrap behavior we want.
    return _to_bcd(diff % 100), carry_out


def make_mpu(variant):
    mpu = test_shim.Shim6502(variant=variant)
    mpu.memory = 0x10000 * [0x00]
    return mpu


def _fmt_failure(failure):
    if len(failure) != 7:
        return repr(failure)
    a, m, cin, er, ec, gr, gc = failure
    return ("  A=%02x M=%02x Cin=%d  expected: result=%02x C=%d"
            "  got: result=%02x C=%d"
            % (a, m, cin, er, ec, gr, gc))


class BcdAdcSweep(unittest.TestCase):

    def _sweep(self, variant):
        mpu = make_mpu(variant)
        failures = []
        for a in BCD_VALUES:
            for m in BCD_VALUES:
                for cin in (0, 1):
                    # Set up fresh state for each case.
                    mpu.p = mpu.DECIMAL | (mpu.CARRY if cin else 0)
                    mpu.a = a
                    # $0200: ADC #imm
                    mpu.memory[0x0200] = 0x69
                    mpu.memory[0x0201] = m
                    mpu.pc = 0x0200
                    mpu.step()

                    exp_result, exp_cout = bcd_adc_reference(a, m, cin)
                    got_result = mpu.a
                    got_cout = 1 if (mpu.p & mpu.CARRY) else 0

                    if got_result != exp_result or got_cout != exp_cout:
                        failures.append(
                            (a, m, cin, exp_result, exp_cout,
                             got_result, got_cout))
                        if len(failures) > 20:
                            failures.append(("...", "more suppressed"))
                            return failures
        return failures

    def test_bcd_adc_all_pairs_65c02(self):
        failures = self._sweep("65C02")
        if failures:
            self.fail("65C02 BCD ADC mismatches (%d):\n%s"
                      % (len(failures),
                         "\n".join(_fmt_failure(f) for f in failures)))

    def test_bcd_adc_all_pairs_nmos(self):
        failures = self._sweep("NMOS")
        if failures:
            self.fail("NMOS BCD ADC mismatches (%d):\n%s"
                      % (len(failures),
                         "\n".join(_fmt_failure(f) for f in failures)))


class BcdSbcSweep(unittest.TestCase):

    def _sweep(self, variant):
        mpu = make_mpu(variant)
        failures = []
        for a in BCD_VALUES:
            for m in BCD_VALUES:
                for cin in (0, 1):
                    mpu.p = mpu.DECIMAL | (mpu.CARRY if cin else 0)
                    mpu.a = a
                    # $0200: SBC #imm
                    mpu.memory[0x0200] = 0xE9
                    mpu.memory[0x0201] = m
                    mpu.pc = 0x0200
                    mpu.step()

                    exp_result, exp_cout = bcd_sbc_reference(a, m, cin)
                    got_result = mpu.a
                    got_cout = 1 if (mpu.p & mpu.CARRY) else 0

                    if got_result != exp_result or got_cout != exp_cout:
                        failures.append(
                            (a, m, cin, exp_result, exp_cout,
                             got_result, got_cout))
                        if len(failures) > 20:
                            failures.append(("...", "more suppressed"))
                            return failures
        return failures

    def test_bcd_sbc_all_pairs_65c02(self):
        failures = self._sweep("65C02")
        if failures:
            self.fail("65C02 BCD SBC mismatches (%d):\n%s"
                      % (len(failures),
                         "\n".join(_fmt_failure(f) for f in failures)))

    def test_bcd_sbc_all_pairs_nmos(self):
        failures = self._sweep("NMOS")
        if failures:
            self.fail("NMOS BCD SBC mismatches (%d):\n%s"
                      % (len(failures),
                         "\n".join(_fmt_failure(f) for f in failures)))


class BcdReferenceSanity(unittest.TestCase):
    """Spot-check the reference functions so a bug in them isn't
    masquerading as the sim being correct."""

    def test_ref_add_trivial(self):
        self.assertEqual((0x19, 0), bcd_adc_reference(0x10, 0x09, 0))

    def test_ref_add_carry_out(self):
        self.assertEqual((0x00, 1), bcd_adc_reference(0x50, 0x50, 0))
        self.assertEqual((0x01, 1), bcd_adc_reference(0x50, 0x50, 1))

    def test_ref_add_with_cin(self):
        self.assertEqual((0x38, 0), bcd_adc_reference(0x19, 0x19, 0))
        self.assertEqual((0x39, 0), bcd_adc_reference(0x19, 0x19, 1))

    def test_ref_sub_trivial(self):
        # 20 - 10 with C=1 => 10, no borrow
        self.assertEqual((0x10, 1), bcd_sbc_reference(0x20, 0x10, 1))

    def test_ref_sub_borrow(self):
        # 10 - 20 => wraps to 90 with borrow (C=0 out)
        self.assertEqual((0x90, 0), bcd_sbc_reference(0x10, 0x20, 1))

    def test_ref_sub_with_cin_zero(self):
        # 20 - 10 - 1 = 9
        self.assertEqual((0x09, 1), bcd_sbc_reference(0x20, 0x10, 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
