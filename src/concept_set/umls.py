import time
import logging
import requests

import time
import logging
import requests

UMLS_BASE_URL = "https://uts-ws.nlm.nih.gov/rest"


def process_relationships(relationships):
  """Build a list of relationships from the API response"""
  relationship_list = []
  for relation in relationships:
    relationship_list += [{"relationship_source": relation['rootSource'],
                            "relationship_type": relation['relationLabel'],
                            "relationship_type_description": relation['additionalRelationLabel'],
                            "relationship_target": relation['relatedIdName'],
                            "relationship_target_code": relation["relatedId"].split("/")[-1]
                          }]
  return relationship_list


def process_hierarchial_term(terms):
  result_list = []
  for term in terms:
    result_list += [{
        "id": term["ui"],
        "name": term["name"]}
    ]
  return result_list


def umls_request(url, api_key=None, additional_params={}):
  """Make a request to the UMLS API and return the response"""
  start_time = time.time()

  params = {"apiKey": api_key}
  params.update(additional_params)

  logging.info(f"Making request to {url} with params {params}")
  try:
      response = requests.get(url, params=params).json()
  except requests.JSONDecodeError:
      response = requests.get(url, params=params)

      print(url, params)

      # print("Response:")
      # print(response)
      # print("Content:")
      # print(response.text)

      raise RuntimeError

  end_time = time.time()
  logging.info(f"Request took {end_time - start_time} seconds")

  return response


def get_vocabularies(api_key):
  rl = umls_request(UMLS_BASE_URL + "/metadata/current/sources", api_key)
  return {r["abbreviation"]: r["expandedForm"] for r in rl['result']}


def get_vocabulary_languages(api_key):
  rl = umls_request(UMLS_BASE_URL + "/metadata/current/sources", api_key)
  return {r["abbreviation"]: r["language"]["expandedForm"] for r in rl['result']}


def get_code_source_information(code, api_key, source="ICD10CM", version = "current"):
  """For a given term in the source vocabulary get the context around the term and
    returns results as a dictionary."""

  languages = get_vocabulary_languages(api_key) # Get language

  r_obj = umls_request(UMLS_BASE_URL + f"/content/{version}/source/{source}/{code}", api_key)

  if "result" not in r_obj:
    return None
  else:
    r = r_obj["result"]

    name = r["name"]

    attributes_dict = {} # Gets a term attributes (MRSAT table)
    if r["attributes"] == "NONE":
      pass
    else:
      attributes = umls_request(r["attributes"], api_key, additional_params={"pageSize": 100}) # TODO: Add paging
      if "result" in attributes:
        for attribute in attributes["result"]:
          attributes_dict[attribute["name"]] = attribute["value"]

    relationship_list = [] # Gets term relationships (MRREL)
    if r["relations"] == "NONE":
      pass
    else:
      relationships = umls_request(r["relations"], api_key, additional_params={"pageSize": 100})
      if "pageCount" in relationships:
        relationship_list = process_relationships(relationships["result"])
        if relationships["pageCount"] > 1:
          for i in range(2,relationships["pageCount"]+1):
            i_relationships = umls_request(r["relations"], api_key, additional_params={"pageSize": 100, "pageNumber": i})
            relationship_list += process_relationships(i_relationships["result"])

    # Get CUIs associated with the term (MRCONSO)
    concept_url = r["concepts"]
    concepts_obj = umls_request(concept_url)

    # Get parent and children terms

    parent_list = []
    children_list = []

    parents = r["parents"]
    children = r["children"]

    if parents != "NONE":
      parent_obj = umls_request(parents)
      parent_list = process_hierarchial_term(parent_obj["result"])

    if children != "NONE":
      children_obj = umls_request(children)
      children_list = process_hierarchial_term(children_obj["result"])

    ancestors_list = []
    descendants_list = []

    ancestors = r["ancestors"]
    descendants = r["descendants"]

    if ancestors != "NONE":
      ancestors_obj = umls_request(ancestors)
      ancestors_list = process_hierarchial_term(ancestors_obj["result"])

    if descendants != "NONE":
      descendants_obj = umls_request(descendants)
      descendants_list = process_hierarchial_term(descendants_obj["result"])

    concept_dict = {}
    if "result" in concepts_obj:
      concepts = concepts_obj["result"]["results"]

      for concept in concepts:
        concept_dict[concept["ui"]] = {"concept_uri": concept["uri"]}

      # Get defintions (include only English defintions) MRDEF
      for cui in concept_dict:
        concept_obj = umls_request(concept_dict[cui]["concept_uri"], api_key)

        if "result" in concept_obj:
          cui_concept_obj = concept_obj["result"]
          semantic_types = [s["name"] for s in cui_concept_obj["semanticTypes"]]
          if len(semantic_types) == 1:
            concept_dict[cui]["semantic_type"] = semantic_types[0]
          else:
            concept_dict[cui]["semantic_type"] = semantic_types

          concept_dict[cui]["definitions"] = {}
          if "definitions" in cui_concept_obj:

            if cui_concept_obj["definitions"] != "NONE":
              defintions_obj = umls_request(cui_concept_obj["definitions"])
              for result in defintions_obj["result"]:
                vocabulary = result["rootSource"]
                if languages[vocabulary] == "English":
                  concept_dict[cui]["definitions"][vocabulary] = result["value"]

  return {"code": code, "name": name, "vocabulary": source, "concepts": concept_dict,
          "attributes": attributes_dict, "relationships": relationship_list,
          "parents": parent_list, "children": children_list,
          "ancestors": ancestors_list, "descendants": descendants_list}