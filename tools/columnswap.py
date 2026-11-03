"""
Memory-efficient FITS file column update for large datasets.
Updates columns in file B with data from file A in chunks.
"""

from astropy.io import fits
import numpy as np
import os

def update_fits_columns(file_a_path, file_b_path, output_path=None, chunk_size=1000000):
    """
    Update columns in file B with matching columns from file A.
    
    Parameters:
    -----------
    file_a_path : str
        Path to source FITS file A
    file_b_path : str
        Path to target FITS file B to be updated
    output_path : str, optional
        Path for output file. If None, overwrites file_b_path
    chunk_size : int
        Number of rows to process at once (default: 1M rows)
    """
    
    # Columns to copy from A to B
    columns_to_copy = ['TOM_BIN_ID', 'SHE_RA', 'SHE_DEC', 
                       'SHE_E1', 'SHE_E2', 'SHE_WEIGHT']
    
    if output_path is None:
        output_path = file_b_path + '.updated.fits'
        will_replace = True
    else:
        will_replace = False
    
    print(f"Opening files...")
    print(f"Source: {file_a_path}")
    print(f"Target: {file_b_path}")
    print(f"Output: {output_path}")
    
    # Open both files in readonly mode (memory mapped)
    with fits.open(file_a_path, mode='readonly', memmap=True) as hdul_a, \
         fits.open(file_b_path, mode='readonly', memmap=True) as hdul_b:
        
        # Get the data tables (assuming extension 1, adjust if needed)
        data_a = hdul_a[1].data
        data_b = hdul_b[1].data
        
        n_rows = len(data_b)
        print(f"Total rows in file B: {n_rows:,}")
        
        # Verify columns exist in both files
        cols_a = set(data_a.columns.names)
        cols_b = set(data_b.columns.names)
        
        missing_in_a = [col for col in columns_to_copy if col not in cols_a]
        missing_in_b = [col for col in columns_to_copy if col not in cols_b]
        
        if missing_in_a:
            raise ValueError(f"Columns missing in file A: {missing_in_a}")
        if missing_in_b:
            raise ValueError(f"Columns missing in file B: {missing_in_b}")
        
        print(f"Columns to update: {columns_to_copy}")
        
        # Create a copy of file B's HDU structure
        # Copy header and column definitions, but we'll update data
        new_hdu = fits.BinTableHDU.from_columns(
            hdul_b[1].columns,
            nrows=n_rows,
            fill=True
        )
        
        # Copy primary HDU
        primary_hdu = fits.PrimaryHDU(header=hdul_b[0].header)
        
        print(f"Processing in chunks of {chunk_size:,} rows...")
        
        # Process data in chunks
        n_chunks = (n_rows + chunk_size - 1) // chunk_size
        
        for i in range(n_chunks):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, n_rows)
            
            if (i + 1) % 10 == 0 or i == n_chunks - 1:
                print(f"Processing chunk {i+1}/{n_chunks} "
                      f"(rows {start_idx:,} to {end_idx:,})...")
            
            # Copy all data from B for this chunk first
            for col_name in data_b.columns.names:
                new_hdu.data[col_name][start_idx:end_idx] = \
                    data_b[col_name][start_idx:end_idx]
            
            # Overwrite with data from A for specified columns
            for col_name in columns_to_copy:
                new_hdu.data[col_name][start_idx:end_idx] = \
                    data_a[col_name][start_idx:end_idx]
        
        print("Writing output file...")
        
        # Create HDU list and write
        hdul_out = fits.HDUList([primary_hdu, new_hdu])
        
        # Copy any additional HDUs from file B
        for j in range(2, len(hdul_b)):
            hdul_out.append(hdul_b[j])
        
        hdul_out.writeto(output_path, overwrite=True)
        print(f"Output written to: {output_path}")
    
    # If we created a temporary file, replace the original
    if will_replace:
        print(f"Replacing original file {file_b_path}...")
        os.replace(output_path, file_b_path)
        print("Done!")


def update_fits_columns_inplace(file_a_path, file_b_path, chunk_size=1000000):
    """
    Even more memory-efficient version that updates file B in place.
    WARNING: This modifies file B directly. Make a backup first!
    
    Parameters:
    -----------
    file_a_path : str
        Path to source FITS file A
    file_b_path : str
        Path to target FITS file B to be updated (modified in place)
    chunk_size : int
        Number of rows to process at once (default: 1M rows)
    """
    
    columns_to_copy = ['TOM_BIN_ID', 'SHE_RA', 'SHE_DEC', 
                       'SHE_E1', 'SHE_E2', 'SHE_WEIGHT']
    
    print(f"Opening files...")
    print(f"Source: {file_a_path}")
    print(f"Target (IN-PLACE): {file_b_path}")
    print("WARNING: File B will be modified directly!")
    
    with fits.open(file_a_path, mode='readonly', memmap=True) as hdul_a, \
         fits.open(file_b_path, mode='update', memmap=True) as hdul_b:
        
        data_a = hdul_a[1].data
        data_b = hdul_b[1].data
        
        n_rows = len(data_b)
        print(f"Total rows: {n_rows:,}")
        
        # Verify columns
        cols_a = set(data_a.columns.names)
        cols_b = set(data_b.columns.names)
        
        missing_in_a = [col for col in columns_to_copy if col not in cols_a]
        missing_in_b = [col for col in columns_to_copy if col not in cols_b]
        
        if missing_in_a:
            raise ValueError(f"Columns missing in file A: {missing_in_a}")
        if missing_in_b:
            raise ValueError(f"Columns missing in file B: {missing_in_b}")
        
        print(f"Updating columns: {columns_to_copy}")
        print(f"Processing in chunks of {chunk_size:,} rows...")
        
        n_chunks = (n_rows + chunk_size - 1) // chunk_size
        
        for i in range(n_chunks):
            start_idx = i * chunk_size
            end_idx = min((i + 1) * chunk_size, n_rows)
            
            if (i + 1) % 10 == 0 or i == n_chunks - 1:
                print(f"Processing chunk {i+1}/{n_chunks} "
                      f"(rows {start_idx:,} to {end_idx:,})...")
            
            # Copy data from A to B for specified columns
            for col_name in columns_to_copy:
                data_b[col_name][start_idx:end_idx] = \
                    data_a[col_name][start_idx:end_idx]
        
        # Flush changes (happens automatically on close, but explicit is better)
        hdul_b.flush()
        print("Done! File B has been updated in place.")


if __name__ == "__main__":
    # Example usage
    
    file_a = "raw/marco_cats.fits"
    file_b = "generated/zerotestmarco.fits"
    
    # Option 1: Create new output file (safer)
    # update_fits_columns(file_a, file_b, output_path="fileB_updated.fits", 
    #                     chunk_size=1000000)
    
    # Option 2: Update in place (more memory efficient, but modifies original)
    # MAKE A BACKUP FIRST!
    update_fits_columns_inplace(file_a, file_b, chunk_size=1000000)
    
    print("Update the file paths above and uncomment the appropriate function call.")