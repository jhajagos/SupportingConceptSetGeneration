from pydantic import BaseModel, Field
from typing import List, Optional
import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
import logging

from sympy.polys.polytools import named_poly

from umls import get_code_source_information


class Code(BaseModel):
    code: str = Field(description="code identifier")
    description: str = Field(description="a human readable description of the code")
    vocabulary: Optional[str] = Field(description="Coding system such as ICD10CM or CCSR")


class CodeWithReason(Code):
    reason: str = Field(description="reason for either inclusion or exclusion")


class CodeList(BaseModel):
    codes: List[Code] = Field(default_factory=list, description="A list of codes")


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


def code_list_to_df(code_list):
    return pd.DataFrame(code_list.dict()["codes"])


def code_list_to_concept_set(code_list, vocabulary_name=None):
    pass

def format_df_as_simple_table(df, delimiter="|"):
    table_str = delimiter.join(list(df.columns)) + "\n"
    row_list = df.values.tolist()
    for row in row_list:
        table_str += delimiter.join(row) + "\n"
    return table_str.rstrip()


def filter_codes(code_df, llm, filter_prompt, chunk_size=25, return_df=True):
    number_of_chunks = 1 + len(code_df) // chunk_size
    filtered_codes = None

    for i in range(number_of_chunks):

        chunk_df = code_df.iloc[i * chunk_size:(i + 1) * chunk_size]

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an agent that filters code that are provided in a table format where fields are separated by ,. Only include codes that are provided in the prompt"),
            ("human", "{input}")])

        code_chain = prompt | llm.with_structured_output(CodeList)

        text_prompt = f"""
    ```csv
{format_df_as_simple_table(chunk_df, delimiter=",")}
```

    {filter_prompt}"""

        results = code_chain.invoke(text_prompt)
        n_codes = len(results.codes)

        if n_codes > 0:
            if filtered_codes is None:
                filtered_codes = results
            else:
                filtered_codes.codes.extend(results.codes)

    if return_df and filtered_codes is not None:
        return code_list_to_df(filtered_codes)
    else:
        return filtered_codes

def get_df_icd10_codes_from_ccsr(ccsr_code):
    code_obj = get_code_source_information(ccsr_code, "CCSR_ICD10CM")
    result_list = []
    for result in code_obj["relationships"]:
        result_list += [result]

    df = pd.DataFrame(result_list)

    df = df[["relationship_target_code", "relationship_target"]].drop_duplicates()
    df.columns = ["code", "description"]

    logging.info(f"Retrieved {len(df)} ICD10 codes for '{ccsr_code}'")

    return df

def get_code_df_vector_search(vector_db, search_term, n_results=100):
    search_results = vector_db.search(search_term, search_type="similarity", k=n_results)
    cleaned_results = []

    for row in search_results:
        cleaned_results += [row.metadata]

    df = pd.DataFrame(cleaned_results)

    df = df[["code","description"]]

    return df

def search_and_filter_codes(llm, vectordb, search_prompt, filter_prompt, n_results=100, chunk_size=25):
    search_df = get_code_df_vector_search(vectordb, search_prompt, n_results)
    return filter_codes(search_df, llm, filter_prompt, chunk_size)