import pandas as pd
import os
import subprocess
import tempfile
import shutil

def trim_video_by_segments():
    print("Starting video trimming process...")
    
    # Check if input files exist
    input_video = 'p2eF4BwzogE-hd.webm'
    segments_csv = 'p2eF4BwzogE-gameplay.csv'
    output_video = 'p2eF4BwzogE-gameplay-hd.webm'
    
    if not os.path.exists(input_video):
        print(f"Error: Input video {input_video} not found!")
        return
    
    if not os.path.exists(segments_csv):
        print(f"Error: Segments CSV {segments_csv} not found!")
        return
    
    # Read the segments CSV file
    try:
        segments_df = pd.read_csv(segments_csv)
        print(f"Found {len(segments_df)} gameplay segments to extract")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return
    
    # Create a temporary directory for intermediate files
    temp_dir = tempfile.mkdtemp()
    print(f"Created temporary directory: {temp_dir}")
    
    try:
        # Create a list file for concatenation
        concat_list_path = os.path.join(temp_dir, 'concat_list.txt')
        
        with open(concat_list_path, 'w') as concat_file:
            # Process each segment
            for i, (_, row) in enumerate(segments_df.iterrows()):
                start_time = row['Start']
                end_time = row['End']
                duration = end_time - start_time
                
                # Skip invalid segments
                if duration <= 0:
                    print(f"Skipping invalid segment {i+1}: start={start_time}, end={end_time}")
                    continue
                
                # Output path for this segment
                segment_output = os.path.join(temp_dir, f"segment_{i:03d}.webm")
                
                # Build ffmpeg command for trimming
                trim_cmd = [
                    'ffmpeg',
                    '-i', input_video,
                    '-ss', str(start_time),
                    '-t', str(duration),
                    '-c', 'copy',  # Use copy to avoid re-encoding
                    '-avoid_negative_ts', '1',
                    segment_output
                ]
                
                # Execute the trim command
                print(f"Extracting segment {i+1}: {start_time} to {end_time} (duration: {duration}s)")
                try:
                    subprocess.run(trim_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    
                    # Add to concat list
                    concat_file.write(f"file '{segment_output}'\n")
                    
                except subprocess.CalledProcessError as e:
                    print(f"Error trimming segment {i+1}: {e}")
                    print(f"ffmpeg stderr: {e.stderr.decode()}")
        
        # Now concatenate all segments
        concat_cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_list_path,
            '-c', 'copy',  # Use copy to avoid re-encoding
            '-fflags', '+genpts',  # Generate new timestamps
            output_video
        ]
        
        print("Concatenating all segments into final video...")
        subprocess.run(concat_cmd, check=True)
        
        print(f"Successfully created gameplay video: {output_video}")
        
    except Exception as e:
        print(f"Error during processing: {e}")
    finally:
        # Clean up temporary files
        print("Cleaning up temporary files...")
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    trim_video_by_segments()