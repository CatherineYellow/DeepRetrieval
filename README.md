<div align="center">

# DeepRetrieval - Hacking Search Engines & Retrievers with LLM + RL
### **Let LLMs learn how to search! (New results on ~10 more datasets coming soon!)**

</div>



![alt text](/images/framework.png "reward curve during training (on pubmed)")

[Preliminary Technical Report (ArXiv preprint)](https://arxiv.org/pdf/2503.00223)

[Wandb Training Log](https://wandb.ai/patjj/literature_search?nw=nwuserpj20)


## Installation

**General Installation (for all retrieval methods):**
```
conda create -n zero python=3.9
# install torch [or you can skip this step and let vllm to install the correct version for you]
pip install torch==2.4.0 --index-url https://download.pytorch.org/whl/cu121
# install vllm
pip3 install vllm==0.6.3 # or you can install 0.5.4, 0.4.2 and 0.3.1
pip3 install ray

# verl
cd code
pip install -e .

# flash attention 2
pip3 install flash-attn --no-build-isolation
# quality of life
pip install wandb IPython matplotlib
```

**For Search Engine Retrieval, you can skip the following steps.**

If using sparse retrieval (e.g., BM25) or dense retrieval (e.g., DPR), please also install the following:
```
# we use pyserini for efficient retrieval and evaluation
pip install pyserini    # the version we used is 0.22.1

# if you don't have faiss installed, install it with:
pip install faiss-gpu==1.7.2    # the version we used is 1.7.2

# if you don't have java installed, install it with:
pip install install-jdk && python -c "import jdk; jdk.install('11')"

# support sql execution
pip install func_timeout
```

## Get Started
```
cd code
```


**1. Data Preparation (required)**

For example, for PubMed:
```
conda activate zero
python data_preprocess/pubmed.py
```

**2. Get Your Search Engine API Key (required if use search engine)**

For example, for PubMed, you may get it following the instruction [here](https://support.nlm.nih.gov/kbArticle/?pn=KA-05317).

Then, put it in under `code/verl/utils/reward_score/apis/` as `pubmed_api.key`.


**3. Reward function Related (optional)**

Reward Design (e.g., in `code/verl/utils/reward_score/pubmed.py`):


| Recall      | ≥ 0.7 | ≥ 0.5 | ≥ 0.4 | ≥ 0.3 | ≥ 0.1 | ≥ 0.05 | < 0.05 |
|-------------|-------|-------|-------|-------|-------|--------|--------|
| **Reward**  | +5.0  | +4.0  | +3.0  | +1.0  | +0.5  | +0.1   | -3.5   |



**4. Customize Monitor Info (optional)**

modify `compute_reward_metrics()` in `code/verl/trainer/ppo/ray_trainer.py`


## Run Training
```
conda activate zero
```

For the following code, if you see Out-of-vram, try add `critic.model.enable_gradient_checkpointing=True` to the script

For example, for PubMed:
```
sh scripts/train/pubmed.sh 
```

### Reward Curve During Training

![alt text](/images/reward_curve.png "reward curve during training (on pubmed)")


## Run Evaluation

```
sh scripts/eval/pubmed.sh
```

**Result (checkpoint date: Feb 16)**

| Model | Method | Recall (Publication) | Recall (Trial) |
|-------|--------|----------------------|----------------|
| **GPT-4o** | Zero-shot | 5.79 | 6.74 |
| | Few-shot | 7.67 | 4.69 |
| | ICL | 19.72 | 14.26 |
| | ICL+Few-shot | 11.95 | 7.98 |
| **GPT-3.5** | Zero-shot | 4.01 | 3.37 |
| | Few-shot | 4.15 | 3.34 |
| | ICL | 18.68 | 13.94 |
| | ICL+Few-shot | 7.06 | 5.54 |
| **Haiku-3** | Zero-shot | 10.98 | 11.59 |
| | Few-shot | 14.71 | 7.47 |
| | ICL | 20.92 | 24.68 |
| | ICL+Few-shot | 19.11 | 9.27 |
| **Mistral-7B** | Zero-shot | 7.18 | 8.08 |
| **LEADS**$^{*}$ | Zero-shot | 24.68 | 32.11 |
| **DeepRetrieval** | Zero-shot | **64.57** | **70.84** |

*Table: Comparison of different models and methods on publication search and trial search tasks. Bold numbers indicate the best performance.*

$^{*}$ *LEADS: a state-of-the-art literature mining LLM trained on 20K reviews and 400K publications [https://arxiv.org/pdf/2501.16255]*

## Acknowledgement

This implementation is mainly based on [verl](https://github.com/volcengine/verl) and [PySerini](https://github.com/castorini/pySerini). The base model during the experiment is [Qwen2.5-3B](https://huggingface.co/Qwen/Qwen2.5-3B). We sincerely appreciate their contributions to the open-source community.

## Cite DeepRetrieval
Current version (will update the author list upon project completion):
```
@misc{jiang2025deepretrievalpowerfulquerygeneration,
      title={DeepRetrieval: Powerful Query Generation for Information Retrieval with Reinforcement Learning}, 
      author={Pengcheng Jiang},
      year={2025},
      eprint={2503.00223},
      archivePrefix={arXiv},
      primaryClass={cs.IR},
      url={https://arxiv.org/abs/2503.00223}, 
}
```

```
@article{deepretrieval,
  title={DeepRetrieval: Hacking Real Search Engines and Retrievers with Large Language Models and Reinforcement Learning},
  author={Jiang, Pengcheng and Lin, Jiacheng and Cao, Lang and Tian, Runchu and Kang, SeongKu and Wang, Zifeng and Sun, Jimeng and Han, Jiawei},
  howpublished={\url{https://github.com/pat-jj/DeepRetrieval}},
  year={2025}
}
```

Thanks for your interests! 😊
