Standalone utility scripts for working with large FITS files. They are not used by the main program (`src/example_run.py`).

Run them from the root of the project directory (e.g. `python tools/filesplitter.py`), since their paths are relative to it. Edit the configuration variables at the top of each script (or in its `__main__` block) before running.

File descriptions:

- `columnswap.py`\
Copies the columns of FITS file A into the matching columns of FITS file B, in row chunks (to a new file or in place)

- `filesplitter.py`\
Splits a large FITS file into multiple smaller FITS files of a fixed number of rows

- `filemerger.py`\
Combines the FITS files in a directory (e.g. the output of `filesplitter.py`) into a single FITS file without loading all data into memory

- `zeroinit.py`\
Creates a FITS file with the column structure of a template FITS file and a given number of zero-initialized rows, written in chunks
