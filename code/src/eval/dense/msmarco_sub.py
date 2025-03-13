import json
import sys
import os
from tqdm import tqdm
import pdb
sys.path.append('./')

from pyserini.search.faiss import FaissSearcher
from src.Lucene.utils import ndcg_at_k
from src.eval.BM25.utils import parse_qrel


index_path = "/home/azureuser/cloudfiles/code/DeepRetrieval/indexes/faiss-flat.msmarco-v1-passage.tct_colbert.20210112.be7119"
dense_encoder_name = "castorini/tct_colbert-msmarco"
topic = "health"
# topic = "science"
# topic = "technology"


if not os.path.exists(index_path):
    print("[Warning] Pyserini index not found for fever")
    search_system = None
else:
    search_system = FaissSearcher(index_path, dense_encoder_name)


if __name__ == '__main__':
    with open("data/raw_data/msmarco/qrels.dev.tsv", "r", encoding="utf-8") as file:
        qrel_test = [line.strip().split("\t") for line in file]

    qrel_test = qrel_test[1:]  # remove the header

    qrel_test = parse_qrel(qrel_test)

    with open("data/raw_data/msmarco/msmarco_health/dev.jsonl", "r", encoding="utf-8") as file:
        queries = [json.loads(line) for line in file]
    queries_dict = {q['_id']: q['text'] for q in queries}
    
    test_data = []
    for qid, value in qrel_test.items():
        test_data.append({
            "qid": qid,
            'query': queries_dict[qid],
            "target": value['targets'],
            "score": value['scores']
        })

    ndcg = []
    batch_size = 100

    for i in tqdm(range(0, len(test_data), batch_size)):
        batch = test_data[i:i+batch_size]
        queries = [item['query'] for item in batch]
        targets = {item['query']: item['target'] for item in batch} 
        scores = {item['query']: item['score'] for item in batch}
        
        results = search_system.batch_search(queries, top_k=10, threads=16)
        
        for query in queries:
            retrieved = [result[0] for result in results.get(query, [])]
            ndcg.append(ndcg_at_k(retrieved, targets[query], 10, rel_scores=scores[query]))
    
    print(f"Average NDCG@10: {sum(ndcg) / len(ndcg)}")