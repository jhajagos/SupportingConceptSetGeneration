import json
import unittest
import concept_set.llm as csl
import concept_set.base as cs
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

class TestLLM(unittest.TestCase):

    def setUp(self):
        with open("./config.json") as f:
            self.config = json.load(f)

    def test_connect_ollama_llm(self):

        llm_obj = csl.LLMCreateWrapper("ollama", "ollama_small_model", self.config, 0.1)

        r = llm_obj.invoke("I am an assistant which filters diagnosis codes")

        self.assertIsNotNone(r)  # add assertion here


    def test_connect_azure_openai_llm(self):

        llm_obj = csl.LLMCreateWrapper("azure_openai", None, self.config, 0.1)
        r = llm_obj.invoke("I am an assistant which filters diagnosis codes")


    def test_ccsr_filter(self):

        # llm_big = csl.LLMCreateWrapper("ollama", "ollama_medium_model", self.config, 0.1)

        llm_big = csl.LLMCreateWrapper("azure_openai", None, self.config, 0.1)
        #ccsr_obj = csl.CCSRWithFiltering(llm_big, "Find CCSR codes for Type 1 diabetes and Type 2 diabetes", "Filter the code list to include codes that are related to impairments of vision",  self.config, 50)
        ccsr_obj = csl.CCSRWithFiltering(llm_big, "Find CCSR codes for breast cancer",
                                         "Only include codes related to metastatic breast cancer and exlcude codes related to screening",
                                         self.config, 50)
        ccsr_obj.select_high_level_codes()

        cs.CompareCodedConceptSets(ccsr_obj.initial_high_level_codes, ccsr_obj.selected_high_level_codes).summary()

        ccsr_obj.retrieve_lower_level_codes()

        ccsr_obj.filter_lower_level_codes()

        for key in ccsr_obj.filtered_lower_level_codes:
            cs.CompareCodedConceptSets(ccsr_obj.retrieved_lower_level_codes[key], ccsr_obj.filtered_lower_level_codes[key]).summary()

        ccsr_obj.combine_codes()

        ccsr_obj.final_concept_set.history_summary()

        ccsr_obj.final_concept_set.to_csv("./output/ccsr_test_concept_set_generated.csv")

        with open("./output/ccsr_test_concept_set_generated.json", "w") as f:
            f.write(ccsr_obj.final_concept_set.to_json())


    def test_build_vector_store(self):

        document_list = csl.generate_icd10_code_list_to_load()
        hf_sentence_embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

        import glob
        if glob.glob(self.config["chroma_persist_directory"]+"/*"):
            pass
        else:
            vectordb_obj = Chroma.from_documents(document_list, hf_sentence_embedder,  persist_directory=self.config["chroma_persist_directory"])


    def test_vector_search(self):
        #llm_big = csl.LLMCreateWrapper("ollama", "ollama_medium_model", self.config, 0.1)

        llm_big = csl.LLMCreateWrapper("azure_openai", None, self.config, 0.1)
        hf_sentence_embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
        vectordb_obj = Chroma(persist_directory=self.config["chroma_persist_directory"], embedding_function=hf_sentence_embedder)

        filter_obj = csl.VectorSearchWithFilter(llm_big, vectordb_obj, "severe headaches or migraines",
                                                            "Filter codes to include those that describe headaches or migraines",
                                                            500)
        filter_obj.search_vector_db()
        filter_obj.filter_codes()

        cs.CompareCodedConceptSets(filter_obj.retrieved_codes, filter_obj.final_concept_set).summary()

        filter_obj.filter_codes_again("Filter codes to only include those that include cluster headaches")

        filter_obj.final_concept_set.history_summary()

        filter_obj.final_concept_set.summary()

        filter_obj.final_concept_set.to_csv("./output/vector_search_test_concept_set_generated.csv")

        with open("./output/vector_search_test_concept_set_generated.json", "w") as f:
            f.write(filter_obj.final_concept_set.to_json())



if __name__ == '__main__':
    unittest.main()
