# h2nim.py

Dirty code just to get as much as it can in the process of wrapping a C header.

In order to use it, just point to the header and to the library and will print to the stdout:
```
python h2nim.py gr.h /usr/gr/lib/libGR.so
```

or well you can provide the output file as well:
```
python h2nim.py gr.h /usr/gr/lib/libGR.so gr_wrapper.nim
```






