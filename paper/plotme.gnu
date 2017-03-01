set term png
set title "Number of spots and Resolution per image"
set xlabel "Image number"
set ylabel "Number of Spots"
set y2label "Resolution"
set grid
set xrange [0:200]
set out 'therm.png'
set y2tics nomirror
set ytics nomirror
set key below
plot 'thermolysin_1_1440.gplt' u 1:2 t 'Found spots', '' u 1:3 t 'Good Bragg candidates', '' u 1:5 axes x1y2 t 'Resolution'
set out
