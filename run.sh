#!/bin/bash

# 检查参数数量
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 option_number"
    echo "1: DBP15K ja-en 0.3"
    echo "2: DBP15K fr-en 0.3"
    echo "3: FBDB15K norm 0.2"
    echo "4: FBYG15K norm 0.2"
    exit 1
fi

# 根据传入的参数运行对应的命令
case $1 in
    1)
        sh run_geea.sh 0 DBP15K ja-en 0.3
        ;;
    2)
        sh run_geea.sh 0 DBP15K fr-en 0.3
        ;;
    3)
        sh run_geea.sh 0 FBDB15K norm 0.2
        ;;
    4)
        sh run_geea.sh 0 FBYG15K norm 0.2
        ;;
    *)
        echo "Invalid option: $1"
        echo "Please choose a number between 1 and 4."
        exit 1
        ;;
esac
