#!/bin/sh
FORMAT=$(echo -e "\033[1;33m%w%f\033[0m")
$@
#while inotifywait -qre close_write --format "$FORMAT" .
while inotifywait -qre close_write .
do
	clear
	$@ |  sed -e "s/\(.*ok.*\|.*PASS.*\)/ \x1B[32m\1\x1b[0m /g" \
	   |  sed -e "s/\(.*Error.*\|.*error.*\)/ \x1B[33m\1\x1b[0m /g" \
	   |  sed -e "s/\(.*FAIL.*\)/ \x1B[31m\1\x1b[0m /g" \
	   |  sed -e "/\(.*\[no test files\].*\)/d" 

	echo "\n =========================================================\n"
done
