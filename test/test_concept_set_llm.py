import unittest
import json
import concept_set_llm as csl

class TestLLM(unittest.TestCase):

    def setUp(self):
        with open("./config.json") as f:
            self.config = json.load(f)

    def test_connect_llm(self):

        llm_obj = csl.LLMCreateWrapper("ollama", "ollama_small_model", self.config, 0.1)

        r = llm_obj.invoke("I am an assistant to help filter ICD10CM codes")

        self.assertIsNotNone(r)  # add assertion here


if __name__ == '__main__':
    unittest.main()
