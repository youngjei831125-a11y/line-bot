import unittest

import time_guards


class TimeGuardTests(unittest.TestCase):
    def test_chinese_evening_ten_is_22_00(self):
        facts = time_guards.extract_time_facts("那我們就大概約晚上10點左右", "zh")

        self.assertEqual(facts[0]["canonical"], "22:00")
        self.assertEqual(facts[0]["thai"], "สี่ทุ่ม")

    def test_tonight_ten_is_22_00(self):
        facts = time_guards.extract_time_facts("今晚10點見", "zh")

        self.assertEqual(facts[0]["canonical"], "22:00")
        self.assertEqual(facts[0]["thai"], "สี่ทุ่ม")

    def test_wrong_thai_colloquial_time_is_rejected(self):
        facts = time_guards.extract_time_facts("那我們就大概約晚上10點左右", "zh")

        self.assertTrue(
            time_guards.translation_breaks_time_facts(
                "งั้นเรานัดกันประมาณสักสองทุ่มนะ",
                facts,
                "th",
            )
        )

    def test_correct_thai_colloquial_time_is_allowed(self):
        facts = time_guards.extract_time_facts("那我們就大概約晚上10點左右", "zh")

        self.assertFalse(
            time_guards.translation_breaks_time_facts(
                "งั้นเรานัดกันประมาณสี่ทุ่มนะ",
                facts,
                "th",
            )
        )


if __name__ == "__main__":
    unittest.main()
