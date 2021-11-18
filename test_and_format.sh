#!/bin/bash
#
#

black *.py tests/*.py

flake8 *.py tests/*.py
