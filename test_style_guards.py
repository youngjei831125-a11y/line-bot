import unittest

import style_guards


class StyleGuardTests(unittest.TestCase):
    def test_detects_chat_style_hints_for_current_example(self):
        facts = style_guards.extract_style_facts(
            "你們可以先去！我晚一點點到！我在吃東西",
            "zh",
            "th",
        )

        sources = {fact["source"] for fact in facts}
        self.assertIn("你們", sources)
        self.assertIn("你們可以先去", sources)
        self.assertIn("我晚一點點到", sources)
        self.assertIn("吃東西", sources)

    def test_rejects_awkward_translation_from_screenshot(self):
        facts = style_guards.extract_style_facts(
            "你們可以先去！我晚一點點到！我在吃東西",
            "zh",
            "th",
        )

        self.assertTrue(
            style_guards.translation_breaks_style_facts(
                "พวกเธอไปก่อนได้เลย! เดี๋ยวเราตามไปทีหลังนิดหน่อย! ตอนนี้เรากำลังกินข้าวอยู่",
                facts,
            )
        )

    def test_allows_more_natural_thai_chat_translation(self):
        facts = style_guards.extract_style_facts(
            "你們可以先去！我晚一點點到！我在吃東西",
            "zh",
            "th",
        )

        self.assertFalse(
            style_guards.translation_breaks_style_facts(
                "ไปกันก่อนได้เลย เดี๋ยวเราไปถึงช้านิดนึง ตอนนี้กำลังกินอะไรอยู่",
                facts,
            )
        )


if __name__ == "__main__":
    unittest.main()
