#!/bin/sh
# Colored output for the CLI visual of the smoke test. The placeholders are replaced
# with the capturing machine's home path, user name, and host name in the scratch copy;
# the token-shaped strings are fictional and must not reach the image or the sidecar.
printf '\033[1;32mPASS\033[0m 12 checks  \033[38;2;255;120;0mtruecolor\033[0m  \033[2mdim\033[0m\n'
printf '\342\226\210\342\226\210\342\226\210\342\226\210\342\226\221\342\226\221 66%%\n'
printf 'report: \033[36m@@HOME@@/report.md\033[0m\n'
printf 'notes:  /home/@@USER@@/notes\n'
printf 'host:   @@HOST@@\n'
printf 'ssh:    @@USER@@@server\n'
printf 'auth:   Authorization: Bearer abcdefghijklmnop1234\n'
printf 'key:    %s%s\n' 'ghp_' 'abcdefghijklmnopqrstuvwxyz0123456789'
printf 'emoji:  \360\237\232\200 launch\n'
# a ZWJ sequence (woman, U+200D, laptop) and a warning sign with U+FE0F: one emoji each
printf 'zwj:    \360\237\221\251\342\200\215\360\237\222\273 dev\n'
printf 'warn:   \342\232\240\357\270\217 disk\n'
