from astropy.io import fits
import os
import numpy as np

# ==== CONFIGURATION ====
INPUT_PATH = "raw/marco_cats.fits"          # Path to your large FITS file
OUTPUT_DIR = "original_pieces"            # Directory where splits will be saved
CHUNK_SIZE = 10000000                     # Rows (for tables) or planes (for 3D images) per chunk
# ========================


def split_fits(input_path, output_dir, chunk_size):
    """
    Split a large FITS file into multiple smaller FITS files efficiently.

    Parameters:
        input_path (str): Path to the large FITS file.
        output_dir (str): Directory to store split FITS files.
        chunk_size (int): Number of rows (for table HDU) or planes (for image HDU) per output file.
    """
    os.makedirs(output_dir, exist_ok=True)

    with fits.open(input_path, memmap=True) as hdul:
        # Use the first extension if it’s a table HDU, else the primary HDU
        hdu = hdul[1] if len(hdul) > 1 else hdul[0]
        header = hdu.header
        data = hdu.data

        if data is None:
            raise ValueError("No data found in the FITS file!")

        # Case 1: FITS binary table
        if isinstance(data, fits.FITS_rec):
            # Make sure we get an integer row count
            n_rows = int(data.shape[0]) if isinstance(data.shape, tuple) else int(len(data))
            print(f"Table with {n_rows:,} rows found.")

            for i in range(0, n_rows, chunk_size):
                chunk = data[i:i + chunk_size]
                out_file = os.path.join(output_dir, f"split_{i // chunk_size:04d}.fits")
                fits.BinTableHDU(data=chunk, header=header).writeto(out_file, overwrite=True)
                print(f"Saved: {out_file}")

        # Case 2: Image data (3D cube)
        else:
            if data.ndim == 2:
                raise ValueError("2D image cannot be split along the first axis (no planes).")
            n_planes = data.shape[0]
            print(f"3D image with {n_planes:,} planes found.")

            for i in range(0, n_planes, chunk_size):
                chunk = data[i:i + chunk_size]
                out_file = os.path.join(output_dir, f"split_{i // chunk_size:04d}.fits")
                fits.PrimaryHDU(data=chunk, header=header).writeto(out_file, overwrite=True)
                print(f"Saved: {out_file}")

    print("✅ Done splitting FITS file.")


# ==== RUN SCRIPT ====
if __name__ == "__main__":
    split_fits(INPUT_PATH, OUTPUT_DIR, CHUNK_SIZE)
