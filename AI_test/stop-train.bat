@echo off
setlocal
> "%~dp0python\STOP_TRAINING" echo stop
echo Stop signal sent. Training will save its checkpoint and stop after the current step.