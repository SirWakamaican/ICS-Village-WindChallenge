#!/bin/bash
python3 hmi.py &
docker start distracted_merkle
sleep 10
docker start eloquent_heisenberg

