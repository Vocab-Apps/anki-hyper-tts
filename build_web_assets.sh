#!/bin/sh

docker run -it --rm \
--mount type=bind,source="$(pwd)"/web,target=/workspace/web \
--mount type=bind,source="$(pwd)",target=/workspace/web_build_output \
lucwastiaux/anki-addon-svelte-build:latest sh -c "cp -rv /workspace/web/* /workspace/web_build/ && cd /workspace/web_build/ && yarn build && cp /workspace/web_build/hypertts.css /workspace/web_build/hypertts.js /workspace/web_build_output"