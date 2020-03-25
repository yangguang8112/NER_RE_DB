TASK_NAME="gad"
BERT_DIR="./relation_extract/config"
RE_DIR=""
OUTPUT_DIR=./relation_extract/model
TEST_DIR=$1

# 加载装有tensorflow-gpu的python环境
# >>> conda init >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$(CONDA_REPORT_ERRORS=false '/home/yg/anaconda3/bin/conda' shell.bash hook 2> /dev/null)"
if [ $?  -eq 0 ];  then
\eval "$__conda_setup"
else
if [ -f  "/home/yg/anaconda3/etc/profile.d/conda.sh" ];  then
.  "/home/yg/anaconda3/etc/profile.d/conda.sh"
CONDA_CHANGEPS1=false conda activate base
else
\export PATH="/home/yg/anaconda3/bin:$PATH"
fi
fi
unset __conda_setup
# <<< conda init <<<
conda activate biobert

python ./relation_extract/run_re.py --task_name=$TASK_NAME --do_train=false --do_eval=false --do_predict=true \
                                            --vocab_file=$BERT_DIR/vocab.txt \
                                            --bert_config_file=$BERT_DIR/bert_config.json \
                                            --init_checkpoint=$BERT_DIR/model.ckpt-1000000 \
                                            --max_seq_length=64 --train_batch_size=16 \
                                            --learning_rate=2e-5 --num_train_epochs=3.0 \
                                            --do_lower_case=false --data_dir=$RE_DIR \
                                            --output_dir=$OUTPUT_DIR \
                                            --test_dir=$TEST_DIR
