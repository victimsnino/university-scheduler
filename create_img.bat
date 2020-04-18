gprof2dot -n1 -e1 -f pstats prof/combined.prof > prof/tmp
dot -Tsvg -o prof/combined.svg prof/tmp
rm ./prof/tmp
.\prof\combined.svg 