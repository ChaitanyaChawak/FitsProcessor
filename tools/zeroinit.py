from astropy.io import fits
import numpy as np
import os

# ==== CONFIGURATION ====
template_fits = "generated/EUC_LE3_SHEARCATALOG__20251024T140753.777043Z_00.00.fits"      # Template FITS to copy column structure
output_fits = "zeros_initialized.fits"
total_rows = 100_000_000             # Total number of rows
chunk_rows = 100_000                 # Tune for available RAM
# ========================


def fits_format_to_nbytes(fmt: str) -> int:
    """Return number of bytes occupied by one element of a given TFORM code."""
    code = fmt.strip()[-1].upper()
    mult = int(fmt.strip()[:-1]) if fmt.strip()[:-1] else 1
    size_map = {
        "L": 1,   # logical
        "X": 1,   # bit (approx)
        "B": 1,   # unsigned byte
        "I": 2,   # 16-bit int
        "J": 4,   # 32-bit int
        "K": 8,   # 64-bit int
        "E": 4,   # float32
        "D": 8,   # float64
        "C": 8,   # complex64
        "M": 16,  # complex128
        "A": 1,   # char
    }
    return mult * size_map.get(code, 1)


def initialize_fits_zeros(template_path, output_path, total_rows, chunk_rows):
    """Create a large zero-initialized FITS binary table efficiently."""
    # Read header and column definitions from template
    with fits.open(template_path, memmap=True) as hdul:
        src_hdu = hdul[1] if len(hdul) > 1 else hdul[0]
        header = src_hdu.header.copy()
        n_cols = header["TFIELDS"]
        tforms = [header[f"TFORM{i+1}"] for i in range(n_cols)]

    # Compute total bytes per row
    row_bytes = sum(fits_format_to_nbytes(f) for f in tforms)
    total_bytes = row_bytes * total_rows

    print(f"Columns: {n_cols}")
    print(f"Row size: {row_bytes} bytes  |  Total size ≈ {total_bytes/1e9:.2f} GB")

    # Create output file
    if os.path.exists(output_path):
        os.remove(output_path)

    # Write header block first (aligned to 2880 bytes)
    header_data = header.tostring().encode("ascii")
    pad = (2880 - (len(header_data) % 2880)) % 2880
    with open(output_path, "wb", buffering=0) as f:
        f.write(header_data)
        f.write(b" " * pad)

        # Write data area in zero chunks
        chunk_bytes = row_bytes * chunk_rows
        zero_block = b"\x00" * chunk_bytes

        print("🧩 Writing zero data blocks…")
        remaining = total_rows
        while remaining > 0:
            n_write = min(remaining, chunk_rows)
            f.write(zero_block[: n_write * row_bytes])
            remaining -= n_write
        print("✅ Zero initialization done.")

        # FITS data must be padded to multiple of 2880 bytes
        pad = (2880 - (f.tell() % 2880)) % 2880
        if pad:
            f.write(b"\x00" * pad)

    print(f"🎉 Created {output_path} ({total_bytes/1e9:.2f} GB logical size)")

initialize_fits_zeros(template_fits, output_fits, total_rows, chunk_rows)