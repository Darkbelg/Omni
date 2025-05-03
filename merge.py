import pandas as pd
import os
import subprocess
import re
import csv

# Preprocess the CSV file to handle quote issues and validate row structure
def preprocess_csv(input_file, output_file):
    print("Preprocessing CSV file to fix formatting issues...")

    with open(input_file, 'r', encoding='utf-8') as infile:
        content = infile.read()

        # Normalize quotes: replace triple quotes with single quotes
        content = content.replace('"""', '"')
        # Handle any double quotes that remain (not part of CSV quoting)
        content = content.replace('""', '"')

    # Write to a temporary file
    with open('temp_raw.csv', 'w', encoding='utf-8') as outfile:
        outfile.write(content)

    # Read and validate each row
    valid_rows = []
    with open('temp_raw.csv', 'r', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        header = next(reader, None)
        if header:
            valid_rows.append(header)

        for row in reader:
            # Check if row has exactly 5 columns
            if len(row) == 5:
                valid_rows.append(row)
            else:
                print(f"Skipping invalid row: {row}")

    # Write valid rows to the output file
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
        writer.writerows(valid_rows)

    # Clean up temporary file
    if os.path.exists('temp_raw.csv'):
        os.remove('temp_raw.csv')

    print(f"Preprocessing complete. Valid rows saved to {output_file}")

# Main script
input_csv = 'dead-space.csv'
processed_csv = 'dead-space-processed.csv'

# Preprocess the CSV file
preprocess_csv(input_csv, processed_csv)

# Read the processed CSV file
df = pd.read_csv(processed_csv)

# Filter rows where Model Output contains "Gameplay"
filtered_df = df[df['Model Output'].str.contains('Gameplay', case=True, na=False)]

# Define a function to extract the numerical part from the filename
def extract_number(filename):
    match = re.search(r'segment_(\d+)\.mp4', filename)
    if match:
        return int(match.group(1))
    return 0

# Sort the filtered dataframe by the numerical part of the filename
filtered_df = filtered_df.copy()  # Create a copy to avoid SettingWithCopyWarning
filtered_df['sort_key'] = filtered_df['Filename'].apply(extract_number)
filtered_df = filtered_df.sort_values('sort_key')

print(f"Found {len(filtered_df)} gameplay segments to merge")

# Create a temporary file listing all videos to concatenate
with open('temp_list.txt', 'w') as f:
    for filename in filtered_df['Filename']:
        input_path = f"/root/projects/omniv4/videos_split/processed/{filename}"
        f.write(f"file '{input_path}'\n")

# Construct the ffmpeg command with improved timestamp handling
output_file = '/root/projects/omniv4/merged_output.webm'
ffmpeg_cmd = [
    'ffmpeg',
    '-f', 'concat',
    '-safe', '0',
    '-fflags', '+genpts',  # Generate new timestamps to avoid timing issues
    '-i', 'temp_list.txt',
    '-c:v', 'libvpx-vp9',  # Re-encode video
    '-c:a', 'libopus',     # Re-encode audio
    '-b:v', '1M',          # Video bitrate
    '-b:a', '128k',        # Audio bitrate
    '-vsync', 'cfr',       # Constant frame rate output
    '-async', '1',         # Audio sync method
    output_file
]

# Execute the ffmpeg command
try:
    subprocess.run(ffmpeg_cmd, check=True)
    print(f"Successfully merged videos into {output_file}")
except subprocess.CalledProcessError as e:
    print(f"Error merging videos: {e}")
finally:
    # Clean up temporary files
    for temp_file in ['temp_list.txt', processed_csv]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    print("Temporary files cleaned up")