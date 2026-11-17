# Introduction

Both the ELRS antenna and ESP talk in the same frequency, 2.4GHz, this popped a curiosity on whether an interference between the two could happen and if it does how can we test it and correct it.

Our drone is being made with only the SEA:ME laboratory in mind so we assumed from the get go that the two would be able to coexist with no major problems but the tests were made to give us peace of mind.

The tests were ran using the telemetry and log function of the edgeTX on our RadioMaster Pocket keeping note of the values explained bellow:


| 1RSS | Signal strength  in dBm, close to 0 is good                                      |
| ---- | -------------------------------------------------------------------------------- |
| RQ1Y | Receiver link quality, if this hits 0 fail safe triggers                         |
| RSNR | Signal to noise ratio, in dB, this is what shows the noise from any interferance |
| TQ1y | Quality of packets that come from the drone                                      |
| TRSS | Signal strength of the drone's telemetry                                         |
| TSNR | Signal to noise ratio on the controller                                          |

# Results

Every value barely changes between the tests, meaning that there's no worries about the two of them coliding.
Every value looks good and present nothing that we should worry about.

| Value | ESP Off | ESP Stress |
| ----- | ------- | ---------- |
| 1RSS  | -44dBm  | -41dBm     |
| RQ1Y  | 97%     | 99%        |
| RSNR  | 12db    | 11db       |
| TQ1y  | 98%     | 98%        |
| TRSS  | -37     | -41        |
| TSNR  | 12db    | 15db       |

# Tags
#resources 