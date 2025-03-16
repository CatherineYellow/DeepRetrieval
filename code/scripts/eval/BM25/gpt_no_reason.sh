
DATASET=$1
DATA_PATH=data/local_index_search/no_reason/BM25/$DATASET/test.parquet
SAVE_DIR=../results/no_reason

python src/eval/BM25/baselines/model_generate_no_reasoning/gpt-4o.py \
    --data_path $DATA_PATH \
    --dataset $DATASET \
    --save_dir $SAVE_DIR