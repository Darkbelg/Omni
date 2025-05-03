import pprint
import os
import csv
import shutil
import torch
import logging
import argparse
from tqdm import tqdm
from pathlib import Path
from transformers import Qwen2_5OmniForConditionalGeneration, Qwen2_5OmniProcessor
from qwen_omni_utils import process_mm_info

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_processing.log'),
        logging.StreamHandler()
    ]
)

def read_custom_prompt(markdown_path):
    """Read custom prompt from a markdown file."""
    try:
        with open(markdown_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        logging.error(f"Custom prompt file not found: {markdown_path}")
        raise
    except Exception as e:
        logging.error(f"Error reading custom prompt: {str(e)}")
        raise

def clean_output_text(text):
    """Clean up the model output text."""
    parts = text.split("assistant\n", 1)
    if len(parts) > 1:
        return parts[1].strip()
    return text  # Return original if pattern not found

def process_videos(model_path, videos_dir, output_csv, custom_prompt_path):
    # Create processed directory if it doesn't exist
    processed_dir = os.path.join(videos_dir, "processed")
    os.makedirs(processed_dir, exist_ok=True)

    # Read custom prompt
    custom_prompt = read_custom_prompt(custom_prompt_path)
    logging.info(f"Using custom prompt: {custom_prompt[:100]}...")

    # The default system prompt required for Qwen2.5-Omni
    system_prompt = {
        "role": "system",
        "content": [
            {"type": "text", "text": "You are Qwen, a virtual human developed by the Qwen Team, Alibaba Group, capable of perceiving auditory and visual inputs, as well as generating text and speech."}
        ]
    }

    # Load model and processor
    logging.info("Loading model and processor...")
    try:
        # Load model from local path
        model = Qwen2_5OmniForConditionalGeneration.from_pretrained(
            model_path,
            torch_dtype="auto",
            device_map="auto",
            trust_remote_code=True,
            local_files_only=True  # Force using local files
        )
        model.disable_talker()  # Since we don't need audio output
        
        processor = Qwen2_5OmniProcessor.from_pretrained(
            model_path,
            trust_remote_code=True,
            local_files_only=True  # Force using local files
        )
        logging.info("Model and processor loaded successfully")
    except Exception as e:
        logging.error(f"Error loading model: {str(e)}")
        raise

    # Prepare results list for CSV
    results = []

    # Get list of video files
    video_files = [f for f in os.listdir(videos_dir)
                  if os.path.isfile(os.path.join(videos_dir, f))
                  and not f.startswith('.')
                  and f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))]

    logging.info(f"Found {len(video_files)} video files to process.")

    # Check if output CSV already exists and load previously processed files
    processed_files = set()
    if os.path.exists(output_csv):
        try:
            with open(output_csv, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                next(reader)  # Skip header
                for row in reader:
                    if row and len(row) > 0:
                        processed_files.add(row[0])
            logging.info(f"Found {len(processed_files)} already processed files in CSV")
        except Exception as e:
            logging.warning(f"Error reading existing CSV: {str(e)}")

    # Filter out already processed files
    video_files = [f for f in video_files if f not in processed_files]
    logging.info(f"Remaining files to process: {len(video_files)}")

    # Process each video
    for video_file in tqdm(video_files, desc="Processing videos"):
        video_path = os.path.join(videos_dir, video_file)

        try:
            # Create conversation with system prompt, video, and text prompt
            conversation = [
                system_prompt,
                {
                    "role": "user",
                    "content": [
                        {"type": "video", "video": video_path},
                        {"type": "text", "text": custom_prompt}
                    ],
                },
            ]

            # Process the conversation
            text = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
            audios, images, videos = process_mm_info(conversation, use_audio_in_video=True)
            inputs = processor(
                text=text,
                audio=audios,
                images=images,
                videos=videos,
                return_tensors="pt",
                padding=True,
                use_audio_in_video=True
            )
            inputs = inputs.to(model.device)

            # Generate text output
            with torch.no_grad():
                text_ids = model.generate(
                    **inputs,
                    use_audio_in_video=True,
                    return_audio=False,
                    max_new_tokens=4096
                )

            output_text = processor.batch_decode(text_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
            output_text = clean_output_text(output_text)
            pprint.pprint(output_text)

            # Save result
            results.append([video_file, output_text])

            # Write this result to CSV immediately to prevent data loss
            with open(output_csv, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                # Write header if file is new
                if os.path.getsize(output_csv) == 0:
                    writer.writerow(['Filename', 'Model Output'])
                writer.writerow([video_file, output_text])

            # Move processed file to processed directory
            shutil.move(video_path, os.path.join(processed_dir, video_file))
            logging.info(f"Processed: {video_file}")

        except Exception as e:
            logging.error(f"Error processing {video_file}: {str(e)}", exc_info=True)
            continue

    logging.info(f"Processing complete. Results saved to {output_csv}")
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process video clips with Qwen2.5-Omni model")
    parser.add_argument("--model_path", default="model/Qwen2.5-Omni-7B", help="Path to local model directory")
    parser.add_argument("--videos_dir", default="videos_split", help="Directory containing video clips")
    parser.add_argument("--output_csv", default="dead-space.csv", help="Output CSV file name")
    parser.add_argument("--custom_prompt_path", default="system_prompt.md", help="Path to custom prompt markdown file")

    args = parser.parse_args()

    # Create output CSV file with header if it doesn't exist
    if not os.path.exists(args.output_csv):
        with open(args.output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Filename', 'Model Output'])

    process_videos(args.model_path, args.videos_dir, args.output_csv, args.custom_prompt_path)