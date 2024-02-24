CUDA_VISIBLE_DEVICES=0 python  main.py \
            --gpu           $1    \
            --eval_epoch    2  \
            --only_test     0   \
            --model_name    MCLEA \
            --data_choice   $2 \
            --data_split    $3 \
            --data_rate     $4 \
            --epoch         100 \
            --lr            1e-3  \
            --scheduler     "fixed"\
            --optim         "adam"\
            --hidden_units  "300,300,300" \
            --save_model    0 \
            --batch_size    3500 \
            --semi_learn_step 1 \
	        --csls          \
	        --csls_k        3 \
	        --random_seed   42 \
            --exp_id        seed_42 \
            --workers       12 \
            --dist          0 \
            --accumulation_steps 1 \
            --scheduler     cos \
            --attr_dim      300     \
            --img_dim       300     \
            --name_dim      300     \
            --char_dim      300     \
            --hidden_size   300     \
            --tau           0.1     \
            --tau2          4.0     \
            --structure_encoder "gat" \
            --num_attention_heads 1 \
            --num_hidden_layers 1 \
            --use_surface   0     \
            --ratio         1.0     \
            --num_layer     3
