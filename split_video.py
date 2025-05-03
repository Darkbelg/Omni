#!/usr/bin/env python3
import os
import subprocess
import json
import concurrent.futures
import math
from pathlib import Path

def get_video_duration(input_file):
    """Get the duration of the video file using ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json',
        input_file
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return float(data['format']['duration'])

def split_segment(input_file, output_dir, segment_index, segment_duration=5):
    """Split a segment from the input file and resize to 640x360."""
    start_time = segment_index * segment_duration
    output_file = os.path.join(output_dir, f"segment_{segment_index:04d}.mp4")

    cmd = [
        'ffmpeg',
        '-y',  # Overwrite output files without asking
        '-i', input_file,
        '-ss', str(start_time),
        '-t', str(segment_duration),
        '-vf', 'scale=640:360',  # Scale video to 640x360
        '-c:v', 'libx264',       # Use H.264 codec for video
        '-preset', 'fast',       # Encoding preset (balance between speed and quality)
        '-c:a', 'aac',           # Use AAC codec for audio
        output_file
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_file

def main():
    input_file = "p2eF4BwzogE.webm"
    output_dir = "videos_split"

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)

    # Get video duration
    duration = get_video_duration(input_file)

    # Calculate number of segments
    segment_duration = 10
    num_segments = math.ceil(duration / segment_duration)

    print(f"Splitting {input_file} ({duration:.2f} seconds) into {num_segments} segments...")

    # Use ProcessPoolExecutor for parallel processing
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # Submit tasks for each segment
        futures = [
            executor.submit(split_segment, input_file, output_dir, i, segment_duration)
            for i in range(num_segments)
        ]

        # Process results as they complete
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            try:
                output_file = future.result()
                print(f"Completed segment {i+1}/{num_segments}: {os.path.basename(output_file)}")
            except Exception as e:
                print(f"Error processing segment {i}: {e}")

    print(f"All {num_segments} segments have been processed and saved to {output_dir}/")

if __name__ == "__main__":
    main()