from typing import List

def get_autocomplete(query, choices: List):
    return list(filter(lambda x: query.lower() in x.lower(), choices))[:25]
