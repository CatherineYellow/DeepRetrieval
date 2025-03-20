import sys
import os
import concurrent.futures
import time
from functools import partial


PUBLICATION_DETAILED_PROMPT = """You are a clinical specialist. You are conducting research and doing a medical literature review.
The research is defined by the following PICO elements:
P (Patient, Problem or Population): {P}
I (Intervention): {I}
C (Comparison): {C}
O (Outcome): {O}

Your task is to create an URL of search query for relevant publications on PubMed.

template URL: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=query+term
You should output an URL of search query based on it.

Notice:
1. Extract the most relevant and specific keywords from each PICO element.
2. Avoid using full sentences; focus on short, impactful terms.
3. Use Boolean operators (AND, OR) to structure your query logically.
4. Ensure the query is concise to maximize recall.
5. Use parentheses to group terms and control the query logic.
6. If there are synonymous terms or common variations, include them using the OR operator.

Steps to create the query:
1. Identify 1-2 primary keyword from each PICO element.
2. Combine these keywords using Boolean operators to form a structured search query.
3. Use parentheses to ensure proper grouping and logic in the query.
4. Include synonyms and variations using the OR operator to expand the search scope, if necessary.

Please do the reasoning before generating the query.
Note: The output should be a valid JSON object, e.g., using double quotes for strings, using slashes for special characters.

Your output should be in the following JSON format:
{{
"reasoning": "...",
"query": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=..."
}}
"""


# Debug: Print current directory and Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))  # 
# Add the project root to Python path
sys.path.insert(0, project_root)  # 


import argparse
import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from tqdm import tqdm
import json
import re
from collections import deque
from threading import Lock

from verl.utils.apis.pubmed import PubmedAPI
from src.utils.claude_api import get_claude_response
from src.utils.gpt_azure import gpt_chat_35_msg, gpt_chat_4o



# Add these at the top with other global variables
_request_times = deque(maxlen=20)  # Track last 20 requests
_request_lock = Lock()  # Thread-safe lock for request tracking



def run_search_pubmed(search_query, search_api, pub_date):
    # Rate limit checking
    current_time = time.time()
    with _request_lock:
        # Remove requests older than 1 second
        while _request_times and current_time - _request_times[0] > 1.0:
            _request_times.popleft()
        
        # Check if we're exceeding rate limit (10 requests per second)
        if len(_request_times) >= 10:
            print("\033[93m[Warning] PubMed rate limit (10 req/s) reached! Consider reducing batch size.\033[0m")
        
        # Record this request
        _request_times.append(current_time)
    
    # add date
    date_query_part = f'&datetype=pdat&mindate=1970/01/01&maxdate={pub_date}'
    search_query += date_query_part
    
    print('Query:', search_query)
    # search
    pmid_list = search_api.search_with_query(search_query, topk=3000)
    
    return pmid_list
    
def extract_json_from_llm_output(text):
    # pattern = r"```json\n([\s\S]+?)\n```"
    # matched_jsons = re.findall(pattern, text)
    
    # if matched_jsons:
    #     extracted_json = matched_jsons[-1]  # get the final one
    #     return json.loads(extracted_json)
    # else:
    #     try:
    #         pattern = r"\{.*?\}"
    #         matched_jsons = re.findall(pattern, text, re.DOTALL)
            
    #         if matched_jsons:
    #             extracted_json = matched_jsons[-1]  # get the final one
    #             try:
    #                 print(f"Extracted JSON: {extracted_json}")
    #                 return json.loads(extracted_json)
    #             except:
    #                 print(f"Warning: No JSON structure found. Using the response itself as the query. {extracted_json}")
    #                 return extracted_json.split(": ")[1].strip()
    #         else:
    #             raise ValueError('No JSON structure found.')
        # except:
        #     return text
        print(text)
        extraction =  text.split("query\": ")[1].split("\n")[0].strip()
        if extraction.startswith("\"") and extraction.endswith("\""):
            return extraction[1:-1]
        else:
            return extraction



def llm_query_generation(P, I, C, O, llm):
    
    if "claude" in llm:
        llm_response = get_claude_response(llm.replace("claude-", ""), PUBLICATION_DETAILED_PROMPT.format(
            P=P,
            I=I,
            C=C,
            O=O
        ))
    elif "gpt" in llm:
        if "35" in llm:
            llm_response = gpt_chat_35_msg(PUBLICATION_DETAILED_PROMPT.format(
                P=P,
                I=I,
                C=C,
                O=O
            ))
        elif "4o" in llm:
            llm_response = gpt_chat_4o(PUBLICATION_DETAILED_PROMPT.format(
                P=P,
                I=I,
                C=C,
                O=O
            ))
    else:
        raise ValueError(f"Unknown LLM: {llm}")
    
    query = extract_json_from_llm_output(llm_response)
    return query, llm_response


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", type=str, default="")
    parser.add_argument("--batch_size", type=int, default=1)
    parser.add_argument("--save_dir", type=str, default="results/pubmed_reason")
    args = parser.parse_args()
    return args

def process_single_llm_call_with_retry(P, I, C, O, llm, max_retries=3):
    retry_count = 0
    while retry_count < max_retries:
        try:
            query, llm_response = llm_query_generation(P, I, C, O, llm)
            return query, llm_response
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                wait_time = 2 ** retry_count  # Exponential backoff
                print(f"LLM call failed. Retrying in {wait_time} seconds... (Attempt {retry_count}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"Failed after {max_retries} attempts. Error: {str(e)}")
                return None, None

def process_batch(batch_data, search_api, llm):
    batch_results = []
    batch_responses = []
    batch_recalls = []
    
    # Use ThreadPoolExecutor for parallel LLM calls
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch_data)) as executor:
        # Create futures with their original indices
        futures = []
        for idx, data in enumerate(batch_data):
            future = executor.submit(
                process_single_llm_call_with_retry,
                data['pico']['P'],
                data['pico']['I'],
                data['pico']['C'],
                data['pico']['O'],
                llm
            )
            futures.append((idx, future))
        
        # Initialize results list with None values
        llm_results = [None] * len(batch_data)
        
        # Process futures as they complete while maintaining original order
        for idx, future in futures:
            try:
                query, llm_response = future.result()
                if query is not None:
                    llm_results[idx] = (query, llm_response, batch_data[idx]['pub_date'], batch_data[idx]['publication_pmids'])
            except Exception as e:
                print(f"Unexpected error processing LLM call at index {idx}: {str(e)}")
                llm_results[idx] = None
    
    # Process search queries sequentially to respect rate limits
    for result in llm_results:
        if result is None:
            batch_responses.append(None)
            batch_recalls.append(0)
            continue
            
        query, llm_response, pub_date, ground_truth = result
        batch_responses.append(llm_response)
        
        try:
            pmid_list = run_search_pubmed(query, search_api, pub_date)
            recall = len(set(pmid_list) & set(ground_truth)) / len(ground_truth)
            batch_recalls.append(recall)
        except Exception as e:
            print(f"Error in search query: {str(e)}")
            batch_recalls.append(0)
    
    return batch_responses, batch_recalls

def main():
    args = arg_parser()
    
    if os.path.exists('verl/utils/reward_score/apis/pubmed_api.key'):
        api_key = open('verl/utils/reward_score/apis/pubmed_api.key', 'r').read().strip()
        search_api = PubmedAPI(api_key=api_key)
        
    test_path = "data/raw_data/pubmed/test.jsonl"
    test_data = []
    with open(test_path, 'r') as f:
        for line in f:
            test_data.append(json.loads(line))
    
    llm_responses = []
    recalls = []
    
    # Process data in batches
    batch_size = args.batch_size
    for i in tqdm(range(0, len(test_data), batch_size)):
        batch = test_data[i:i + batch_size]
        batch_responses, batch_recalls = process_batch(batch, search_api, args.llm)
        
        llm_responses.extend(batch_responses)
        recalls.extend(batch_recalls)
        
        current_avg_recall = sum(recalls) / len(recalls)
        print(f"Batch {i//batch_size + 1} completed. Current Average Recall: {current_avg_recall:.4f}")
    
    final_avg_recall = sum(recalls) / len(recalls)
    print(f"\nFinal Average Recall: {final_avg_recall:.4f}")
    
    # Save results
    os.makedirs(args.save_dir, exist_ok=True)
    with open(os.path.join(args.save_dir, f"llm_responses_{args.llm}.json"), 'w') as f:
        json.dump(llm_responses, f, indent=2)

if __name__ == "__main__":
    main()
