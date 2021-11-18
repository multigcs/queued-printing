#!/bin/bash
#
#




for IMG in PrusaSlicer/resources/profiles/*/*_thumbnail.png
do

    VENDOR="`echo "$IMG" | cut -d"/" -f4`"
    MODEL="`echo "$IMG" | cut -d"/" -f5 | sed "s|_thumbnail.png$||g"`"

    echo "$VENDOR-$MODEL.png"
    ln -sfv "../$IMG" "images/$VENDOR-$MODEL.png"


done

