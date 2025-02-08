#!/bin/bash
source activate "/chekkk/software/python39"
python --version
nohup python saas_csv_process.py -p 'chek/rawData/zeeker/007/ZEEKER-OS-6.0.3beta-N3/' > ./logs/zeeker_007_ZEEKER-OS-6_0_3beta-N3.logs 2>&1 &