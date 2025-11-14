from pydantic import BaseModel, Field
from typing import List, Optional
import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.documents import Document
import json

import concept_set
from umls import get_code_source_information
from concept_set import CodedConceptSet, CodedConcept, CodedConceptSetChange

class Code(BaseModel):
    code: str = Field(description="code identifier")
    description: str = Field(description="a human readable description of the code")
    vocabulary: Optional[str] = Field(description="Coding system such as ICD10CM or CCSR")


class CodeList(BaseModel):
    codes: List[Code] = Field(default_factory=list, description="A list of codes")


class CodeWithReason(Code):
    selected: bool = Field(description="whether the code was selected by the LLM to be included in the final code set")
    reason: str = Field(description="explain the reason for adding or remove the code")


class CodeWithReasonList(BaseModel):
    codes: List[CodeWithReason] = Field(description="A list of codes")


class LLMCreateWrapper(object):
    def __init__(self, llm_type, model_type, llm_config, temperature=0.1):
        if model_type in llm_config:
            named_model_type = llm_config[model_type]
        else:
            named_model_type = model_type

        if llm_type == "ollama":
            self.llm = ChatOllama(
                model=named_model_type,  # or whatever model you have pulled
                base_url=llm_config["ollama_server_url"],  # default Ollama URL
                temperature=temperature
            )

    def invoke(self, prompt):
        return self.llm.invoke(prompt)

    def return_llm(self):
        return self.llm


class CodeSelectionAndFiltering(object):
    def __init__(self, llm, selection_prompt, filter_prompt, config_dict,  chunk_size=15, default_high_level_vocabulary=None, default_low_level_vocabulary=None):
        self.llm = llm
        self.selection_prompt = selection_prompt
        self.filter_prompt = filter_prompt

        self.chunk_size = chunk_size

        self.selected_high_level_code = {}
        self.retrieved_lower_level_codes = {}

        self.filtered_lower_level_codes = {}

        self.concept_set = None
        self.additional_codes = {}
        self.included_additional_codes = {}
        self.excluded_additional_codes = {}

        self.config_dict = config_dict
        self.final_concept_set = None

        self.default_high_level_vocabulary = default_high_level_vocabulary
        self.default_low_level_vocabulary = default_low_level_vocabulary


        self.statuses = {0: "not_started",
                         1: "select_high_level_codes",
                         2: "retrieve_lower_level_codes",
                         3: "filter_lower_level_codes",
                         4: "combine_codes"}

        self.status = 0

    def select_high_level_codes(self):
        pass

    def retrieve_lower_level_codes(self):
        pass

    def filter_lower_level_codes(self):
        pass

    def combine_codes(self):
        pass


class CCSRWithFiltering(CodeSelectionAndFiltering):

    def select_high_level_codes(self):

        self.default_high_level_vocabulary = "CCSR_ICD10CM"
        self.default_low_level_vocabulary = "ICD10CM"

        ccsr_path = self.config_dict["ccsr_path"]
        if self.status == 0:
            self.selected_high_level_code = self.llm.invoke(self.selection_prompt)
            ccsr_df  = pd.read_csv(ccsr_path)

            code_list = []
            for row_dict in ccsr_df.to_dict("records"):
                code_list += [CodedConcept(row_dict["code"], "CCSR_ICD10CM", row_dict["description"])]

            full_ccsr_cs_obj = CodedConceptSet("CCSR_ICD10CM", code_list)

            self.initial_high_level_codes = full_ccsr_cs_obj

            filtered_ccsr_code_list = filter_concept_set_with_llm(full_ccsr_cs_obj, self.llm.return_llm(), self.selection_prompt, chunk_size=50, default_vocabulary=self.default_high_level_vocabulary)

            self.selected_high_level_codes = CodedConceptSet(f"prompt='{self.selection_prompt}'", filtered_ccsr_code_list)

            self.status = 1
        else:
            raise Exception("Code selection already started")

    def retrieve_lower_level_codes(self):

        if self.status == 1:
            for code in self.selected_high_level_codes:
                ccsr_code = code.code
                concepts_df_to_concept_set = get_df_icd10_codes_from_ccsr(ccsr_code, self.config_dict["umls_api_key"])

                cs_ccsr = concept_set.concepts_df_to_concept_set(concepts_df_to_concept_set, f"CCSR_ICD10CM_{ccsr_code}")
                self.retrieved_lower_level_codes[ccsr_code] = cs_ccsr

            self.status = 2
        else:
            raise Exception("High level codes not selected yet")


    def filter_lower_level_codes(self):

        if self.status == 2:
            for key in self.retrieved_lower_level_codes:
                filtered_code_list = filter_concept_set_with_llm(self.retrieved_lower_level_codes[key], self.llm.return_llm(), self.filter_prompt, chunk_size=self.chunk_size, default_vocabulary="ICD10CM")
                filtered_codes = CodedConceptSet(f"{key}|prompt='{self.filter_prompt}'", filtered_code_list)
                self.filtered_lower_level_codes[key] = filtered_codes
            self.status = 3
        else:
            raise Exception("Lower level codes not retrieved yet")

    def combine_codes(self):

        if self.status == 3:
            self.final_concept_set = CodedConceptSet("combined_codes", [])

            for key in self.filtered_lower_level_codes:
                self.final_concept_set.register_change(CodedConceptSetChange(list(self.filtered_lower_level_codes[key]), [], None, change_type=key))

        else:
            raise Exception("Lower level codes not filtered yet")



class VectorSearchWithFilter(object):

    def __init__(self, llm, vector_db, search_prompt, filter_prompt, search_size, chunk_size=15,  default_vocabulary=None):
        self.llm = llm
        self.vector_db = vector_db
        self.search_prompt = search_prompt
        self.filter_prompt = filter_prompt
        self.search_size = search_size
        self.chunk_size = chunk_size
        self.default_vocabulary = default_vocabulary

        self.statuses = {0: "not_started",
                         1: "search_vector_db",
                         2: "filter_codes"}

        self.retrieved_codes = None
        self.final_concept_set = None

        self.status = 0

    def search_vector_db(self):
        if self.status == 0:
            search_result = get_code_list_vector_search(self.vector_db, self.search_prompt, self.search_size)
            self.retrieved_codes = CodedConceptSet(f"search='{self.search_prompt}'", search_result)
            self.status = 1
        else:
            raise Exception("Search already started")

    def filter_codes(self):
        if self.status == 1:
            filtered_code_list = filter_concept_set_with_llm(self.retrieved_codes, self.llm.return_llm(), self.filter_prompt, chunk_size=self.chunk_size, default_vocabulary=self.default_vocabulary)
            self.final_concept_set = CodedConceptSet(f"search_prompt='{self.search_prompt}' & filter_prompt='{self.filter_prompt}'", filtered_code_list)
            self.status = 2
        else:
            raise Exception("Codes not retrieved yet")


    def filter_codes_again(self, additional_filter_prompt):
        if self.status == 2:
            filtered_code_list = filter_concept_set_with_llm(self.final_concept_set, self.llm.return_llm(), additional_filter_prompt, chunk_size=self.chunk_size, default_vocabulary=self.default_vocabulary)

            updated_concept_set = CodedConceptSet(f"filter_prompt='{additional_filter_prompt}", filtered_code_list)

            cs_obj = concept_set.CompareCodedConceptSets(self.final_concept_set, updated_concept_set)
            self.final_concept_set.register_change(CodedConceptSetChange([], cs_obj.left_difference, updated_concept_set.name, "remove"))



def code_list_to_df(code_list):
    return pd.DataFrame(code_list.dict()["codes"])


def format_df_as_simple_table(df, delimiter="|"):
    table_str = delimiter.join(list(df.columns)) + "\n"
    row_list = df.values.tolist()
    for row in row_list:
        table_str += delimiter.join(row) + "\n"
    return table_str.rstrip()


def filter_concept_set_with_llm(concept_set, llm, filter_prompt, chunk_size=25, default_vocabulary=None):
    number_of_chunks = 1 + len(concept_set) // chunk_size
    filtered_codes = None

    for i in range(number_of_chunks):

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "I am an AI agent that filters code that are provided in a CSV format where fields are separated by a comma. Do not include the vocabulary type in the description. Only include codes that are provided in the prompt to the agent."),
            ("human", "{input}")])

        code_chain = prompt | llm.with_structured_output(CodeList)

        text_prompt = f"""
```csv
{concept_set.to_csv_string(i*chunk_size, (i+1)*chunk_size).rstrip()}
```

{filter_prompt}"""

        results = code_chain.invoke(text_prompt)
        n_codes = len(results.codes)

        if n_codes > 0:
            if filtered_codes is None:
                filtered_codes = results
            else:
                filtered_codes.codes.extend(results.codes)

    filtered_code_list = []

    if filtered_codes is None:
        pass
    else:
        for code in filtered_codes.dict()["codes"]:
            if code["vocabulary"] is None or len(code["vocabulary"]) == 0:
                code["vocabulary"] = default_vocabulary

            filtered_code_list += [CodedConcept(code["code"], code["vocabulary"], code["description"])]
    return filtered_code_list


def get_df_icd10_codes_from_ccsr(ccsr_code, api_key=None):
    code_obj = get_code_source_information(ccsr_code,  api_key, "CCSR_ICD10CM")
    result_list = []
    for result in code_obj["relationships"]:
        result_list += [result]

    df = pd.DataFrame(result_list)

    df = df[["relationship_target_code", "relationship_target"]].drop_duplicates()
    df.columns = ["code", "description"]

    df["vocabulary"] = "ICD10CM"

    return df

def get_code_list_vector_search(vector_db, search_term, n_results=100):
    search_results = vector_db.search(search_term, search_type="similarity", k=n_results)
    cleaned_results = []

    for row in search_results:
        cleaned_results += [row.metadata]

    df = pd.DataFrame(cleaned_results)
    df = df[["code","description", "vocabulary"]]

    code_list = []
    for code in df.to_dict("records"):
        code_list += [CodedConcept(code["code"], code["vocabulary"], code["description"])]

    return code_list

def generate_icd10_code_list_to_load():
    full_icd10cm_df = pd.read_csv("https://raw.githubusercontent.com/jhajagos/SupportingConceptSetGeneration/refs/heads/main/comorbidities/data/generated_from_nb/Build_ICD10CM_tables/umls_ohdsi_icd10_pt.csv")
    codable_subset_df = full_icd10cm_df[full_icd10cm_df.TTY == "PT"]
    codable_subset_df["doc"] = codable_subset_df.STR + "|" + codable_subset_df.STYs.map(lambda x: "|".join(json.loads(x.replace("'",'"'))))  + "|" + codable_subset_df.CODE

    document_list = []
    for row in codable_subset_df.to_dict("records"):
        document_list += [Document(page_content=row["doc"], metadata={"code": row["CODE"], "description": row["STR"], "vocabulary": "ICD10CM"})]

    return document_list

