#!/bin/bash
cd "$(dirname "$0")/.."
for k in 1 2 3 5 8; do
  echo "######## device-derived k=$k ########"
  python3 -m fedhomeguard.runner --stage 3 --config configs/stage3_k$k.yaml --name dev_k$k
  echo "######## IID control k=$k ########"
  python3 - <<PY
import yaml,copy
c=yaml.safe_load(open('configs/stage3_k$k.yaml')); c['partition']['kind']='iid'; c['name']='iid_k$k'
yaml.safe_dump(c, open('configs/_tmp_iid_k$k.yaml','w'), sort_keys=False)
PY
  python3 -m fedhomeguard.runner --stage 3 --config configs/_tmp_iid_k$k.yaml --name iid_k$k
done
echo "KSWEEP DONE"
