# install
```
apt update
apt install screen rsync nano ffmpeg yt-dlp git git-lfs
```


# transfer
 rsync -avz  --exclude='*/.git' -e "ssh -p 22149 -i ~/.ssh/id_ed25519" /root/projects/omni/ root@63.141.33.46:/workspace/

# install
We need
- screen
- rsync
- nano
- ffmpeg
- yt-dlp

pip:
```python
pip install -r requirements.txt
pip uninstall transformers
pip install git+https://github.com/huggingface/transformers@v4.51.3-Qwen2.5-Omni-preview
pip install accelerate
pip install qwen-omni-utils[decord]
pip install protobuf
```



# workflow
Download 360p webm
Replace the id in all scripts
python split_videos.py
Setup runpod server
Install apt
install pip
Do the custom pip stuff
Copy everything over to the server
python process_videos.py
Copy everything back to home base
Shut down runpod server
Download the best version of the video
python merge_gameplay.py
python recut.py

```python
python process_videos.py --model_path="model/Qwen2.5-Omni-7B" --videos_dir="segments" --output_csv="dead-space.csv" --custom_prompt_path="system_prompt.md"
python process_videos.py --model_path="model/Qwen2.5-Omni-3B" --videos_dir="segments" --output_csv="dead-space-3b.csv" --custom_prompt_path="system_prompt.md"
python process_videos.py --model_path="model/Qwen2.5-Omni-7B" --videos_dir="segments" --output_csv="dead-space-system_prompt_technical-micro-analysis.csv" --custom_prompt_path="system_prompt_technical-micro-analysis.md"
python process_videos.py --model_path="model/Qwen2.5-Omni-3B" --videos_dir="segments" --output_csv="dead-space-system_prompt_technical-micro-analysis-3b.csv" --custom_prompt_path="system_prompt_technical-micro-analysis.md"
python process_videos.py --model_path="model/Qwen2.5-Omni-7B" --videos_dir="segments" --output_csv="system_prompt_technical-detailed-video-analysis.csv" --custom_prompt_path="system_prompt_technical-detailed-video-analysis.md"
python process_videos.py --model_path="model/Qwen2.5-Omni-3B" --videos_dir="segments" --output_csv="system_prompt_technical-detailed-video-analysis-3b.csv" --custom_prompt_path="system_prompt_technical-detailed-video-analysis.md"
python process_videos.py --model_path="model/Qwen2.5-Omni-7B" --videos_dir="segments" --output_csv="dead-space-system_prompt_technical-close-reading-of-video-content.csv" --custom_prompt_path="system_prompt_technical-close-reading-of-video-content.md"
python process_videos.py --model_path="model/Qwen2.5-Omni-3B" --videos_dir="segments" --output_csv="dead-space-system_prompt_technical-close-reading-of-video-content-3b.csv" --custom_prompt_path="system_prompt_technical-close-reading-of-video-content.md"
```