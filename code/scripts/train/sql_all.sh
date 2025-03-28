export HYDRA_FULL_ERROR=1

PROJECT_NAME=sql_all

EXP_NAME=sql_all_3b
INIT_MODEL=/dev/v-langcao/Qwen2.5-Coder-3B-Instruct
# INIT_MODEL=Qwen/Qwen2.5-Coder-3B-Instruct

# EXP_NAME=sql_all_7b
# INIT_MODEL=Qwen/Qwen2.5-7B-Instruct
# INIT_MODEL=/dev/v-langcao/Qwen2.5-Coder-7B-Instruct


DATE=$(date '+%Y-%m-%d-%H-%M-%S')

python3 -m verl.trainer.main_ppo \
    data.train_files=data/sql/bird/train.parquet \
    data.val_files=data/sql/bird/test.parquet \
    data.train_batch_size=64 \
    data.val_batch_size=64 \
    data.max_prompt_length=2048 \
    data.max_response_length=512 \
    actor_rollout_ref.actor.optim.lr=1e-6 \
    actor_rollout_ref.actor.strategy=fsdp \
    actor_rollout_ref.actor.ppo_mini_batch_size=16 \
    actor_rollout_ref.actor.ppo_micro_batch_size=4 \
    critic.ppo_micro_batch_size=4 \
    actor_rollout_ref.rollout.log_prob_micro_batch_size=4 \
    actor_rollout_ref.rollout.tensor_model_parallel_size=1 \
    actor_rollout_ref.rollout.gpu_memory_utilization=0.3 \
    actor_rollout_ref.ref.log_prob_micro_batch_size=4 \
    actor_rollout_ref.rollout.temperature=0.6 \
    actor_rollout_ref.model.enable_gradient_checkpointing=True \
    actor_rollout_ref.ref.fsdp_config.param_offload=True \
    critic.model.enable_gradient_checkpointing=True \
    critic.optim.lr=1e-5 \
    critic.model.enable_gradient_checkpointing=True \
    algorithm.kl_ctrl.kl_coef=0.001 \
    trainer.logger=['wandb'] \
    +trainer.val_before_train=False \
    trainer.default_hdfs_dir=null \
    trainer.n_gpus_per_node=4 \
    trainer.nnodes=1 \
    trainer.save_freq=200 \
    trainer.test_freq=20 \
    trainer.project_name=$PROJECT_NAME \
    trainer.experiment_name=$EXP_NAME \
    actor_rollout_ref.model.path=$INIT_MODEL \
    critic.model.path=$INIT_MODEL \
    trainer.default_local_dir=/dev/v-langcao/training_outputs/${EXP_NAME} \
    trainer.total_epochs=5 2>&1 | tee exp_log/$PROJECT_NAME-3b-ppo-verl_demo_$DATE.log 
