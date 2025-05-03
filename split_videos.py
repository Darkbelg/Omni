import os
import subprocess
import argparse
import shlex
import time
import mmap
import tempfile
import concurrent.futures
import csv
from concurrent.futures import ProcessPoolExecutor

def process_video_chunk(video_path, start_time, duration):
    """Process a chunk of the video to find keyframes"""
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-select_streams', 'v:0',
        '-show_entries', 'frame=pkt_pts_time,pict_type',
        '-of', 'csv=p=0',
        '-read_intervals', f'{start_time}%+{duration}',  # Specify time range
        video_path
    ]

    # Use memory mapping for efficient I/O
    with tempfile.NamedTemporaryFile(mode='w+') as tmp:
        subprocess.run(cmd, stdout=tmp, check=True)
        tmp.flush()

        keyframes = []
        with open(tmp.name, 'rb') as f:
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            for line in iter(mm.readline, b''):
                timestamp, frame_type = line.decode().strip().split(',')
                if frame_type == 'I':
                    keyframes.append(float(timestamp))
            mm.close()

    return keyframes

def get_keyframes_parallel(video_path, chunk_duration=3600, max_workers=None):
    """
    Extract keyframes using parallel processing and memory mapping
    """
    print(f"Starting parallel keyframe extraction for {video_path}")
    start_time = time.time()

    # Get total video duration
    duration = float(subprocess.check_output([
        'ffprobe',
        '-v', 'quiet',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]))

    # Create chunks
    chunks = [
        (i, chunk_duration)
        for i in range(0, int(duration), chunk_duration)
    ]

    # Calculate optimal number of workers
    if max_workers is None:
        max_workers = min(len(chunks), os.cpu_count())

    print(f"Processing {len(chunks)} chunks using {max_workers} workers...")

    # Process chunks in parallel
    keyframes = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all chunks for processing
        future_to_chunk = {
            executor.submit(process_video_chunk, video_path, start, dur): (start, dur)
            for start, dur in chunks
        }

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_chunk):
            chunk_start, chunk_dur = future_to_chunk[future]
            try:
                chunk_keyframes = future.result()
                keyframes.extend(chunk_keyframes)
                print(f"Chunk {chunk_start}-{chunk_start+chunk_dur}: Found {len(chunk_keyframes)} keyframes")
            except Exception as e:
                print(f"Chunk {chunk_start}-{chunk_start+chunk_dur} failed: {e}")

    keyframes.sort()  # Ensure keyframes are in order

    end_time = time.time()
    print(f"Keyframe extraction completed in {end_time - start_time:.2f} seconds")
    print(f"Total keyframes found: {len(keyframes)}")

    return keyframes

def find_nearest_keyframe(keyframes, target_time):
    """Find the nearest keyframe to the target time"""
    return min(keyframes, key=lambda x: abs(x - target_time)) if keyframes else target_time

def create_output_dir(dir_name):
    """Create output directory if it doesn't exist"""
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

def split_video_at_intervals(video_path, output_dir, segment_duration=5, keyframes=None):
    """Split video into segment of specified duration, aligned to nearest keyframes"""
    # Get total video duration
    total_duration = float(subprocess.check_output([
        'ffprobe',
        '-v', 'quiet',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        video_path
    ]))

    print(f"Video duration: {total_duration:.2f} seconds")

    # Calculate segment start times (at exact intervals)
    segment_starts = [i for i in range(0, int(total_duration), segment_duration)]

    # If no keyframes provided, use exact times
    if keyframes is None or not keyframes:
        keyframes = segment_starts

    # Store segment information for CSV
    segments_data = []

    # Process each segment
    for i, start_time in enumerate(segment_starts):
        # Find nearest keyframe for clean cut
        nearest_start = find_nearest_keyframe(keyframes, start_time)

        # Calculate end time
        end_time = min(start_time + segment_duration, total_duration)

        # Calculate duration
        duration = end_time - nearest_start

        # Skip if duration is too short
        if duration < 0.5:  # Skip segments shorter than 0.5 seconds
            print(f"Skipping segment {i+1}: too short ({duration:.2f} seconds)")
            continue

        # Create output filename
        segment_name = f"segment_{i+1:04d}.mp4"
        output_file = os.path.join(output_dir, segment_name)

        # Build ffmpeg command
        command = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(nearest_start),
            '-t', str(duration),
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            output_file
        ]

        print(f"Creating segment {i+1}/{len(segment_starts)}: {nearest_start:.2f}s to {nearest_start+duration:.2f}s")

        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
            print(f"Created: {output_file}")
            
            # Store segment information for CSV
            segments_data.append({
                'name': segment_name,
                'start': nearest_start,
                'end': nearest_start + duration
            })
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating segment {i+1}: {e}")
            print(f"ffmpeg error: {e.stderr}")
    
    return segments_data

def write_segments_csv(segments_data, video_path, output_dir):
    """
    Write segment information to a CSV file.
    
    Args:
        segments_data: List of dictionaries containing 'name', 'start', and 'end' for each segment
        video_path: Original video file path
        output_dir: Directory where the CSV will be saved
    """
    # Use the original video filename (without extension) for the CSV
    base_name = os.path.basename(video_path)
    video_name = os.path.splitext(base_name)[0]
    csv_path = os.path.join(output_dir, f"{video_name}.csv")
    
    with open(csv_path, 'w', newline='') as csvfile:
        fieldnames = ['Name', 'Start', 'End']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for segment in segments_data:
            writer.writerow({
                'Name': segment['name'],
                'Start': f"{segment['start']:.2f}",
                'End': f"{segment['end']:.2f}"
            })
    
    print(f"CSV file created: {csv_path}")

def main():
    parser = argparse.ArgumentParser(description='Split video into 5-second segments.')
    parser.add_argument('video_path', help='Path to the video file')
    parser.add_argument('--output-dir', default='segments', help='Output directory for segments')
    parser.add_argument('--duration', type=int, default=5, help='Duration of each segment in seconds')
    parser.add_argument('--use-keyframes', action='store_true', help='Align segments to nearest keyframes')
    args = parser.parse_args()

    # Create output directory
    create_output_dir(args.output_dir)

    # Extract keyframes if needed
    keyframes = None
    if args.use_keyframes:
        print("Extracting keyframes for clean cuts...")
        keyframes = get_keyframes_parallel(args.video_path)

    # Split the video and get segment data
    segments_data = split_video_at_intervals(args.video_path, args.output_dir, args.duration, keyframes)
    
    # Write segment information to CSV
    write_segments_csv(segments_data, args.video_path, args.output_dir)

    print("Video splitting complete!")

if __name__ == '__main__':
    main()