import os

# numpy (pulled in by shapely/pyproj) otherwise starts one OpenBLAS thread per
# core, each reserving a large buffer; this fails on memory-constrained hosts
# and containers. The backend performs no heavy linear algebra.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
