#!/bin/bash

uvicorn --host 0.0.0.0 --port 8080 ichnaea.vis_aggregator.service.main:app
