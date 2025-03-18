export CUDA_VISIBLE_DEVICES=0,1

PROJECT_NAME=msmarco_search
train_domain=health
eval_domain=health
retrieval_mode=sparse
EXP_NAME=msmarco_search_3b_${train_domain}_${retrieval_mode}_new_corpus

DATE=$(date '+%Y-%m-%d-%H-%M-%S')

python3 -m verl.trainer.main_ppo \
    data.train_files=data/local_index_search/msmarco_${train_domain}/${retrieval_mode}/train.parquet \
    data.val_files=data/local_index_search/msmarco_${eval_domain}/${retrieval_mode}/test.parquet \
    data.train_batch_size=64 \
    data.val_batch_size=64 \
    data.max_prompt_length=256 \
    data.max_response_length=350 \
    actor_rollout_ref.actor.optim.lr=1e-6 \
    actor_rollout_ref.actor.strategy=fsdp \
    actor_rollout_ref.actor.ppo_mini_batch_size=16 \
    actor_rollout_ref.actor.ppo_micro_batch_size=2 \
    critic.ppo_micro_batch_size=2 \
    actor_rollout_ref.rollout.log_prob_micro_batch_size=2 \
    actor_rollout_ref.rollout.tensor_model_parallel_size=1 \
    actor_rollout_ref.rollout.gpu_memory_utilization=0.2 \
    actor_rollout_ref.ref.log_prob_micro_batch_size=2 \
    actor_rollout_ref.model.enable_gradient_checkpointing=True \
    actor_rollout_ref.ref.fsdp_config.param_offload=True \
    critic.model.enable_gradient_checkpointing=True \
    critic.optim.lr=1e-5 \
    critic.model.enable_gradient_checkpointing=True \
    algorithm.kl_ctrl.kl_coef=0.001 \
    trainer.logger=['wandb'] \
    +trainer.val_before_train=False \
    trainer.default_hdfs_dir=null \
    trainer.n_gpus_per_node=2 \
    trainer.nnodes=1 \
    trainer.save_freq=50 \
    trainer.test_freq=50 \
    trainer.project_name=$PROJECT_NAME \
    trainer.experiment_name=$EXP_NAME \
    actor_rollout_ref.model.path=Qwen/Qwen2.5-3B-Instruct \
    critic.model.path=Qwen/Qwen2.5-3B-Instruct \
    trainer.default_local_dir=/shared/eng/pj20/lmr_model/msmarco_${train_domain}_${retrieval_mode}_new_corpus \
    trainer.total_epochs=5 2>&1 | tee exp_log/$PROJECT_NAME-3b-ppo-verl_demo_$DATE.log 
