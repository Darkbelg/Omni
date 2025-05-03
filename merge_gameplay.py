import csv
import os
import re

def preprocess_csv(input_file, output_file):
    print(f"Preprocessing CSV file {input_file} to fix formatting issues...")

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
            # Add row if it has the expected number of columns
            if len(row) == len(header):
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
    return output_file

def extract_segment_number(filename):
    # Extract the numeric part from segment_XXXX.mp4
    match = re.search(r'segment_(\d+)\.mp4', filename)
    if match:
        return int(match.group(1))
    return 0

def merge_close_segments(gameplay_blocks, max_gap=15.0):
    """
    Merge gameplay blocks that are within max_gap seconds of each other
    """
    if not gameplay_blocks:
        return []
        
    # Sort blocks by start time (they should already be sorted)
    gameplay_blocks.sort(key=lambda x: x['start'])
    
    merged_blocks = [gameplay_blocks[0]]
    
    for block in gameplay_blocks[1:]:
        # Get the last merged block
        last_block = merged_blocks[-1]
        
        # Check if current block starts within max_gap seconds after the last block ends
        if block['start'] - last_block['end'] <= max_gap:
            # Merge blocks by extending the end time of the last block
            last_block['end'] = block['end']
        else:
            # Add as a new block if the gap is too large
            merged_blocks.append(block)
    
    return merged_blocks

def identify_gameplay_segments():
    # Preprocess the CSV files
    clean_dead_space = preprocess_csv('dead-space.csv', 'clean_dead_space.csv')
    clean_segments = preprocess_csv('p2eF4BwzogE.csv', 'clean_segments.csv')
    
    # Read the gameplay classification data
    gameplay_data = {}
    with open(clean_dead_space, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Store whether this segment is gameplay or not
            filename = row['Filename']
            is_gameplay = row['Model Output'].strip() == 'Gameplay'
            gameplay_data[filename] = is_gameplay
    
    # Read the segment timing data
    segments = []
    with open(clean_segments, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = row['Name']
            # Check if this segment exists in gameplay_data
            if name in gameplay_data:
                segments.append({
                    'name': name,
                    'start': float(row['Start']),
                    'end': float(row['End']),
                    'is_gameplay': gameplay_data[name]
                })
    
    # Sort segments by name (which should sort them chronologically)
    segments.sort(key=lambda x: extract_segment_number(x['name']))
    
    # Identify continuous gameplay blocks
    gameplay_blocks = []
    current_block = None
    
    for segment in segments:
        if segment['is_gameplay'] and current_block is None:
            # Start a new gameplay block
            current_block = {'start': segment['start'], 'end': segment['end']}
        elif segment['is_gameplay'] and current_block is not None:
            # Extend the current gameplay block
            current_block['end'] = segment['end']
        elif not segment['is_gameplay'] and current_block is not None:
            # End the current gameplay block
            gameplay_blocks.append(current_block)
            current_block = None
    
    # Don't forget to add the last block if it's still open
    if current_block is not None:
        gameplay_blocks.append(current_block)
    
    # Merge blocks that are close together (within 15 seconds)
    print(f"Found {len(gameplay_blocks)} initial gameplay blocks")
    merged_blocks = merge_close_segments(gameplay_blocks, max_gap=15.0)
    print(f"After merging close segments: {len(merged_blocks)} gameplay blocks")
    
    # Write the merged gameplay blocks to a new CSV file
    with open('p2eF4BwzogE-gameplay.csv', 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Start', 'End'])
        for block in merged_blocks:
            writer.writerow([block['start'], block['end']])
    
    print(f"Wrote gameplay blocks to p2eF4BwzogE-gameplay.csv")
    
    # Clean up temporary files
    if os.path.exists('clean_dead_space.csv'):
        os.remove('clean_dead_space.csv')
    if os.path.exists('clean_segments.csv'):
        os.remove('clean_segments.csv')

if __name__ == "__main__":
    identify_gameplay_segments()