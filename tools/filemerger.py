from astropy.io import fits
import numpy as np
import os

# ==== CONFIGURATION ====
INPUT_DIR = "original_pieces"  # Directory containing split FITS files
OUTPUT_PATH = "testcombined.fits"  # Path to save the merged FITS file
# ========================

def combine_fits_efficient(input_dir, output_path):
    """
    Combine multiple FITS files into a single FITS file without loading all data into memory.
    Uses incremental row-by-row writing for large binary tables.
    """
    files = sorted(
        [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith(".fits")]
    )
    
    if not files:
        raise FileNotFoundError(f"No .fits files found in directory: {input_dir}")
    
    print(f"🧩 Found {len(files)} FITS parts to combine.")
    
    # Open the first file to get header and structure
    with fits.open(files[0], memmap=True) as hdul:
        hdu0 = hdul[1] if len(hdul) > 1 else hdul[0]
        header = hdu0.header.copy()
        first_data = hdu0.data
        
        if not isinstance(first_data, fits.FITS_rec):
            raise TypeError("This script currently supports binary table HDUs (not image cubes).")
        
        # Get the total number of rows across all files
        total_rows = 0
        for file in files:
            with fits.open(file, memmap=True) as temp_hdul:
                temp_hdu = temp_hdul[1] if len(temp_hdul) > 1 else temp_hdul[0]
                total_rows += len(temp_hdu.data)
        
        print(f"📊 Total rows to combine: {total_rows:,}")
        
        # Update NAXIS2 in header to reflect total rows
        header['NAXIS2'] = total_rows
        
        # Create an empty binary table HDU with the correct structure
        # We'll create a dummy with 0 rows first
        cols = []
        for col in first_data.columns:
            cols.append(fits.Column(
                name=col.name,
                format=col.format,
                array=np.array([], dtype=col.array.dtype).reshape(0, *col.array.shape[1:])
            ))
        
        empty_table = fits.BinTableHDU.from_columns(cols, header=header, nrows=total_rows)
        
        # Write the empty structure to file
        primary_hdu = fits.PrimaryHDU()
        hdul_out = fits.HDUList([primary_hdu, empty_table])
        hdul_out.writeto(output_path, overwrite=True)
        print(f"📝 Created output file structure")
    
    # Now append data from each file incrementally
    current_row = 0
    with fits.open(output_path, mode='update', memmap=True) as hdul_out:
        out_table = hdul_out[1]
        
        for i, file in enumerate(files):
            with fits.open(file, memmap=True) as hdul_in:
                hdu_in = hdul_in[1] if len(hdul_in) > 1 else hdul_in[0]
                data_in = hdu_in.data
                n_rows = len(data_in)
                
                # Copy data chunk by chunk to avoid memory issues
                print(f" ✅ Writing part {i+1}/{len(files)} — {n_rows:,} rows (position {current_row:,})")
                
                # Write in smaller batches if needed (adjust batch_size based on your memory)
                batch_size = min(100000, n_rows)  # Process 100k rows at a time
                
                for batch_start in range(0, n_rows, batch_size):
                    batch_end = min(batch_start + batch_size, n_rows)
                    batch_data = data_in[batch_start:batch_end]
                    
                    # Copy each column
                    for col_name in data_in.names:
                        out_table.data[col_name][current_row + batch_start:current_row + batch_end] = batch_data[col_name]
                
                current_row += n_rows
        
        # Flush changes to disk
        hdul_out.flush()
    
    print(f"🎉 Combined FITS file saved as: {output_path}")
    print(f"📦 Total rows written: {current_row:,}")

# ==== RUN ====
if __name__ == "__main__":
    combine_fits_efficient(INPUT_DIR, OUTPUT_PATH)